"""Coupon code and discount

Revision ID: 89a08a6c6eb2
Revises: a94cb0bde02b
Create Date: 2023-05-28 15:06:47.158488

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '89a08a6c6eb2'
down_revision = 'a94cb0bde02b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('product', sa.Column('discount', sa.Float(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('product', 'discount')
    # ### end Alembic commands ###