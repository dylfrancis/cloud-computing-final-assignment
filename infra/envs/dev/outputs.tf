output "sql_server_fqdn" {
  value = module.sql.fully_qualified_domain_name
}

output "sql_database_name" {
  value = module.sql.database_name
}

output "api_url" {
  value = module.app_service.url
}

output "api_app_name" {
  value = module.app_service.app_name
}

output "web_url" {
  value = module.static_web_app.url
}

output "swa_deployment_token" {
  value       = module.static_web_app.api_key
  sensitive   = true
  description = "Run: terraform output -raw swa_deployment_token (then save to GitHub secret AZURE_STATIC_WEB_APPS_API_TOKEN)"
}
