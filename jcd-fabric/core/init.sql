CREATE DATABASE litellm;
\c fabric
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS jobs (
  id uuid PRIMARY KEY,
  business text NOT NULL,
  kind text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL DEFAULT 'queued',
  result jsonb,
  error text,
  expected_value_zar numeric,
  max_cost_zar numeric,
  created_at timestamptz NOT NULL DEFAULT now(),
  started_at timestamptz,
  finished_at timestamptz
);
CREATE INDEX IF NOT EXISTS jobs_status_created_idx ON jobs(status, created_at);
CREATE TABLE IF NOT EXISTS approvals (
  id uuid PRIMARY KEY,
  job_id uuid REFERENCES jobs(id) ON DELETE SET NULL,
  action text NOT NULL,
  summary text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL DEFAULT 'pending',
  created_at timestamptz NOT NULL DEFAULT now(),
  decided_at timestamptz
);
CREATE TABLE IF NOT EXISTS revenue_events (
  id bigserial PRIMARY KEY,
  business text NOT NULL,
  amount_zar numeric NOT NULL,
  kind text NOT NULL,
  reference text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS model_events (
  id bigserial PRIMARY KEY,
  business text,
  model text,
  task text,
  cost_usd numeric,
  latency_ms integer,
  success boolean,
  created_at timestamptz NOT NULL DEFAULT now()
);
