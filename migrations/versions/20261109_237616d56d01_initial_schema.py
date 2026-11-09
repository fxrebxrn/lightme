"""initial schema

Revision ID: 237616d56d01
Revises: 
Create Date: 2026-11-09 10:04:20.737797
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '237616d56d01'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table('bot_settings',
    sa.Column('key', sa.Enum('TECH_MODE', 'EMERGENCY', name='bot_flag', native_enum=False, length=32), nullable=False),
    sa.Column('enabled', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('key', name=op.f('pk_bot_settings'))
    )
    op.create_table('queue_schedules',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('company', sa.Enum('DTEK', 'CEK', name='company', native_enum=False, length=16), nullable=False),
    sa.Column('queue', sa.String(length=8), nullable=False),
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_queue_schedules')),
    sa.UniqueConstraint('company', 'queue', 'day', name=op.f('uq_queue_schedules_company_queue_day'))
    )
    op.create_index('ix_queue_schedules_day', 'queue_schedules', ['day'], unique=False)
    op.create_table('users',
    sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False),
    sa.Column('username', sa.String(length=64), nullable=True),
    sa.Column('full_name', sa.String(length=256), nullable=True),
    sa.Column('language', sa.String(length=8), server_default='uk', nullable=False),
    sa.Column('notify_off', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('notify_on', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('notify_off_10', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('notify_on_10', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    op.create_table('compares',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('company1', sa.Enum('DTEK', 'CEK', name='company', native_enum=False, length=16), nullable=False),
    sa.Column('queue1', sa.String(length=8), nullable=False),
    sa.Column('company2', sa.Enum('DTEK', 'CEK', name='company', native_enum=False, length=16), nullable=False),
    sa.Column('queue2', sa.String(length=8), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_compares_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_compares'))
    )
    op.create_index(op.f('ix_compares_user_id'), 'compares', ['user_id'], unique=False)
    op.create_table('outages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('schedule_id', sa.Integer(), nullable=False),
    sa.Column('start_minute', sa.SmallInteger(), nullable=False),
    sa.Column('end_minute', sa.SmallInteger(), nullable=False),
    sa.CheckConstraint('start_minute >= 0 AND end_minute <= 1440 AND start_minute < end_minute', name=op.f('ck_outages_valid_interval')),
    sa.ForeignKeyConstraint(['schedule_id'], ['queue_schedules.id'], name=op.f('fk_outages_schedule_id_queue_schedules'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_outages'))
    )
    op.create_index(op.f('ix_outages_schedule_id'), 'outages', ['schedule_id'], unique=False)
    op.create_table('subscriptions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('company', sa.Enum('DTEK', 'CEK', name='company', native_enum=False, length=16), nullable=False),
    sa.Column('queue', sa.String(length=8), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_subscriptions_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_subscriptions')),
    sa.UniqueConstraint('user_id', 'company', 'queue', name=op.f('uq_subscriptions_user_id_company_queue'))
    )
    op.create_index('ix_subscriptions_company_queue', 'subscriptions', ['company', 'queue'], unique=False)
    op.create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=False)



def downgrade() -> None:

    op.drop_index(op.f('ix_subscriptions_user_id'), table_name='subscriptions')
    op.drop_index('ix_subscriptions_company_queue', table_name='subscriptions')
    op.drop_table('subscriptions')
    op.drop_index(op.f('ix_outages_schedule_id'), table_name='outages')
    op.drop_table('outages')
    op.drop_index(op.f('ix_compares_user_id'), table_name='compares')
    op.drop_table('compares')
    op.drop_table('users')
    op.drop_index('ix_queue_schedules_day', table_name='queue_schedules')
    op.drop_table('queue_schedules')
    op.drop_table('bot_settings')

