# Trakora OS

Production procurement-intelligence runtime for Trakora Automotive Supply & Fleet Solutions.

## Architecture
DigitalOcean Ubuntu 24.04 → Docker Compose → FastAPI API/dashboard + PostgreSQL + six-hour procurement worker.

The worker ingests South African National Treasury eTenders OCDS releases, filters automotive and selected low-working-capital adjacent categories, deduplicates on OCID, keeps immutable versions of material changes, detects expired/missed-compulsory-briefing opportunities, and assigns an internal bid/partner/watch/no-bid screen.

## Core records
- opportunities
- opportunity_versions
- ingest_runs
- suppliers
- supplier_quotes
- bids
- alerts

## Runtime endpoints
- GET /health
- GET /
- GET /api/metrics
- GET /api/opportunities
- POST /api/opportunities/{id}/decision using the server-side ADMIN_TOKEN

## Deployment
Run bootstrap.sh as root on Ubuntu 24.04. It installs Docker, clones this repository, generates server-local database/admin credentials, starts the stack, creates a daily local pg_dump, configures UFW and disables password-based SSH.

No production secret is stored in Git.
