data "azurerm_resource_group" "rg" {
  name = var.resource_group_name
}

resource "random_string" "suffix" {
  length  = 6
  lower   = true
  numeric = true
  upper   = false
  special = false
}

resource "random_password" "jwt_secret" {
  length  = 48
  special = false
}

locals {
  name_suffix = random_string.suffix.result

  swa_url       = module.static_web_app.url
  cors_for_app  = concat(var.cors_origins, [local.swa_url])
}

module "sql" {
  source = "../../modules/sql"

  name_prefix         = var.prefix
  name_suffix         = local.name_suffix
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = var.location
  admin_user          = var.sql_admin_user
  admin_password      = var.sql_admin_password
  allowed_ip          = var.allowed_ip
}

module "static_web_app" {
  source = "../../modules/static_web_app"

  name_prefix         = var.prefix
  name_suffix         = local.name_suffix
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = "eastus2"
}

module "app_service" {
  source = "../../modules/app_service"

  name_prefix         = var.prefix
  name_suffix         = local.name_suffix
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = var.location
  sku_name            = var.app_service_sku
  database_url        = module.sql.connection_string
  jwt_secret          = random_password.jwt_secret.result
  cors_origins        = local.cors_for_app
}
