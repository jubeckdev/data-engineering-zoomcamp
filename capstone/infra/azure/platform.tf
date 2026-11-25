variable "enable_platform" {
  description = "Create the small Azure SQL/Container Apps platform within trial credit."
  type        = bool
  default     = false
}

variable "sql_location" {
  description = "SQL region; this trial rejected Switzerland North and West Europe. France Central advertises Basic availability."
  type        = string
  default     = "francecentral"
}

variable "operator_ipv4" {
  description = "Optional single IPv4 address for local SQL initialization; remove when finished."
  type        = string
  default     = null
}

variable "pipeline_image" {
  description = "Immutable ACR image reference. Null prepares the platform without starting a job."
  type        = string
  default     = null
}

locals {
  platform_count = var.enable_platform ? 1 : 0
  suffix         = substr(replace(var.subscription_id, "-", ""), 0, 8)
}

resource "azurerm_mssql_server" "warehouse" {
  count                         = local.platform_count
  name                          = "sql-zoomcamp-${local.suffix}-fc"
  resource_group_name           = azurerm_resource_group.portfolio.name
  location                      = var.sql_location
  version                       = "12.0"
  minimum_tls_version           = "1.2"
  connection_policy             = "Proxy"
  public_network_access_enabled = true
  azuread_administrator {
    login_username              = "Portfolio owner"
    object_id                   = data.azurerm_client_config.current.object_id
    tenant_id                   = data.azurerm_client_config.current.tenant_id
    azuread_authentication_only = true
  }
  tags = local.tags
}

resource "azurerm_mssql_database" "warehouse" {
  count                = local.platform_count
  name                 = "swiss-rail"
  server_id            = azurerm_mssql_server.warehouse[0].id
  sku_name             = "Basic"
  max_size_gb          = 2
  collation            = "Latin1_General_100_BIN2"
  storage_account_type = "Local"
  tags                 = local.tags
}

resource "azurerm_mssql_firewall_rule" "azure" {
  count            = local.platform_count
  name             = "AzureServicesWithEntraAuthentication"
  server_id        = azurerm_mssql_server.warehouse[0].id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

resource "azurerm_mssql_firewall_rule" "operator" {
  count            = var.enable_platform && var.operator_ipv4 != null ? 1 : 0
  name             = "TemporaryOperatorAddress"
  server_id        = azurerm_mssql_server.warehouse[0].id
  start_ip_address = var.operator_ipv4
  end_ip_address   = var.operator_ipv4
}

resource "azurerm_user_assigned_identity" "pipeline" {
  count               = local.platform_count
  name                = "id-zoomcamp-pipeline"
  resource_group_name = azurerm_resource_group.portfolio.name
  location            = var.location
  tags                = local.tags
}

resource "azurerm_role_assignment" "pipeline_data" {
  count                = local.platform_count
  scope                = azurerm_storage_account.lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.pipeline[0].principal_id
}

resource "azurerm_container_registry" "pipeline" {
  count               = local.platform_count
  name                = "acrzoomcamp${local.suffix}"
  resource_group_name = azurerm_resource_group.portfolio.name
  location            = var.location
  sku                 = "Basic"
  admin_enabled       = false
  tags                = local.tags
}

resource "azurerm_role_assignment" "image_pull" {
  count                = local.platform_count
  scope                = azurerm_container_registry.pipeline[0].id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.pipeline[0].principal_id
}

resource "azurerm_log_analytics_workspace" "pipeline" {
  count               = local.platform_count
  name                = "log-zoomcamp-pipeline"
  resource_group_name = azurerm_resource_group.portfolio.name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  daily_quota_gb      = 0.1
  tags                = local.tags
}

resource "azurerm_container_app_environment" "pipeline" {
  count                      = local.platform_count
  name                       = "cae-zoomcamp-pipeline"
  resource_group_name        = azurerm_resource_group.portfolio.name
  location                   = var.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.pipeline[0].id
  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }
  tags = local.tags
}

resource "azurerm_container_app_job" "pipeline" {
  count                        = var.enable_platform && var.pipeline_image != null ? 1 : 0
  name                         = "job-swiss-rail"
  resource_group_name          = azurerm_resource_group.portfolio.name
  location                     = var.location
  container_app_environment_id = azurerm_container_app_environment.pipeline[0].id
  workload_profile_name        = "Consumption"
  replica_timeout_in_seconds   = 900
  replica_retry_limit          = 1
  schedule_trigger_config {
    cron_expression          = "0 6 1 * *"
    parallelism              = 1
    replica_completion_count = 1
  }
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.pipeline[0].id]
  }
  registry {
    server   = azurerm_container_registry.pipeline[0].login_server
    identity = azurerm_user_assigned_identity.pipeline[0].id
  }
  template {
    container {
      name   = "pipeline"
      image  = var.pipeline_image
      cpu    = 1
      memory = "2Gi"
      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.pipeline[0].client_id
      }
      env {
        name  = "STORAGE_ACCOUNT"
        value = azurerm_storage_account.lake.name
      }
      env {
        name  = "SQL_SERVER"
        value = azurerm_mssql_server.warehouse[0].fully_qualified_domain_name
      }
      env {
        name  = "SQL_DATABASE"
        value = azurerm_mssql_database.warehouse[0].name
      }
    }
  }
  depends_on = [azurerm_role_assignment.image_pull, azurerm_role_assignment.pipeline_data]
  tags       = local.tags
}

output "runtime_config" {
  value = var.enable_platform ? {
    storage_account       = azurerm_storage_account.lake.name
    sql_server            = azurerm_mssql_server.warehouse[0].fully_qualified_domain_name
    sql_database          = azurerm_mssql_database.warehouse[0].name
    identity_client_id    = azurerm_user_assigned_identity.pipeline[0].client_id
    identity_principal_id = azurerm_user_assigned_identity.pipeline[0].principal_id
    registry              = azurerm_container_registry.pipeline[0].login_server
  } : null
}
