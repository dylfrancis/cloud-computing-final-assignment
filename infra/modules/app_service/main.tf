resource "azurerm_service_plan" "this" {
  name                = "${var.name_prefix}-plan-${var.name_suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = var.sku_name
}

resource "azurerm_linux_web_app" "this" {
  name                = "${var.name_prefix}-api-${var.name_suffix}"
  resource_group_name = var.resource_group_name
  location            = azurerm_service_plan.this.location
  service_plan_id     = azurerm_service_plan.this.id
  https_only          = true

  site_config {
    # F1 (Free) is the only SKU that doesn't support always_on. B1+ does.
    always_on        = var.sku_name != "F1"
    app_command_line = "bash startup.sh"
    application_stack {
      python_version = var.python_version
    }
    cors {
      allowed_origins     = var.cors_origins
      support_credentials = true
    }
  }

  app_settings = merge(
    {
      SCM_DO_BUILD_DURING_DEPLOYMENT = "1"
      APP_ENV                        = "dev"
      DATABASE_URL                   = var.database_url
      JWT_SECRET                     = var.jwt_secret
      JWT_ALG                        = "HS256"
      JWT_EXPIRES_MIN                = "60"
      CORS_ORIGINS                   = join(",", var.cors_origins)
    },
    var.extra_app_settings,
  )

  identity {
    type = "SystemAssigned"
  }
}
