"""Add "upload_ip" column to minidump

Revision ID: 20211211_002700_add_upload_ip
Revises: 
Create Date: 2021-12-11 05:20:46.385955

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20211211_002700_add_upload_ip"
down_revision = "20211211_001700_initial_database"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("minidump", sa.Column("upload_ip", postgresql.INET(), nullable=True))


def downgrade():
    op.drop_column("minidump", "upload_ip")
