-- Rebuild only the two tables with cohort CHECK constraints. D1 applies the
-- migration transactionally; defer NO ACTION foreign keys during replacement.
-- Never rename the old parent: human_trials must keep referencing human_sessions.
PRAGMA defer_foreign_keys = ON;

DROP TRIGGER human_assignment_revision;
DROP TRIGGER human_assignment_reserved;
DROP TRIGGER human_exposure_assigned;
DROP TRIGGER human_trial_completed;

CREATE TABLE human_protocol_state_new (
  protocol_version TEXT NOT NULL,
  cohort TEXT NOT NULL CHECK(cohort IN ('main','pilot','smoke','creator')),
  revision INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(protocol_version, cohort)
);
INSERT INTO human_protocol_state_new(protocol_version,cohort,revision)
  SELECT protocol_version,cohort,revision FROM human_protocol_state;
DROP TABLE human_protocol_state;
ALTER TABLE human_protocol_state_new RENAME TO human_protocol_state;

CREATE TABLE human_sessions_new (
  session_id TEXT PRIMARY KEY,
  participant_id TEXT NOT NULL REFERENCES human_participants(participant_id),
  session_token_hash TEXT NOT NULL UNIQUE,
  protocol_version TEXT NOT NULL,
  cohort TEXT NOT NULL CHECK(cohort IN ('main','pilot','smoke','creator')),
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
INSERT INTO human_sessions_new(
  session_id,participant_id,session_token_hash,protocol_version,cohort,
  assignment_seed,assignment_revision,status,consented_at,created_at,started_at,
  completed_at,device_class,viewport_bucket,assigned_count,answered_count,
  skipped_count,timeout_count)
SELECT session_id,participant_id,session_token_hash,protocol_version,cohort,
  assignment_seed,assignment_revision,status,consented_at,created_at,started_at,
  completed_at,device_class,viewport_bucket,assigned_count,answered_count,
  skipped_count,timeout_count FROM human_sessions;
DROP TABLE human_sessions;
ALTER TABLE human_sessions_new RENAME TO human_sessions;

CREATE UNIQUE INDEX human_one_main ON human_sessions(participant_id, protocol_version) WHERE cohort = 'main';
CREATE UNIQUE INDEX human_one_creator ON human_sessions(participant_id, protocol_version) WHERE cohort = 'creator';
CREATE INDEX human_session_analysis ON human_sessions(protocol_version, cohort, status);
CREATE INDEX human_session_participant ON human_sessions(participant_id);

-- Restore the existing trigger definitions without changing their behavior.
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

PRAGMA defer_foreign_keys = OFF;
