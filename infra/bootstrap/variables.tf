variable "subscription_id" {
  type        = string
  description = "Azure subscription ID"
}

variable "tenant_id" {
  type        = string
  description = "Azure tenant ID"
}

variable "resource_group_name" {
  type        = string
  description = "Existing resource group that holds the tfstate storage account"
  default     = "final-project-rg"
}

variable "prefix" {
  type        = string
  description = "Short prefix for globally-unique resource names"
  default     = "adh2"
}
