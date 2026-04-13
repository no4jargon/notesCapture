create table if not exists journal_events (
  canonical_event_uid text primary key,
  journal_path text not null,
  journal_line_no integer not null,
  journal_bucket_date text not null,
  event_id text,
  event_type text not null,
  schema_name text,
  schema_version text,
  captured_at text not null,
  committed_at text,
  source_client text,
  source_transport text,
  content_type text,
  text_body text,
  raw_event_json text not null
);

create virtual table if not exists journal_events_fts using fts5(
  canonical_event_uid unindexed,
  text_body
);

create table if not exists purpose_relevance (
  decision_id text primary key,
  purpose_id text not null,
  canonical_event_uid text not null,
  eligible integer not null,
  relevant integer not null,
  confidence real not null,
  reason text not null,
  decided_by text not null,
  classifier_version text not null,
  unique (purpose_id, canonical_event_uid)
);

create table if not exists time_use_evidence (
  evidence_id text primary key,
  canonical_event_uid text not null,
  source_event_type text not null,
  actuality text not null,
  observed_day_local text,
  observed_start_at text,
  observed_end_at text,
  anchor_time_at text not null,
  temporal_mode text not null,
  activity_text text not null,
  category text not null,
  subcategory text,
  confidence text not null,
  supporting_snippet text not null,
  derivation_notes text not null
);

create table if not exists time_use_blocks (
  block_id text primary key,
  day_local text not null,
  start_at text not null,
  end_at text not null,
  category text not null,
  label text not null,
  confidence text not null,
  source_evidence_ids text not null,
  derivation_type text not null,
  week_start text not null
);

create table if not exists time_use_daily_rollups (
  day_local text not null,
  category text not null,
  total_minutes integer not null,
  high_confidence_minutes integer not null,
  low_confidence_minutes integer not null,
  unknown_minutes integer not null,
  supporting_blocks integer not null,
  primary key (day_local, category)
);

create table if not exists time_use_weekly_rollups (
  week_start text not null,
  category text not null,
  total_minutes integer not null,
  high_confidence_minutes integer not null,
  low_confidence_minutes integer not null,
  unknown_minutes integer not null,
  supporting_blocks integer not null,
  primary key (week_start, category)
);

create table if not exists pipeline_runs (
  run_id text primary key,
  command_name text not null,
  started_at text not null,
  finished_at text not null,
  status text not null,
  metadata_json text not null
);
