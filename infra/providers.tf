terraform {
  required_version = ">= 1.9"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.0"
    }
  }
}

# Authentification : Azure CLI (az login). Aucun secret dans le code.
# L'ID d'abonnement vient de terraform.tfvars, qui n'est jamais versionné.
provider "azurerm" {
  subscription_id = var.subscription_id

  features {}
}
