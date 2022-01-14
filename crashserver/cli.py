import os
import uuid

import click
from email_validator import validate_email, EmailNotValidError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from crashserver.config import get_postgres_url


def register_cli(app):
    register_translation(app)
    register_account_mgmt(app)
    register_util(app)


def register_translation(app):
    @app.cli.group()
    def translate():
        """Translation and localization commands."""
        pass

    @translate.command()
    def update():
        """Update all languages."""
        if os.system("pybabel extract -F babel.cfg -k _l -o messages.pot ."):
            raise RuntimeError("extract command failed")
        if os.system("pybabel update -i messages.pot -d res/translations"):
            raise RuntimeError("update command failed")
        os.remove("messages.pot")

    @translate.command()
    def compile():
        """Compile all languages."""
        if os.system("pybabel compile -d res/translations"):
            raise RuntimeError("compile command failed")

    @translate.command()
    @click.argument("lang")
    def init(lang):
        """Initialize a new language."""
        if os.system("pybabel extract -F babel.cfg -k _l -o messages.pot ."):
            raise RuntimeError("extract command failed")
        if os.system("pybabel init -i messages.pot -d res/translations -l " + lang):
            raise RuntimeError("init command failed")
        os.remove("messages.pot")


def register_account_mgmt(app):
    @app.cli.group()
    def account():
        """Account management commands"""
        pass

    @account.command()
    @click.argument("email")
    def adduser(email):
        """Create a new web account"""
        from crashserver.server.models import User

        # Ensure email is valid
        try:
            valid = validate_email(email)
            email = valid.email
        except EmailNotValidError as e:
            click.echo(str(e))
            return

        # Connect to database
        with Session(create_engine(get_postgres_url())) as session:
            res = session.query(User).filter_by(email=email).first()
            if res:
                click.echo(f"User {email} already exists")
                return

            new_password = str(uuid.uuid4()).replace("-", "")  # Generate password
            new_user = User(email=email)
            new_user.set_password(new_password)

            session.add(new_user)  # Store to server
            session.commit()

            click.echo(f"User {email}:{new_password} has been created.")  # Notify

    @account.command()
    @click.argument("email", required=True)
    def deluser(email):
        """Delete an existing web account"""
        from crashserver.server.models import User

        with Session(create_engine(get_postgres_url())) as session:
            res = session.query(User).filter_by(email=email).first()
            if not res:
                click.echo(f"User {email} does not exist")

            # Delete the user
            session.delete(res)
            session.commit()
            click.echo(f"User {email} deleted.")


def register_util(app):
    @app.cli.group()
    def util():
        """Misc crashserver interface functions"""
        pass

    @util.command(help="Force minidump to decode")
    @click.argument("dump_id", required=True)
    def force_decode(dump_id):
        from crashserver.server.models import Minidump

        with Session(create_engine(get_postgres_url())) as session:
            res = session.query(Minidump).get(dump_id)
            res.decode_task()
        print(f"Minidump {dump_id} sent to worker for decode.")
