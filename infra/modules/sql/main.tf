resource "azurerm_mssql_server" "this" {
  name                         = "${var.name_prefix}-sql-${var.name_suffix}"
  resource_group_name          = var.resource_group_name
  location                     = var.location
  version                      = "12.0"
  administrator_login          = var.admin_user
  administrator_login_password = var.admin_password
  minimum_tls_version          = "1.2"

  public_network_access_enabled = true
}

resource "azurerm_mssql_database" "this" {
  name      = var.database_name
  server_id = azurerm_mssql_server.this.id
  collation = "SQL_Latin1_General_CP1_CI_AS"

  # Serverless Gen5 with auto-pause — pauses after idle, $0 at rest,
  # cents per active hour. Enable the "free offer" via the portal after
  # creation if this subscription hasn't already consumed it.
  sku_name                    = "GP_S_Gen5_2"
  min_capacity                = 0.5
  auto_pause_delay_in_minutes = 60
  max_size_gb                 = 32
  zone_redundant              = false
}

resource "azurerm_mssql_firewall_rule" "azure_services" {
  name             = "AllowAzureServices"
  server_id        = azurerm_mssql_server.this.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

resource "azurerm_mssql_firewall_rule" "dev_ip" {
  count            = var.allowed_ip == "" ? 0 : 1
  name             = "DevIP"
  server_id        = azurerm_mssql_server.this.id
  start_ip_address = var.allowed_ip
  end_ip_address   = var.allowed_ip
}
