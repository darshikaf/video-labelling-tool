-- Migration to update annotations table for object storage
-- This migration removes binary storage and adds object storage references

-- Add new columns for object storage
ALTER TABLE annotations 
ADD COLUMN mask_storage_key VARCHAR,
ADD COLUMN mask_width INTEGER,
ADD COLUMN mask_height INTEGER,
ADD COLUMN polygon_points TEXT;

-- Note: In a production environment with existing data, you would:
-- 1. First migrate existing mask_data to object storage
-- 2. Update mask_storage_key with object storage paths
-- 3. Then drop the mask_data column
-- 
-- For development/prototype, we can drop the column directly
-- since we're starting fresh

-- Remove the binary mask data column (development only)
ALTER TABLE annotations DROP COLUMN IF EXISTS mask_data;

-- Make mask_storage_key required for new records
-- (Skip this constraint if you need to migrate existing data first)
-- ALTER TABLE annotations ALTER COLUMN mask_storage_key SET NOT NULL;

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_annotations_mask_storage_key ON annotations(mask_storage_key);