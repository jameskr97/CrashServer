import flask_migrate
import pytest

from crashserver.config import settings
from crashserver.server import create_app, db
from crashserver.server.models import User, Storage


@pytest.fixture(scope="session", autouse=True)
def setup_session(client):

    # Create Database
    flask_migrate.upgrade()

    # Create default user
    user = User(email=settings.login.email)
    user.set_password(settings.login.passwd)
    db.session.add(user)
    db.session.commit()

    yield  # Do the tests

    # Delete default user
    db.session.delete(User.query.filter_by(email=settings.login.email).first())
    db.session.commit()


@pytest.fixture(scope="session")
def client():
    """Create a flask test client with database access"""
    settings.configure(FORCE_ENV_FOR_DYNACONF="testing")
    flask_app = create_app()
    flask_app.config.configure(FORCE_ENV_FOR_DYNACONF="testing")

    with flask_app.test_client() as testing_client:  # Create a test client using the Flask application configured for testing
        with flask_app.app_context():  # Establish an application context
            yield testing_client  # this is where the testing happens!
