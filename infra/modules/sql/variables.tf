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

variable "allowed_ip" {
  type        = string
  default     = ""
  description = "Public IP to whitelist on the SQL firewall (leave empty to skip)"
}
