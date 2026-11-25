variable "subscription_id" {
  description = "Azure subscription selected for this portfolio project."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.subscription_id))
    error_message = "Set subscription_id to the UUID of your Azure subscription."
  }
}

variable "storage_account_name" {
  description = "Globally unique account name: 3-24 lowercase letters or digits."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{3,24}$", var.storage_account_name))
    error_message = "Use 3-24 lowercase letters or digits; Azure checks global uniqueness at deployment."
  }
}

variable "resource_group_name" {
  description = "Dedicated resource group for resources managed by this configuration."
  type        = string
  default     = "rg-zoomcamp-portfolio-dev"

  validation {
    condition     = can(regex("^[a-zA-Z0-9_-]{1,90}$", var.resource_group_name))
    error_message = "Use 1-90 letters, digits, underscores, or hyphens."
  }
}

variable "location" {
  description = "Azure region. Switzerland North is the portfolio default; confirm subscription availability before applying."
  type        = string
  default     = "switzerlandnorth"
}

variable "tags" {
  description = "Additional tags. Required project and environment tags are applied below."
  type        = map(string)
  default     = {}
}
