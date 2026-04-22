variable "subscription_id" {
  type        = string
  description = "Azure subscription ID"
}

variable "tenant_id" {
  type        = string
  description = "Azure tenant ID"
}

variable "resource_group_name" {
  type    = string
  default = "final-project-rg"
}

variable "location" {
  type        = string
  default     = "eastus2"
  description = "Primary region. SWA is forced to eastus2 regardless."
}

variable "prefix" {
  type    = string
  default = "adh2"
}

variable "sql_admin_user" {
  type    = string
  default = "sqladmin"
}

variable "sql_admin_password" {
  type        = string
  sensitive   = true
  description = "Pass via TF_VAR_sql_admin_password env var — never commit."
}

variable "allowed_ips" {
  type        = list(string)
  default     = []
  description = "Dev public IPs to whitelist on the SQL firewall (set in terraform.tfvars)"
}

variable "app_service_sku" {
  type    = string
  default = "B1"
}

variable "cors_origins" {
  type    = list(string)
  default = ["http://localhost:5173"]
}
