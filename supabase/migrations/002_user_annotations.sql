-- GAD UA-01 — User trigger annotations and watchlist
-- Allows users to save triggers with state snapshots for drift detection.

CREATE TABLE IF NOT EXISTS user_trigger_annotations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES profiles(id),
    trigger_id TEXT NOT NULL,
    note TEXT,
    saved_at TIMESTAMPTZ DEFAULT now(),
    -- Snapshot at time of save
    model_version_id TEXT,
    threshold_percentile DOUBLE PRECISION,
    firing_rate DOUBLE PRECISION,
    spearman_rho DOUBLE PRECISION,
    UNIQUE(user_id, trigger_id)
);

-- RLS
ALTER TABLE user_trigger_annotations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read own annotations" ON user_trigger_annotations FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own annotations" ON user_trigger_annotations FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own annotations" ON user_trigger_annotations FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own annotations" ON user_trigger_annotations FOR DELETE USING (auth.uid() = user_id);
