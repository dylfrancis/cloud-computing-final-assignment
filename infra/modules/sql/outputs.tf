output "server_name" {
  value = azurerm_mssql_server.this.name
}

output "fully_qualified_domain_name" {
  value = azurerm_mssql_server.this.fully_qualified_domain_name
}

output "database_name" {
  value = azurerm_mssql_database.this.name
}

output "connection_string" {
  value = format(
    "mssql+aioodbc://%s:%s@%s:1433/%s?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no",
    var.admin_user,
    var.admin_password,
    azurerm_mssql_server.this.fully_qualified_domain_name,
    azurerm_mssql_database.this.name,
  )
  sensitive = true
}
