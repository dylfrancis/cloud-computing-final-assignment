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

variable "admin_user" {
  type    = string
  default = "sqladmin"
}

variable "admin_password" {
  type      = string
  sensitive = true
}

variable "database_name" {
  type    = string
  default = "retail"
}

variable "allowed_ips" {
  type        = list(string)
  default     = []
  description = "Public IPs to whitelist on the SQL firewall (empty list skips)"
}
