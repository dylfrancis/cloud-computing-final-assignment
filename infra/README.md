# Infra

Terraform for the Azure infrastructure:

- Azure SQL server + serverless database (free offer)
- Linux Python App Service (backend)
- Static Web App (frontend)

Resources are created inside the existing resource group `final-project-rg`.
Each globally-unique name is `adh2-<role>-<random6>`.

## One-time: bootstrap the remote state storage

```bash
cd infra/bootstrap
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
```

Record the output `storage_account_name` — you'll feed it into `envs/dev/backend.hcl`.

## Dev environment

```bash
cd infra/envs/dev
cp terraform.tfvars.example terraform.tfvars
cp backend.hcl.example backend.hcl   # fill in storage_account_name from bootstrap

# sensitive vars via env, not files:
export TF_VAR_sql_admin_password='<a-strong-password>'

terraform init -backend-config=backend.hcl
terraform plan
terraform apply
```

### Useful outputs after apply

```bash
terraform output api_url
terraform output web_url
terraform output -raw swa_deployment_token   # copy to GitHub secret AZURE_STATIC_WEB_APPS_API_TOKEN
```

## Notes

- **SQL free offer:** `use_free_limit = true` requests the free Azure SQL serverless
  offer (one per subscription). If you already consumed it elsewhere, set it to
  `false` in `modules/sql/main.tf` and accept normal serverless pricing.
- **App Service SKU:** defaults to `B1` (~$13/mo). Change `app_service_sku = "F1"`
  in tfvars for the free tier (no always-on, cold starts).
- **SQL firewall:** `allowed_ips` in `terraform.tfvars` is a list — add teammate
  IPs there and `terraform apply`. Leave empty to rely on the Azure-services
  rule only.
- **State:** lives in `tfstate` container in the bootstrap storage account. Never
  commit `*.tfvars`, `*.tfstate*`, or `.terraform/` — already gitignored.
