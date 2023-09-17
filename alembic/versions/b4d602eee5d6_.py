"""empty message

Revision ID: b4d602eee5d6
Revises: 30a8cc2aa2e3
Create Date: 2023-09-17 16:13:27.590209

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'b4d602eee5d6'
down_revision = '30a8cc2aa2e3'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('anle_section', 'context',
               existing_type=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=1000),
               type_=sa.Text(),
               existing_nullable=True)
    op.alter_column('anle_section', 'solution',
               existing_type=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=1000),
               type_=sa.Text(),
               existing_nullable=True)
    op.alter_column('anle_section', 'content',
               existing_type=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=1000),
               type_=sa.Text(),
               existing_nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('anle_section', 'content',
               existing_type=sa.Text(),
               type_=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=1000),
               existing_nullable=True)
    op.alter_column('anle_section', 'solution',
               existing_type=sa.Text(),
               type_=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=1000),
               existing_nullable=True)
    op.alter_column('anle_section', 'context',
               existing_type=sa.Text(),
               type_=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=1000),
               existing_nullable=True)
    # ### end Alembic commands ###