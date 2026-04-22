output "app_name" {
  value = azurerm_linux_web_app.this.name
}

output "default_hostname" {
  value = azurerm_linux_web_app.this.default_hostname
}

output "url" {
  value = "https://${azurerm_linux_web_app.this.default_hostname}"
}

output "principal_id" {
  value       = azurerm_linux_web_app.this.identity[0].principal_id
  description = "System-assigned managed identity, for future Key Vault / SQL Entra auth"
}
