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
  type        = string
  description = "Static Web Apps only runs in: eastus2, centralus, westus2, westeurope, eastasia"
  default     = "eastus2"
}
