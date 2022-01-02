import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from email_validator import validate_email, EmailNotValidError
from cloup import HelpFormatter, HelpTheme, Style, command, argument, group
from crashserver.config import get_postgres_url
import click


"""
initdb
project create <name>
symbol add <location>
purge symcache
purge minidumps

adduser <email>
deluser <email>
"""


@group(
    formatter_settings=HelpFormatter.settings(
        theme=HelpTheme(
            invoked_command=Style(fg="blue"),
            heading=Style(fg="white", bold=True),
            constraint=Style(fg="magenta"),
            col1=Style(fg="cyan"),
        )
    )
)
@click.version_option(prog_name="CrashServer")
def cli():
    """CrashServer CLI Manager - Access backend functionality of the CrashServer"""
    pass


@cli.command(help="Create a new web account")
@argument("email")
def adduser(email):
    from crashserver.webapp.models import User

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


@cli.command(help="Delete an existing web account")
@argument("email", required=True)
def deluser(email):
    from crashserver.webapp.models import User

    with Session(create_engine(get_postgres_url())) as session:
        res = session.query(User).filter_by(email=email).first()
        if not res:
            click.echo(f"User {email} does not exist")

        # Delete the user
        session.delete(res)
        session.commit()
        click.echo(f"User {email} deleted.")


@cli.command(help="Force minidump to decode")
@argument("dump_id", required=True)
def force_decode(dump_id):
    from crashserver.webapp.models import Minidump

    with Session(create_engine(get_postgres_url())) as session:
        res = session.query(Minidump).get(dump_id)
        res.decode_task()
    print(f"Minidump {dump_id} sent to worker for decode.")


if __name__ == '__main__':
    cli()