variable "name_prefix" {
  type = string
}

variable "name_suffix" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "sku_name" {
  type        = string
  default     = "B1"
  description = "App Service plan SKU. F1 = free (no always-on), B1 = Basic ~$13/mo"
}

variable "python_version" {
  type    = string
  default = "3.13"
}

variable "database_url" {
  type      = string
  sensitive = true
}

variable "jwt_secret" {
  type      = string
  sensitive = true
}

variable "cors_origins" {
  type    = list(string)
  default = []
}

variable "extra_app_settings" {
  type    = map(string)
  default = {}
}
