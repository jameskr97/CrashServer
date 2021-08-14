from huey.contrib.mini import MiniHuey
from webapp.models import Minidump, Project, Symbol, CompileMetadata
from pathlib import Path
from webapp import db, init_app
import subprocess
import utility
import logging

logger = logging.getLogger("CrashServer")

huey = MiniHuey()
huey.start()

@huey.task()
def decode_minidump(crash_id):
    app = init_app()
    with app.app_context():
        binary = str(Path("res/bin/linux/minidump_stackwalk").absolute())

        # Query database
        minidump = Minidump.query.get(crash_id)

        # Get minidump metadata
        dumpfile = str(Path(app.config["cfg"]["storage"]["minidump_location"]).absolute() / minidump.file_location)
        machine = subprocess.run([binary, "-m", dumpfile], capture_output=True)
        machine_text = machine.stdout.decode('utf-8').split('\n')
        metadata = utility.process_machine_minidump(machine_text)

        # Check if module_id and build_id exist in database
        compile_meta = db.session.query(CompileMetadata).filter(CompileMetadata.build_id == metadata.build_id).first()

        # The symbol file needed to decode this minidump does not exist.
        # Make a record in the CompileMetadata table with {build,module}_id. There will be a
        # relationship from that metadata to the minidump
        if compile_meta is None:
            logger.info("New build_id {} for module_id {}. Recording existence for project"
                        .format(metadata.build_id, metadata.build_id))
            new_metadata = CompileMetadata(project_id=minidump.project_id, module_id=metadata.module_id,
                                           build_id=metadata.build_id, symbol_exists=False)
            db.session.add(new_metadata)
            db.session.flush()
            minidump.build_metadata_id = new_metadata.id
            db.session.commit()
            return

        minidump.build_metadata_id = compile_meta.id

        if not compile_meta.symbol_exists:
            logger.info("Unable to symbolicate minidump id {}. Symbols do not exist.".format(crash_id))
            return

        symfolder = str(Path(app.config["cfg"]["storage"]["symbol_location"]).absolute() / str(minidump.project_id))
        raw = subprocess.run([binary, dumpfile, symfolder], capture_output=True)
        minidump.machine_stacktrace = machine.stdout.decode('utf-8')
        minidump.raw_stacktrace = raw.stdout.decode('utf-8')
        db.session.commit()


