-- CutPrint™ — per-show scene detection calibration profiles
ALTER TABLE shows ADD COLUMN IF NOT EXISTS cutprint_threshold INTEGER;
ALTER TABLE shows ADD COLUMN IF NOT EXISTS cutprint_min_scene INTEGER;  -- seconds
ALTER TABLE shows ADD COLUMN IF NOT EXISTS cutprint_genre VARCHAR(50);
ALTER TABLE shows ADD COLUMN IF NOT EXISTS cutprint_raw_cuts_per_min FLOAT;
ALTER TABLE shows ADD COLUMN IF NOT EXISTS cutprint_scenes_per_min FLOAT;
ALTER TABLE shows ADD COLUMN IF NOT EXISTS cutprint_median_scene_dur FLOAT;
ALTER TABLE shows ADD COLUMN IF NOT EXISTS cutprint_calibrated_at TIMESTAMPTZ;
ALTER TABLE shows ADD COLUMN IF NOT EXISTS cutprint_sample_episodes JSONB DEFAULT '[]';
