output "resource_group_name" {
  description = "Dedicated portfolio resource group."
  value       = azurerm_resource_group.portfolio.name
}

output "storage_account_name" {
  description = "Storage account used by future ingestion and transformation jobs."
  value       = azurerm_storage_account.lake.name
}

output "data_lake_endpoint" {
  description = "Authenticated ADLS endpoint; anonymous access is disabled."
  value       = azurerm_storage_account.lake.primary_dfs_endpoint
}

output "layer_uris" {
  description = "ABFS paths for the raw, cleaned, and analytical data layers."
  value = {
    for layer in local.layers : layer => "abfss://${layer}@${azurerm_storage_account.lake.name}.dfs.core.windows.net/"
  }
}
