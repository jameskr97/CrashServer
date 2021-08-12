from huey.contrib.mini import MiniHuey
from webapp.models import Minidump, Project
from pathlib import Path
from webapp import db, init_app
import subprocess

huey = MiniHuey()
huey.start()

@huey.task()
def decode_minidump(crash_id):
    app = init_app()
    with app.app_context():
        binary = str(Path("res/bin/minidump_stackwalk").absolute())
        minidump, project = db.session.query(Minidump, Project)\
            .filter(Minidump.id == crash_id)\
            .filter(Minidump.project_id == Project.id)\
            .first()

        dumpfile = str(Path(app.config["cfg"]["storage"]["minidump_location"]).absolute() / minidump.filename)
        symfolder = str(Path(app.config["cfg"]["storage"]["symbol_location"]).absolute() / str(project.id))

        raw = subprocess.run([binary, dumpfile, symfolder], capture_output=True)
        machine = subprocess.run([binary, "-m", dumpfile, symfolder], capture_output=True)
        minidump.machine_stacktrace = machine.stdout.decode('utf-8')
        minidump.raw_stacktrace = raw.stdout.decode('utf-8')
        db.session.commit()


