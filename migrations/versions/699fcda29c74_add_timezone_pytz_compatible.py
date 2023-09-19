"""Add timezone pytz compatible

Revision ID: 699fcda29c74
Revises: f0e90411280a
Create Date: 2023-09-18 18:45:28.647337

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '699fcda29c74'
down_revision = 'f0e90411280a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('timezone', sa.String(length=255), server_default='UTC', nullable=False))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('timezone')

    # ### end Alembic commands ###