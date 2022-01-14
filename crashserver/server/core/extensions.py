import boto3
import redis
import rq
from flask_babel import Babel
from flask_debugtoolbar import DebugToolbarExtension
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from crashserver.config import get_redis_url, get_s3store_config

babel = Babel()
debug_toolbar = DebugToolbarExtension()
limiter = Limiter(key_func=get_remote_address)
login = LoginManager()
migrate = Migrate()
db = SQLAlchemy()
s3store = boto3.client("s3", **get_s3store_config())
queue = rq.Queue("crashserver", connection=redis.Redis.from_url(get_redis_url()))
