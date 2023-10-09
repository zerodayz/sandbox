"""Remove language from exercise

Revision ID: ca9a2cd98855
Revises: b87cad02facf
Create Date: 2023-10-09 13:15:24.324243

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ca9a2cd98855'
down_revision = 'b87cad02facf'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('exercises', schema=None) as batch_op:
        batch_op.drop_column('language')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('exercises', schema=None) as batch_op:
        batch_op.add_column(sa.Column('language', sa.VARCHAR(), nullable=True))

    # ### end Alembic commands ###