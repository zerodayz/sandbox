"""exercise_scores: Adds an Execution Time

Revision ID: f0e90411280a
Revises: 
Create Date: 2023-09-13 21:37:58.257509

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f0e90411280a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('exercise_scores', schema=None) as batch_op:
        batch_op.add_column(sa.Column('execution_time', sa.Float(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('exercise_scores', schema=None) as batch_op:
        batch_op.drop_column('execution_time')

    # ### end Alembic commands ###