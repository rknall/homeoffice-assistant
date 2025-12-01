"""add_location_and_photo_features_v02

Revision ID: cb63b9a8c1b4
Revises: 22f34dad53ce
Create Date: 2025-12-01 19:50:19.139641

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb63b9a8c1b4'
down_revision: Union[str, None] = '22f34dad53ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add location fields to events table
    op.add_column('events', sa.Column('city', sa.String(200), nullable=True))
    op.add_column('events', sa.Column('country', sa.String(200), nullable=True))
    op.add_column('events', sa.Column('country_code', sa.String(3), nullable=True))
    op.add_column('events', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('events', sa.Column('longitude', sa.Float(), nullable=True))

    # Extend photo_references with metadata fields
    op.add_column('photo_references', sa.Column('thumbnail_url', sa.String(500), nullable=True))
    op.add_column('photo_references', sa.Column('taken_at', sa.DateTime(), nullable=True))
    op.add_column('photo_references', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('photo_references', sa.Column('longitude', sa.Float(), nullable=True))

    # Create location_images cache table for Unsplash images
    op.create_table(
        'location_images',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('city', sa.String(200), nullable=True),
        sa.Column('country', sa.String(200), nullable=False),
        sa.Column('unsplash_id', sa.String(50), nullable=False),
        sa.Column('image_url', sa.String(500), nullable=False),
        sa.Column('thumbnail_url', sa.String(500), nullable=False),
        sa.Column('photographer_name', sa.String(200), nullable=True),
        sa.Column('photographer_url', sa.String(500), nullable=True),
        sa.Column('fetched_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_location_images_city_country', 'location_images', ['city', 'country'])


def downgrade() -> None:
    # Drop location_images table
    op.drop_index('ix_location_images_city_country', table_name='location_images')
    op.drop_table('location_images')

    # Remove photo_references metadata columns
    op.drop_column('photo_references', 'longitude')
    op.drop_column('photo_references', 'latitude')
    op.drop_column('photo_references', 'taken_at')
    op.drop_column('photo_references', 'thumbnail_url')

    # Remove events location columns
    op.drop_column('events', 'longitude')
    op.drop_column('events', 'latitude')
    op.drop_column('events', 'country_code')
    op.drop_column('events', 'country')
    op.drop_column('events', 'city')
