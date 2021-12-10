import redis
import rq
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

from crashserver.config import get_redis_url

limiter = Limiter(key_func=get_remote_address)
login = LoginManager()
db = SQLAlchemy()
queue = rq.Queue("crashserver", connection=redis.Redis.from_url(get_redis_url()))
