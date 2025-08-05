-- Add display_name column to projects table
-- This migration adds display_name to preserve original user input while name becomes system-generated

-- First, add the display_name column as nullable
ALTER TABLE projects ADD COLUMN display_name VARCHAR;

-- Update existing projects to have display_name equal to current name
UPDATE projects SET display_name = name WHERE display_name IS NULL;

-- Make display_name NOT NULL now that all rows have values
ALTER TABLE projects ALTER COLUMN display_name SET NOT NULL;

-- Add unique constraint to name column for system-generated names
-- Note: This may fail if there are existing duplicates, which is expected
-- In that case, we'll need to update existing names to be unique first
DO $$
BEGIN
    -- Try to add unique constraint
    BEGIN
        ALTER TABLE projects ADD CONSTRAINT projects_name_unique UNIQUE (name);
    EXCEPTION WHEN duplicate_key THEN
        -- If duplicate names exist, we'll handle this in the application layer
        RAISE NOTICE 'Unique constraint not added due to existing duplicates. Will be handled by application logic.';
    END;
END $$;

-- Create index on display_name for faster searches
CREATE INDEX IF NOT EXISTS idx_projects_display_name ON projects (display_name);