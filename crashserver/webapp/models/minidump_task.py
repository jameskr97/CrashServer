import rq
import redis
from sqlalchemy.dialects.postgresql import UUID

from crashserver.webapp import db
from crashserver import config


class MinidumpTask(db.Model):
    __tablename__ = "minidump_task"
    id = db.Column(db.String(36), primary_key=True)
    task_name = db.Column(db.String(128), index=True)
    minidump_id = db.Column(UUID(as_uuid=True), db.ForeignKey("minidump.id"))
    complete = db.Column(db.Boolean, default=False)

    def get_rq_job(self):
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=config.get_redis_url())
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job
