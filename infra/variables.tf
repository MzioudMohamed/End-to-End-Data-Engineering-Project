variable "subscription_id" {
  description = "ID de l'abonnement Azure, fourni par terraform.tfvars (jamais versionné)."
  type        = string
}

variable "location" {
  description = "Région Azure. Doit faire partie des régions autorisées par la policy d'Azure for Students."
  type        = string
  default     = "francecentral"

  validation {
    condition     = contains(["switzerlandnorth", "denmarkeast", "francecentral", "spaincentral", "austriaeast"], var.location)
    error_message = "Région non autorisée par l'abonnement Azure for Students."
  }
}

variable "project" {
  description = "Nom court du projet, utilisé dans le nommage des ressources (lettres minuscules et chiffres)."
  type        = string
  default     = "retailmod"
}

variable "env" {
  description = "Environnement (dev ou prod)."
  type        = string
  default     = "dev"
}

variable "suffix" {
  description = "Suffixe court (2 à 6 minuscules ou chiffres) qui rend le nom du storage account unique dans tout Azure."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{2,6}$", var.suffix))
    error_message = "Le suffixe doit contenir 2 à 6 caractères : minuscules et chiffres uniquement."
  }
}
