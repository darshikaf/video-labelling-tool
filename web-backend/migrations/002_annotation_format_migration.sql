-- Migration to add annotation format support and annotation storage keys
-- This migration adds annotation format selection and dual storage capability

-- Add annotation_format column to projects table
ALTER TABLE projects 
ADD COLUMN annotation_format VARCHAR(20) DEFAULT 'YOLO';

-- Add annotation_storage_key column to annotations table
ALTER TABLE annotations 
ADD COLUMN annotation_storage_key VARCHAR;

-- Update existing projects to have default annotation format
UPDATE projects 
SET annotation_format = 'YOLO' 
WHERE annotation_format IS NULL;

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_projects_annotation_format ON projects(annotation_format);
CREATE INDEX IF NOT EXISTS idx_annotations_annotation_storage_key ON annotations(annotation_storage_key);

-- Add check constraint for valid annotation formats
ALTER TABLE projects 
ADD CONSTRAINT chk_annotation_format 
CHECK (annotation_format IN ('YOLO', 'COCO', 'PASCAL_VOC'));

-- Add comments for documentation
COMMENT ON COLUMN projects.annotation_format IS 'Preferred annotation format for training data (YOLO, COCO, PASCAL_VOC)';
COMMENT ON COLUMN annotations.annotation_storage_key IS 'Object storage key for annotation file in specified format';