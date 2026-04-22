output "resource_group_name" {
  value = data.azurerm_resource_group.rg.name
}

output "storage_account_name" {
  value = azurerm_storage_account.tfstate.name
}

output "container_name" {
  value = azurerm_storage_container.tfstate.name
}

output "suffix" {
  value       = random_string.suffix.result
  description = "Random suffix reused for the rest of the infra naming"
}
