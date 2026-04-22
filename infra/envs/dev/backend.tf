# Remote state lives in the storage account created by infra/bootstrap.
# The storage_account_name includes a random suffix, so pass it via
# `terraform init -backend-config=backend.hcl` (see backend.hcl.example).
#
# Auth: uses the storage account access key. Before `terraform init`:
#   export ARM_ACCESS_KEY=$(az storage account keys list \
#     --account-name <storage-account> \
#     --resource-group final-project-rg \
#     --query '[0].value' -o tsv)
terraform {
  backend "azurerm" {
    resource_group_name = "final-project-rg"
    container_name      = "tfstate"
    key                 = "dev.tfstate"
  }
}
