PRAGMA foreign_keys = ON;

CREATE TABLE human_participants (
  participant_id TEXT PRIMARY KEY,
  created_at INTEGER NOT NULL
);
CREATE TABLE human_protocol_state (
  protocol_version TEXT NOT NULL,
  cohort TEXT NOT NULL CHECK(cohort IN ('main','pilot','smoke')),
  revision INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(protocol_version, cohort)
);
CREATE TABLE human_sessions (
  session_id TEXT PRIMARY KEY,
  participant_id TEXT NOT NULL REFERENCES human_participants(participant_id),
  session_token_hash TEXT NOT NULL UNIQUE,
  protocol_version TEXT NOT NULL,
  cohort TEXT NOT NULL CHECK(cohort IN ('main','pilot','smoke')),
  assignment_seed TEXT NOT NULL,
  assignment_revision INTEGER NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('created','active','completed','abandoned')),
  consented_at INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  started_at INTEGER NOT NULL,
  completed_at INTEGER,
  device_class TEXT NOT NULL CHECK(device_class IN ('desktop','tablet','mobile')),
  viewport_bucket TEXT NOT NULL CHECK(viewport_bucket IN ('small','medium','large')),
  assigned_count INTEGER NOT NULL CHECK(assigned_count = 40),
  answered_count INTEGER NOT NULL DEFAULT 0 CHECK(answered_count >= 0),
  skipped_count INTEGER NOT NULL DEFAULT 0 CHECK(skipped_count >= 0),
  timeout_count INTEGER NOT NULL DEFAULT 0 CHECK(timeout_count >= 0),
  CHECK(answered_count + skipped_count <= assigned_count),
  CHECK(timeout_count <= skipped_count)
);
CREATE UNIQUE INDEX human_one_main ON human_sessions(participant_id, protocol_version) WHERE cohort = 'main';
CREATE INDEX human_session_analysis ON human_sessions(protocol_version, cohort, status);
CREATE INDEX human_session_participant ON human_sessions(participant_id);
CREATE TABLE human_trials (
  trial_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES human_sessions(session_id),
  position INTEGER NOT NULL CHECK(position BETWEEN 1 AND 40),
  challenge_id TEXT NOT NULL,
  variant TEXT NOT NULL CHECK(variant IN ('street-grid','hard-street-grid','checker-shadow','routing-puzzle','degraded-vision')),
  subtype TEXT,
  difficulty TEXT,
  resolution INTEGER,
  series_id TEXT,
  status TEXT NOT NULL DEFAULT 'assigned' CHECK(status IN ('assigned','presented','answered','skipped','timed_out')),
  assigned_at INTEGER NOT NULL,
  presented_at INTEGER,
  answered_at INTEGER,
  submitted_answer_json TEXT,
  submission_fingerprint TEXT,
  correct INTEGER CHECK(correct IN (0,1)),
  skipped INTEGER NOT NULL DEFAULT 0 CHECK(skipped IN (0,1)),
  timed_out INTEGER NOT NULL DEFAULT 0 CHECK(timed_out IN (0,1)),
  client_solve_time_ms INTEGER CHECK(client_solve_time_ms BETWEEN 0 AND 120000),
  server_elapsed_ms INTEGER CHECK(server_elapsed_ms >= 0),
  interrupted INTEGER NOT NULL DEFAULT 0 CHECK(interrupted IN (0,1)),
  UNIQUE(session_id, position),
  UNIQUE(session_id, challenge_id),
  CHECK(timed_out = 0 OR skipped = 1),
  CHECK(skipped = 0 OR correct = 0),
  CHECK((status IN ('assigned','presented') AND answered_at IS NULL AND correct IS NULL)
    OR (status IN ('answered','skipped','timed_out') AND answered_at IS NOT NULL AND correct IS NOT NULL AND submission_fingerprint IS NOT NULL))
);
CREATE UNIQUE INDEX human_unique_scene ON human_trials(session_id, series_id) WHERE variant = 'degraded-vision';
CREATE INDEX human_trial_current ON human_trials(session_id, status, position);
CREATE INDEX human_trial_challenge ON human_trials(challenge_id);
CREATE INDEX human_trial_variant ON human_trials(variant);
CREATE INDEX human_trial_subtype_difficulty ON human_trials(subtype, difficulty);
CREATE INDEX human_trial_resolution ON human_trials(resolution, series_id);
CREATE TABLE human_challenge_exposure (
  protocol_version TEXT NOT NULL,
  cohort TEXT NOT NULL,
  challenge_id TEXT NOT NULL,
  assigned_count INTEGER NOT NULL DEFAULT 0,
  completed_count INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(protocol_version, cohort, challenge_id)
);
CREATE TABLE human_rate_limits (
  bucket TEXT PRIMARY KEY,
  window_start INTEGER NOT NULL,
  request_count INTEGER NOT NULL
);

-- A stale exposure snapshot must roll back the entire session+assignment batch.
CREATE TRIGGER human_assignment_revision BEFORE INSERT ON human_sessions
WHEN NEW.assignment_revision != COALESCE((SELECT revision FROM human_protocol_state
  WHERE protocol_version = NEW.protocol_version AND cohort = NEW.cohort), -1)
BEGIN SELECT RAISE(ABORT, 'HB_ASSIGNMENT_CONFLICT'); END;
CREATE TRIGGER human_assignment_reserved AFTER INSERT ON human_sessions
BEGIN
  UPDATE human_protocol_state SET revision = revision + 1
    WHERE protocol_version = NEW.protocol_version AND cohort = NEW.cohort;
END;
CREATE TRIGGER human_exposure_assigned AFTER INSERT ON human_trials
BEGIN
  INSERT INTO human_challenge_exposure(protocol_version, cohort, challenge_id, assigned_count, completed_count)
    SELECT protocol_version, cohort, NEW.challenge_id, 1, 0 FROM human_sessions WHERE session_id = NEW.session_id
    ON CONFLICT(protocol_version, cohort, challenge_id) DO UPDATE SET assigned_count = assigned_count + 1;
END;
CREATE TRIGGER human_trial_final BEFORE UPDATE ON human_trials
WHEN OLD.status IN ('answered','skipped','timed_out')
BEGIN SELECT RAISE(ABORT, 'HB_TRIAL_FINAL'); END;
CREATE TRIGGER human_trial_completed AFTER UPDATE OF status ON human_trials
WHEN OLD.status IN ('assigned','presented') AND NEW.status IN ('answered','skipped','timed_out')
BEGIN
  UPDATE human_challenge_exposure SET completed_count = completed_count + 1
    WHERE challenge_id = NEW.challenge_id AND (protocol_version,cohort) =
      (SELECT protocol_version,cohort FROM human_sessions WHERE session_id = NEW.session_id);
  UPDATE human_sessions SET answered_count = answered_count + CASE WHEN NEW.status = 'answered' THEN 1 ELSE 0 END,
    skipped_count = skipped_count + NEW.skipped, timeout_count = timeout_count + NEW.timed_out
    WHERE session_id = NEW.session_id;
  UPDATE human_sessions SET status = 'completed', completed_at = NEW.answered_at
    WHERE session_id = NEW.session_id AND answered_count + skipped_count = assigned_count;
END;
