import json
import subprocess
from pathlib import Path

import requests
from loguru import logger

from crashserver import config
from crashserver.server.core.extensions import db
from crashserver.server.models import Minidump, BuildMetadata, SymCache, Storage
from crashserver.utility import processor


def download_windows_symbol(module_id: str, build_id: str) -> (bool, bool):
    """Attempts to download and convert symbols from Microsft Symbol Server.
    Returns tuple:
        - 1st tuple: True if succesful download, otherwise false
        - 2nd tuple: True if already downloaded, otherwise false
    """
    cached_sym = db.session.query(SymCache).filter_by(module_id=module_id, build_id=build_id).first()

    if cached_sym:
        return (False, True)  # Not downloaded, already exists

    cached_sym = SymCache(module_id=module_id, build_id=build_id)
    logger.debug("SymCache Miss. Attempting to download {}:{}".format(module_id, build_id))

    res = requests.get("https://msdl.microsoft.com/download/symbols/" + cached_sym.url_path)
    if res.status_code != 200:
        logger.debug("Symbol not available on Windows Symbol Server => {}:{}".format(module_id, build_id))
        return (False, False)

    cached_sym.store_and_convert_symbol(res.content)
    db.session.add(cached_sym)
    db.session.commit()
    return (True, False)


def decode_minidump(crash_id):
    # Prepare decode environment
    stackwalker = str(Path("res/bin/linux/stackwalker").absolute())
    cache_dir = Path("/tmp/crash_decode/cache")
    current_dump = Path("/tmp/crash_decode/current_dump.dmp")

    cache_dir.mkdir(parents=True, exist_ok=True)
    current_dump.parent.mkdir(parents=True, exist_ok=True)
    current_dump.unlink(missing_ok=True)

    # Symbolicate without symbols to get metadata
    # TODO: Proper error handling for if executable fails
    minidump = db.session.query(Minidump).get(crash_id)
    if not minidump:
        logger.error(f"Minidump [{crash_id}] - Unable to decode. No database entry found.")
        return

    # Request symbol and minidump from Storage
    with open(current_dump, "wb") as dump_out:
        try:
            dump_out.write(Storage.retrieve(minidump.file_location).read())
        except FileNotFoundError:
            logger.error(f"Minidump [{minidump.id}] was not found. Cancelling decode process.")
            return

    machine = subprocess.run([stackwalker, current_dump], capture_output=True)
    json_stack = json.loads(machine.stdout.decode("utf-8"))
    crash_data = processor.ProcessedCrash.generate(json_stack)

    # Check if a build_metadata already exists. (Previous minidump from same build, or symbol already uploaded)
    minidump.build = db.session.query(BuildMetadata).filter(BuildMetadata.build_id == crash_data.main_module.debug_id).first()

    # The symbol file needed to decode this minidump does not exist.
    # Make a record in the CompileMetadata table with {build,module}_id. There will be a
    # relationship from that metadata to the minidump
    if minidump.build is None:
        minidump.build = BuildMetadata(
            project_id=minidump.project_id,
            module_id=crash_data.main_module.debug_file,
            build_id=crash_data.main_module.debug_id,
        )
        db.session.flush()

    # No symbols? Notify and return
    if not minidump.build.symbol:
        logger.info(f"Minidump [{crash_id}] - Symbol [{crash_data.main_module.debug_file}:{crash_data.main_module.debug_id}] does not exist. Partial stacktrace stored.")
        minidump.stacktrace = json_stack
        minidump.symbolicated = False
        minidump.decode_task_complete = True
        db.session.commit()
        return

    # If we get here, then the symbol exists. Get it from the storage module.
    sym_path = Path(cache_dir, minidump.build.symbol.file_location)
    sym_path.parent.mkdir(parents=True, exist_ok=True)
    with open(sym_path, "wb") as out_sym:
        out_sym.write(Storage.retrieve(minidump.build.symbol.file_location_stored).read())

    # If windows, attempt to download all possible windows symbols before decoding
    # TODO(james): This is good as a prototype, but should be in a separate HTTP symbol supplier module/class
    if minidump.build.symbol.os == "windows":
        logger.debug(f"Minidump [{crash_id}] - Attempting Windows Symbol Server download")
        num_downloaded, num_existing = 0, 0
        for module in crash_data.modules_no_symbols:
            wasDownloaded, alreadyDownloaded = download_windows_symbol(module.debug_file, module.debug_id)

            if wasDownloaded:
                num_downloaded += 1
            if alreadyDownloaded:
                num_existing += 1

        logger.info(f"Minidump [{crash_id}] - Windows Symbols Obtained - [{num_downloaded}] Downloaded - [{num_existing}] Preexisting")

    def process(binary):
        return subprocess.run([binary, current_dump, cache_dir], capture_output=True)

    json_stackwalk = process(stackwalker)
    minidump.stacktrace = json.loads(json_stackwalk.stdout.decode("utf-8"))
    minidump.symbolicated = True
    minidump.decode_task_complete = True
    db.session.commit()
    logger.info(f"Minidump [{crash_id}] - Sucessfully decoded.", minidump.id)
