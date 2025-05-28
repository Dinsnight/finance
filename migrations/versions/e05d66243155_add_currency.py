"""add currency

Revision ID: e05d66243155
Revises: b3e527f36397
Create Date: 2025-05-28 03:14:03.059358

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e05d66243155'
down_revision = 'b3e527f36397'
branch_labels = None
depends_on = None


def upgrade():
    # Добавить колонку nullable
    op.add_column('transaction', sa.Column('currency', sa.String(length=10), nullable=True))

    # Можно добавить SQL-запрос для заполнения уже существующих записей, например:
    op.execute("UPDATE transaction SET currency = 'USD' WHERE currency IS NULL")

    # Сделать колонку NOT NULL
    with op.batch_alter_table('transaction') as batch_op:
        batch_op.alter_column('currency', nullable=False)


def downgrade():
    op.drop_column('transaction', 'currency')
