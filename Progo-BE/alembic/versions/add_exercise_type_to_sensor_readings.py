"""Add exercise_type to sensor_readings table

Revision ID: add_exercise_type_001
Revises: 95702332fd1d
Create Date: 2025-06-16 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_exercise_type_001'
down_revision = '95702332fd1d'
branch_labels = None
depends_on = None


def upgrade():
    """Add exercise_type column to sensor_readings table."""
    # Add exercise_type column
    op.add_column('sensor_readings', sa.Column('exercise_type', sa.String(), nullable=True))
    
    # Create index on exercise_type for performance
    op.create_index('ix_sensor_readings_exercise_type', 'sensor_readings', ['exercise_type'])


def downgrade():
    """Remove exercise_type column from sensor_readings table."""
    # Drop index first
    op.drop_index('ix_sensor_readings_exercise_type', table_name='sensor_readings')
    
    # Drop column
    op.drop_column('sensor_readings', 'exercise_type')
