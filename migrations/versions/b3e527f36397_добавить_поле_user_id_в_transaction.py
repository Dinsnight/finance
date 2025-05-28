"""Добавить поле user_id в Transaction

Revision ID: b3e527f36397
Revises:
Create Date: 2025-05-28 02:36:27.483356

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3e527f36397'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('transaction', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.alter_column('description',
               existing_type=sa.VARCHAR(length=100),
               type_=sa.String(length=255),
               existing_nullable=True)
        batch_op.alter_column('category',
               existing_type=sa.VARCHAR(length=50),
               type_=sa.String(length=100),
               existing_nullable=True)
        batch_op.alter_column('date',
               existing_type=sa.DATETIME(),
               type_=sa.Date(),
               existing_nullable=True)
        batch_op.create_foreign_key(
            "fk_transaction_user_id_user",  # здесь обязательно имя
            'user',
            ['user_id'],
            ['id']
        )

def downgrade():
    with op.batch_alter_table('transaction', schema=None) as batch_op:
        batch_op.drop_constraint("fk_transaction_user_id_user", type_='foreignkey')
        batch_op.alter_column('date',
               existing_type=sa.Date(),
               type_=sa.DATETIME(),
               existing_nullable=True)
        batch_op.alter_column('category',
               existing_type=sa.String(length=100),
               type_=sa.VARCHAR(length=50),
               existing_nullable=True)
        batch_op.alter_column('description',
               existing_type=sa.String(length=255),
               type_=sa.VARCHAR(length=100),
               existing_nullable=True)
        batch_op.drop_column('user_id')

