import uuid

from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.sql import func, text, expression

from crashserver.utility import processor
from crashserver.webapp import db, queue
from crashserver import config
from loguru import logger


class Minidump(db.Model):
    """
    Each minidump uploaded will get a file reference. The file won't always exist on system,
    but any data to regenerate the UI view of the minidump on /crash-report endpoints

    id: Generated GUID for this table
    project_id: The project which this minidump relates to
    date_created: The timestamp of when the minidump was uploaded
    filename: The filename of the guid stored in the MINIDUMP_STORE directory
    client_guid: The guid parameter passed in from the post parameters. Optional.
    stacktrace: Stacktrace decoded with `./stackwalker <dmp> [<symbol_dirs>]`
    """

    __tablename__ = "minidump"
    id = db.Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey("project.id"), nullable=False)
    build_metadata_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("build_metadata.id"),
        nullable=True,
        default=None,
    )
    date_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    symbolicated = db.Column(db.Boolean(), default=expression.false())
    client_guid = db.Column(UUID(as_uuid=True), nullable=True)
    filename = db.Column(db.Text(), nullable=False)
    stacktrace = db.Column(JSONB, nullable=True)

    # Relationships
    project = db.relationship("Project")
    build = db.relationship("BuildMetadata", back_populates="unprocessed_dumps")
    annotations = db.relationship("Annotation")
    task = db.relationship("MinidumpTask", uselist=False)
    symbol = db.relationship(
        "Symbol",
        primaryjoin="Minidump.build_metadata_id == BuildMetadata.id",
        secondary="join(BuildMetadata, Symbol, BuildMetadata.id == Symbol.build_metadata_id)",
        viewonly=True,
        uselist=False,
    )

    def store_minidump(self, file_contents: bytes):
        filename = "minidump-%s.dmp" % str(uuid.uuid4().hex)

        dump_file = config.get_appdata_directory("minidump") / str(self.project_id) / filename
        dump_file.parent.mkdir(parents=True, exist_ok=True)
        with open(dump_file.absolute(), "wb") as f:
            f.write(file_contents)

        self.filename = filename

    def decode_task(self, *args, **kwargs):
        from crashserver.webapp.models import MinidumpTask

        rq_job = queue.enqueue("crashserver.tasks." + "decode_minidump", self.id, *args, **kwargs)
        task = db.session.query(MinidumpTask).filter_by(minidump_id=self.id).first()
        if not task:
            task = MinidumpTask(task_name="decode_minidump", minidump_id=self.id)
        task.id = rq_job.get_id()
        task.complete = False
        db.session.add(task)
        return task

    @property
    def json(self):
        return processor.ProcessedCrash.generate(self.stacktrace)

    def symbols_exist(self):
        return self.symbol is not None

    def currently_processing(self):
        return self.task is not None
