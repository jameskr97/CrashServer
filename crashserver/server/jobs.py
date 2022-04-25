import json
import subprocess
from pathlib import Path

import requests
from loguru import logger

from crashserver import config
from crashserver.server.core.extensions import db
from crashserver.server.models import Minidump, BuildMetadata, SymCache, Storage
from crashserver.utility import processor


def download_windows_symbol(module_id: str, build_id: str):
    cached_sym = db.session.query(SymCache).filter_by(module_id=module_id, build_id=build_id).first()

    if cached_sym:
        logger.debug("SymCache Hit for {}:{}".format(module_id, build_id))
        return

    cached_sym = SymCache(module_id=module_id, build_id=build_id)
    logger.info("SymCache Miss. Attempting to download {}:{}".format(module_id, build_id))

    url = "https://msdl.microsoft.com/download/symbols/" + cached_sym.url_path
    res = requests.get(url)
    if res.status_code != 200:
        logger.warning("Symbol not available on Windows Symbol Server => {}:{}".format(module_id, build_id))
        return

    cached_sym.store_and_convert_symbol(res.content)
    db.session.add(cached_sym)
    db.session.commit()


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
        logger.error(f"Unable to decode minidump [{minidump}]. No database entry found.")
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
        logger.info(
            "Symbol {} does not exist. Storing partial stacktrace for Minidump ID {}",
            crash_data.main_module.debug_id,
            crash_id,
        )
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
        logger.info("Attempting to download windows symbols for minidump {}", minidump.id)
        for module in crash_data.modules_no_symbols:
            download_windows_symbol(module.debug_file, module.debug_id)
        logger.info("Symbol Download Complete for {}", minidump.id)

    def process(binary):
        return subprocess.run([binary, current_dump, cache_dir], capture_output=True)

    json_stackwalk = process(stackwalker)
    minidump.stacktrace = json.loads(json_stackwalk.stdout.decode("utf-8"))
    minidump.symbolicated = True
    minidump.decode_task_complete = True
    db.session.commit()
    logger.info("Minidump {} decoded", minidump.id)
