from gevent import monkey

monkey.patch_all()
from pathlib import Path
import subprocess
import logging

from huey.contrib.mini import MiniHuey

from crashserver.utility import processor
from crashserver.webapp.models import Minidump, Project, Symbol, BuildMetadata
from crashserver.webapp import db, init_app


logger = logging.getLogger("CrashServer")

huey = MiniHuey()
huey.start()


@huey.task()
def decode_minidump(crash_id):
    app = init_app()
    with app.app_context():
        binary = str(Path("res/bin/linux/minidump_stackwalk").absolute())

        # Get minidump metadata
        minidump = db.session.query(Minidump).get(crash_id)
        dumpfile = str(Path(minidump.project.minidump_location) / minidump.filename)
        machine = subprocess.run([binary, "-m", dumpfile], capture_output=True)
        machine_text = machine.stdout.decode("utf-8").split("\n")
        metadata = processor.process_machine_minidump(machine_text)

        minidump.build = db.session.query(BuildMetadata).filter(BuildMetadata.build_id == metadata.build_id).first()

        # The symbol file needed to decode this minidump does not exist.
        # Make a record in the CompileMetadata table with {build,module}_id. There will be a
        # relationship from that metadata to the minidump
        if minidump.build is None:
            minidump.build = BuildMetadata(
                project_id=minidump.project_id,
                module_id=metadata.module_id,
                build_id=metadata.build_id,
            )
            db.session.flush()

        if not minidump.build.symbol:
            logger.info("Unable to symbolicate minidump id {}. Symbols do not exist.".format(crash_id))
        else:
            raw = subprocess.run(
                [binary, dumpfile, minidump.project.symbol_location],
                capture_output=True,
            )
            machine = subprocess.run(
                [binary, "-m", dumpfile, minidump.project.symbol_location],
                capture_output=True,
            )
            minidump.machine_stacktrace = machine.stdout.decode("utf-8")
            minidump.raw_stacktrace = raw.stdout.decode("utf-8")
        db.session.commit()
