locals {
  tags = {
    project    = var.project
    env        = var.env
    managed_by = "terraform"
  }
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${var.project}-${var.env}"
  location = var.location
  tags     = local.tags
}

# Data lake : un storage account avec namespace hiérarchique (HNS) = ADLS Gen2.
# LRS : réplication la moins chère, suffisante pour un projet éducatif.
resource "azurerm_storage_account" "lake" {
  name                            = "st${var.project}${var.env}${var.suffix}"
  resource_group_name             = azurerm_resource_group.main.name
  location                        = azurerm_resource_group.main.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  account_kind                    = "StorageV2"
  is_hns_enabled                  = true
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  tags                            = local.tags
}

# Dans ADLS Gen2, un "conteneur" s'appelle un filesystem : c'est là que ADF écrira les fichiers Parquet.
resource "azurerm_storage_data_lake_gen2_filesystem" "landing" {
  name               = "landing"
  storage_account_id = azurerm_storage_account.lake.id
}
