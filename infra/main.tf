locals {
  tags = {
    project    = var.project
    env        = var.env
    managed_by = "terraform"
  }
}

data "azurerm_client_config" "current" {}

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

resource "azurerm_key_vault" "main" {
  name                       = "kv-${var.project}-${var.env}-${var.suffix}"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  purge_protection_enabled   = false
  soft_delete_retention_days = 7
  tags                       = local.tags
}

resource "azurerm_data_factory" "main" {
  name                = "adf-${var.project}-${var.env}-${var.suffix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

resource "azurerm_role_assignment" "adf_storage_contributor" {
  scope                = azurerm_storage_account.lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_data_factory.main.identity[0].principal_id
}

resource "azurerm_role_assignment" "adf_key_vault_secrets_user" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_data_factory.main.identity[0].principal_id
}

resource "azurerm_role_assignment" "current_user_key_vault_officer" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_data_factory_integration_runtime_self_hosted" "main" {
  name            = "shir-${var.project}-${var.env}"
  data_factory_id = azurerm_data_factory.main.id
}