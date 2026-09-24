CREATE TABLE IF NOT EXISTS opportunities (
  id BIGSERIAL PRIMARY KEY,
  ocid TEXT NOT NULL UNIQUE,
  release_id TEXT,
  tender_id TEXT,
  buyer_name TEXT NOT NULL DEFAULT 'Unknown',
  title TEXT NOT NULL,
  description TEXT,
  category TEXT,
  province TEXT,
  delivery_location TEXT,
  procurement_method TEXT,
  published_at TIMESTAMPTZ,
  closing_at TIMESTAMPTZ,
  briefing_required BOOLEAN NOT NULL DEFAULT FALSE,
  briefing_compulsory BOOLEAN NOT NULL DEFAULT FALSE,
  briefing_at TIMESTAMPTZ,
  briefing_venue TEXT,
  submission_method TEXT,
  submission_details TEXT,
  eligibility_criteria TEXT,
  special_conditions TEXT,
  source_url TEXT,
  documents JSONB NOT NULL DEFAULT '[]'::jsonb,
  raw JSONB NOT NULL,
  content_hash TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'live',
  bid_decision TEXT NOT NULL DEFAULT 'watch',
  fit_score NUMERIC NOT NULL DEFAULT 0,
  margin_score NUMERIC NOT NULL DEFAULT 0,
  capital_score NUMERIC NOT NULL DEFAULT 0,
  execution_score NUMERIC NOT NULL DEFAULT 0,
  deadline_score NUMERIC NOT NULL DEFAULT 0,
  total_score NUMERIC NOT NULL DEFAULT 0,
  recommended_action TEXT,
  needs_primary_verification BOOLEAN NOT NULL DEFAULT FALSE,
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS opp_closing_idx ON opportunities(closing_at);
CREATE INDEX IF NOT EXISTS opp_decision_idx ON opportunities(bid_decision,total_score DESC);
CREATE INDEX IF NOT EXISTS opp_status_idx ON opportunities(status);

CREATE TABLE IF NOT EXISTS opportunity_versions (
  id BIGSERIAL PRIMARY KEY,
  opportunity_id BIGINT NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
  content_hash TEXT NOT NULL,
  raw JSONB NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(opportunity_id,content_hash)
);

CREATE TABLE IF NOT EXISTS ingest_runs (
  id BIGSERIAL PRIMARY KEY,
  source_name TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  fetched INTEGER NOT NULL DEFAULT 0,
  matched INTEGER NOT NULL DEFAULT 0,
  inserted INTEGER NOT NULL DEFAULT 0,
  updated INTEGER NOT NULL DEFAULT 0,
  rejected INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'running',
  error_summary TEXT
);

CREATE TABLE IF NOT EXISTS suppliers (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  province TEXT,
  categories JSONB NOT NULL DEFAULT '[]'::jsonb,
  brands JSONB NOT NULL DEFAULT '[]'::jsonb,
  contact_name TEXT,
  email TEXT,
  phone TEXT,
  website TEXT,
  credit_days INTEGER,
  credit_limit_zar NUMERIC,
  delivery_sla_days INTEGER,
  rating NUMERIC,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS supplier_quotes (
  id BIGSERIAL PRIMARY KEY,
  opportunity_id BIGINT NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
  supplier_id BIGINT REFERENCES suppliers(id),
  description TEXT NOT NULL,
  quantity NUMERIC,
  unit_cost_zar NUMERIC,
  logistics_zar NUMERIC NOT NULL DEFAULT 0,
  stock_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
  lead_time_days INTEGER,
  quote_valid_until TIMESTAMPTZ,
  evidence_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bids (
  id BIGSERIAL PRIMARY KEY,
  opportunity_id BIGINT NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'draft',
  quoted_revenue_zar NUMERIC,
  expected_cost_zar NUMERIC,
  expected_contribution_zar NUMERIC,
  own_cash_required_zar NUMERIC,
  submitted_at TIMESTAMPTZ,
  awarded_at TIMESTAMPTZ,
  invoice_amount_zar NUMERIC,
  invoiced_at TIMESTAMPTZ,
  paid_at TIMESTAMPTZ,
  outcome_notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alerts (
  id BIGSERIAL PRIMARY KEY,
  opportunity_id BIGINT REFERENCES opportunities(id) ON DELETE CASCADE,
  alert_type TEXT NOT NULL,
  fingerprint TEXT NOT NULL UNIQUE,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  acknowledged_at TIMESTAMPTZ
);