# MarketIntelli Backend

A backend system for managing marketplace operations using ERPNext, FastAPI, and AI-driven insights.

## Features

- ERPNext integration for stock and order management.
- AI-driven replenishment and pricing optimization.
- Real-time metrics and observability.
- Modular and scalable architecture.

## Setup

1. Clone the repository.
2. Run `create_project_structure.sh` to create the project structure.
3. Install dependencies with `pip install -r requirements.txt`.
4. Run the application with `uvicorn app:app --reload`.

## Directory Structure

```
.
├── Dockerfile
├── README.md
├── app.py
├── cache
│   ├── pubsub_messaging.py
│   └── redis_cache.py
├── config
│   ├── config.json
│   ├── dev.env
│   └── prod.env
├── integrations
│   ├── customizations
│   ├── examples
│   └── setup_erpnext.sh
├── models
│   ├── ai_models.py
│   ├── api_responses.py
│   ├── inventory_models.py
│   ├── marketplace_models.py
│   └── order_models.py
├── requirements.txt
├── routers
│   ├── health.py
│   ├── inventory.py
│   ├── marketplace.py
│   ├── metrics.py
│   ├── order.py
│   ├── pricing.py
│   └── replenishment.py
├── services
│   ├── ai_insights_service.py
│   ├── cache_service.py
│   ├── erpnext_service.py
│   ├── integration
│   ├── notification_service.py
│   ├── pricing_service.py
│   ├── queue_service.py
│   ├── replenishment_service.py
│   └── stock_service.py
├── tests
│   ├── test_integration.py
│   ├── test_inventory.py
│   ├── test_marketplace.py
│   ├── test_order.py
│   ├── test_pricing.py
│   └── test_replenishment.py
└── utils
    ├── file_utils.py
    ├── logging_helpers.py
    ├── prometheus_helpers.py
    ├── retry_helpers.py
    └── slack_helpers.py

11 directories, 41 files
```
