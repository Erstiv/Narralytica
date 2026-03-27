-- Narralytica: Add Thea integration fields to shows and episodes.
-- Stores metadata pulled from Sonarr/Radarr (artwork, genres, ratings, etc.)

-- Show metadata from Sonarr
ALTER TABLE shows ADD COLUMN IF NOT EXISTS year INTEGER;
ALTER TABLE shows ADD COLUMN IF NOT EXISTS network VARCHAR(255);
ALTER TABLE shows ADD COLUMN IF NOT EXISTS overview TEXT;
ALTER TABLE shows ADD COLUMN IF NOT EXISTS genres JSONB DEFAULT '[]';
ALTER TABLE shows ADD COLUMN IF NOT EXISTS sonarr_id INTEGER;
ALTER TABLE shows ADD COLUMN IF NOT EXISTS tvdb_id INTEGER;
ALTER TABLE shows ADD COLUMN IF NOT EXISTS poster_url TEXT;
ALTER TABLE shows ADD COLUMN IF NOT EXISTS fanart_url TEXT;
ALTER TABLE shows ADD COLUMN IF NOT EXISTS banner_url TEXT;
ALTER TABLE shows ADD COLUMN IF NOT EXISTS clearlogo_url TEXT;
ALTER TABLE shows ADD COLUMN IF NOT EXISTS media_path TEXT;
ALTER TABLE shows ADD COLUMN IF NOT EXISTS rating_value FLOAT;
ALTER TABLE shows ADD COLUMN IF NOT EXISTS rating_votes INTEGER;

-- Episode metadata from Sonarr
ALTER TABLE episodes ADD COLUMN IF NOT EXISTS air_date VARCHAR(20);
ALTER TABLE episodes ADD COLUMN IF NOT EXISTS overview TEXT;
ALTER TABLE episodes ADD COLUMN IF NOT EXISTS sonarr_episode_id INTEGER;

-- Index for looking up shows by Sonarr ID
CREATE INDEX IF NOT EXISTS idx_shows_sonarr_id ON shows(sonarr_id);
