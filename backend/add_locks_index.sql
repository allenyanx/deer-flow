-- Manually add missing index for team_locks table
-- This index is needed for efficient expiration checks

CREATE INDEX IF NOT EXISTS idx_team_locks_expires_at 
ON team_locks (expires_at);

-- Verify the index was created
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'team_locks';
