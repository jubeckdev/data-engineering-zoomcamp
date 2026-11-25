locals {
  layers = toset(["bronze", "silver", "gold"])
  tags = merge(var.tags, {
    project     = "zoomcamp-portfolio"
    environment = "dev"
    managed_by  = "terraform"
  })
}

data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "portfolio" {
  name     = var.resource_group_name
  location = var.location
  tags     = local.tags
}

resource "azurerm_storage_account" "lake" {
  name                            = var.storage_account_name
  resource_group_name             = azurerm_resource_group.portfolio.name
  location                        = azurerm_resource_group.portfolio.location
  account_kind                    = "StorageV2"
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  access_tier                     = "Hot"
  is_hns_enabled                  = true
  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = false
  default_to_oauth_authentication = true
  public_network_access_enabled   = true
  sftp_enabled                    = false
  local_user_enabled              = false
  tags                            = local.tags
}

# Management-plane Owner/Contributor does not itself grant access to lake data.
# Grant the signed-in Terraform operator data access on this account only.
resource "azurerm_role_assignment" "operator_data" {
  scope                = azurerm_storage_account.lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

# A new role assignment can take time to become effective in storage APIs.
resource "time_sleep" "rbac" {
  depends_on      = [azurerm_role_assignment.operator_data]
  create_duration = "60s"
  triggers = {
    role_assignment_id = azurerm_role_assignment.operator_data.id
  }
}

resource "azurerm_storage_data_lake_gen2_filesystem" "layer" {
  for_each           = local.layers
  name               = each.value
  storage_account_id = azurerm_storage_account.lake.id
  depends_on         = [time_sleep.rbac]
}
