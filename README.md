# Cloud Computing Final Project

Retail insights app built on Azure. Analyzes the 84.51°/Kroger Complete Journey sample dataset (households, products, transactions) and surfaces customer engagement, basket, CLV, and churn insights.

## Layout

```
frontend/   React + Vite + TypeScript SPA  →  Azure Static Web Apps
backend/    FastAPI + SQLAlchemy + sklearn →  Azure App Service (Linux, Python)
infra/      Terraform for all Azure infra
.github/    GitHub Actions workflows
```

## Stack

- **Frontend:** React 19, Vite, TypeScript
- **Backend:** FastAPI, SQLAlchemy 2 (async), Alembic, pandas, scikit-learn
- **Database:** Azure SQL Database — Serverless (free tier)
- **Auth:** JWT with bcrypt-hashed credentials
- **Infra:** Terraform, remote state in Azure Storage
- **CI/CD:** GitHub Actions (one workflow per service)

## Getting started

See `frontend/`, `backend/`, and `infra/` READMEs (to be added) for per-service setup.
