output "resource_group_name" {
  description = "Nom du resource group créé."
  value       = azurerm_resource_group.main.name
}

output "storage_account_name" {
  description = "Nom du storage account ADLS Gen2."
  value       = azurerm_storage_account.lake.name
}

output "landing_filesystem" {
  description = "Nom du filesystem où ADF déposera les fichiers Parquet."
  value       = azurerm_storage_data_lake_gen2_filesystem.landing.name
}
