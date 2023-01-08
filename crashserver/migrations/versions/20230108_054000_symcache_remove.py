"""Remove symcache table

Revision ID: 8ef90f500b38
Revises: 20220114_103500_storage_table
Create Date: 2023-01-08 05:37:58.456479

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20230108_054000_symcache_remove"
down_revision = "20220114_103500_storage_table"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("symcache")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "symcache",
        sa.Column("id", postgresql.UUID(), server_default=sa.text("gen_random_uuid()"), autoincrement=False, nullable=False),
        sa.Column("date_created", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("now()"), autoincrement=False, nullable=True),
        sa.Column("module_id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("build_id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("os", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("arch", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("file_location", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("file_size_bytes", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("id", name="symcache_pkey"),
    )
    # ### end Alembic commands ###