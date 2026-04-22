output "name" {
  value = azurerm_static_web_app.this.name
}

output "default_host_name" {
  value = azurerm_static_web_app.this.default_host_name
}

output "url" {
  value = "https://${azurerm_static_web_app.this.default_host_name}"
}

output "api_key" {
  value       = azurerm_static_web_app.this.api_key
  sensitive   = true
  description = "Deployment token. Save as AZURE_STATIC_WEB_APPS_API_TOKEN in GitHub secrets."
}
