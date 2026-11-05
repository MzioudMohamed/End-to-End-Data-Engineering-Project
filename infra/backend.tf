terraform {
  backend "azurerm" {
    resource_group_name  = "rg-retailmod-dev"
    storage_account_name = "stretailmoddevmm10"
    container_name       = "tfstate"
    key                  = "retailmod-dev.tfstate"
    use_azuread_auth     = true
  }
}