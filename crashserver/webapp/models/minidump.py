from functools import cached_property
from pathlib import Path
import uuid

from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.sql import func, text, expression
import redis
import rq

from crashserver.utility import processor
from crashserver.webapp import db, queue
from crashserver import config


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
    upload_ip = db.Column(INET(), nullable=True, server_default=None)
    filename = db.Column(db.Text(), nullable=False)
    stacktrace = db.Column(JSONB, nullable=True)
    decode_task_id = db.Column(db.String(36))
    decode_task_complete = db.Column(db.Boolean())

    # Relationships
    project = db.relationship("Project")
    build = db.relationship("BuildMetadata", back_populates="unprocessed_dumps")
    annotations = db.relationship("Annotation")
    symbol = db.relationship(
        "Symbol",
        primaryjoin="Minidump.build_metadata_id == BuildMetadata.id",
        secondary="join(BuildMetadata, Symbol, BuildMetadata.id == Symbol.build_metadata_id)",
        viewonly=True,
        uselist=False,
    )
    attachments = db.relationship("Attachment")

    @property
    def file_location(self) -> Path:
        return config.get_appdata_directory("minidump") / str(self.project_id) / self.filename

    def store_minidump(self, file_contents: bytes):
        filename = "minidump-%s.dmp" % str(uuid.uuid4().hex)

        dump_file = config.get_appdata_directory("minidump") / str(self.project_id) / filename
        dump_file.parent.mkdir(parents=True, exist_ok=True)
        with open(dump_file.absolute(), "wb") as f:
            f.write(file_contents)

        self.filename = filename

    def delete_minidump(self):
        from crashserver.webapp.models import Annotation, Attachment

        # Get all annotations
        annotations = db.session.query(Annotation).filter_by(minidump_id=self.id).all()
        attachments = db.session.query(Attachment).filter_by(minidump_id=self.id).all()
        [db.session.delete(a) for a in annotations]
        for a in attachments:
            a.delete_file()
            db.session.delete(a)

        self.file_location.unlink(missing_ok=True)

    def decode_task(self, *args, **kwargs):
        rq_job = queue.enqueue("crashserver.webapp.jobs." + "decode_minidump", self.id, *args, **kwargs)
        self.decode_task_id = rq_job.get_id()
        self.decode_task_complete = False
        return rq_job

    def get_decode_job(self):
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=config.get_redis_url())
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job

    @cached_property
    def json(self):
        return processor.ProcessedCrash.generate(self.stacktrace)

    def symbols_exist(self):
        return self.symbol is not None

    def currently_processing(self):
        return self.task is not None
