import uuid

from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from flask_login import UserMixin
from crashserver.webapp import db


class User(db.Model, UserMixin):
    """
    Crash Server keeps track of user accounts ot determine who has has permission to administrate Crash Server.
    There will be zero permissions available.
        - An anonymous user can upload minidumps, view symbols, and view the crash dashboard for each application.
        - An authenticated user can access api-keys, delete symbols, and manage any application settings.
    """

    __tablename__ = "users"
    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    date_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    email = db.Column(db.String(254), nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def __init__(self, email):
        self.email = email

    def set_password(self, password):
        self.password = generate_password_hash(password, method="pbkdf2:sha512:310000")

    def check_password(self, password):
        return check_password_hash(self.password, password)
