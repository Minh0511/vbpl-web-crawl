"""change fulltext field size

Revision ID: 87229110fc79
Revises: 442c32ff0fc8
Create Date: 2023-09-15 10:46:56.690998

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '87229110fc79'
down_revision = '442c32ff0fc8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('vbpl_toan_van', 'section_name',
               existing_type=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=100),
               type_=sa.String(length=200),
               existing_nullable=True)
    op.alter_column('vbpl_toan_van', 'chapter_name',
               existing_type=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=100),
               type_=sa.String(length=200),
               existing_nullable=True)
    op.alter_column('vbpl_toan_van', 'big_part_name',
               existing_type=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=100),
               type_=sa.String(length=200),
               existing_nullable=True)
    op.alter_column('vbpl_toan_van', 'part_name',
               existing_type=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=100),
               type_=sa.String(length=200),
               existing_nullable=True)
    op.alter_column('vbpl_toan_van', 'mini_part_name',
               existing_type=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=100),
               type_=sa.String(length=200),
               existing_nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('vbpl_toan_van', 'mini_part_name',
               existing_type=sa.String(length=200),
               type_=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=100),
               existing_nullable=True)
    op.alter_column('vbpl_toan_van', 'part_name',
               existing_type=sa.String(length=200),
               type_=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=100),
               existing_nullable=True)
    op.alter_column('vbpl_toan_van', 'big_part_name',
               existing_type=sa.String(length=200),
               type_=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=100),
               existing_nullable=True)
    op.alter_column('vbpl_toan_van', 'chapter_name',
               existing_type=sa.String(length=200),
               type_=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=100),
               existing_nullable=True)
    op.alter_column('vbpl_toan_van', 'section_name',
               existing_type=sa.String(length=200),
               type_=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=100),
               existing_nullable=True)
    # ### end Alembic commands ###