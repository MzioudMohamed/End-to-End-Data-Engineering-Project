# État d'avancement

Dernière mise à jour : 30 octobre 2026.
À mettre à jour à la fin de chaque step ou tâche (propose le texte, l'utilisateur valide).

## Où on en est

- **Tâche en cours : T2 (ingestion).** Steps 2.1 faits, 2.2 à confirmer, **prochain : step 2.3** (première brique Terraform).
- **T1 (environnement et source legacy)** : techniquement terminée (source fonctionnelle, 3 jours rejoués). Reste le README (non créé).

## Points à confirmer au début de la session

Demande à l'utilisateur, un par un :
1. **Step 2.2** : Azure CLI et Terraform sont-ils installés ? (`az account show` affiche *Azure for Students*, `terraform -version` répond,
   extension VS Code HashiCorp Terraform installée.)
2. Les 5 fichiers de `infra/` sont-ils copiés dans le dépôt ? Le `.gitignore` contient-il `*.tfvars` ?
3. `docs/journal.md` existe-t-il et contient-il les premières entrées (voir « Leçons à noter » plus bas) ?
4. Les scripts de `legacy/` et de `docker-compose.yml` sont-ils commités et poussés ?
5. Le quiz T1 a été présenté ; l'utilisateur veut-il en revoir les points faibles ?

## T1 : environnement et source legacy

| Step | Contenu | Statut |
|---|---|---|
| 1.1 | Prérequis (Docker Desktop WSL2, Git, `.wslconfig` à 6 Go) | Fait |
| 1.2 | Dépôt GitHub, `.gitignore`, `.env.example` | Fait |
| 1.3 | SQL Server 2022 dans Docker Compose (`localhost,1434`, conteneur `legacy-sqlserver`, healthy) | Fait |
| 1.4 | Restauration d'AdventureWorks2022 (`legacy/restore_adventureworks.sql`) | Fait |
| 1.5 | Exploration et profilage de la source | Fait |
| 1.6 | Création de `LegacyRetail` à J0 (`legacy/create_legacy_retail.sql`) | Fait |
| 1.7 | Procédure `dbo.usp_advance_one_day` (`legacy/advance_one_day.sql`) | Fait : **3 jours rejoués** |
| 1.8 | Section « Source legacy » du README | **Non fait : le README n'existe pas** |

**État actuel de la source** : `LastDay` = **2014-05-03** (jours 2014-05-01, 02 et 03 rejoués). La source n'est donc plus à J0.
Avant le chargement initial de T2 (step 2.7), la remettre à J0 en relançant `legacy/create_legacy_retail.sql` **après confirmation de
l'utilisateur** (action destructive, locale). Raison : les lignes modifiées depuis J0 ont perdu leur valeur de J0, et un chargement initial
« tel que J0 » serait faux. Voir `docs/PROJECT.md`, section 5.5.

**README** : à créer par l'utilisateur, dans ses mots. Propose-lui un plan à la fin de T2 (au plus tard en T10) :
principe (AdventureWorks = archive, `LegacyRetail` = legacy vivant, J0, 61 jours rejouables) ; reproduction (`docker compose up -d`,
téléchargement manuel du `.bak`, scripts SQL) ; périmètre des 7 tables ; limites assumées (pas de `DELETE` captés, volume faible).

## Valeurs de référence vérifiées

| Élément | Valeur |
|---|---|
| Lignes à J0 | `Territory` 10, `ProductCategory` 4, `ProductSubcategory` 37, `Product` 504, `Customer` 17 406, `SalesOrderHeader` 28 115, `SalesOrderDetail` 110 561 |
| `LastDay` après création | 2014-04-30 |
| Premier jour rejoué (2014-05-01) | 227 commandes, 46 lignes clients modifiées (15 déplacés + nouveaux), 3 produits repriced (514, 515, 517) |
| `LastDay` actuel | 2014-05-03 |
| Test de complétude optionnel | Après 61 appels, `SalesOrderHeader` doit contenir 31 465 lignes (puis relancer `create_legacy_retail.sql` pour revenir à J0) |

## T2 : ingestion (legacy vers landing)

| Step | Contenu | Statut |
|---|---|---|
| 2.1 | Abonnement Azure, régions autorisées, tests de validation, budget | **Fait** |
| 2.2 | Azure CLI, Terraform, `az login` | À confirmer |
| 2.3 | Terraform brique 1 : resource group + ADLS Gen2 + filesystem `landing` | **Prochain** (fichiers `infra/` fournis, pas encore exécutés) |
| 2.4 | Key Vault + ADF (identité managée) + RBAC | À faire |
| 2.5 | Login SQL `adf_reader` en lecture seule, secret dans Key Vault | À faire |
| 2.6 | SHIR (ressource Terraform, installation sur l'hôte, connexion à `localhost,1434`) | À faire |
| 2.7 | Premier pipeline : Copy d'une table en full load vers Parquet | À faire |
| 2.8 | Pipeline générique (Lookup → ForEach → Copy) avec extraction incrémentale | À faire |
| 2.9 | Tests (relance, extraction vide, jours suivants) et export JSON vers `adf/` | À faire |

### Résultat du step 2.1
- Abonnement **Azure for Students** actif, obtenu en se connectant avec **GitHub** (la vérification par e-mail scolaire avait échoué avec
  « Vous n'avez pas accès »). Reconnexion : *Sign-in options → GitHub*.
- Tenant de l'abonnement **différent** de celui de Fabric.
- Régions autorisées : `switzerlandnorth`, `denmarkeast`, `francecentral`, `spaincentral`, `austriaeast`. Région retenue : `francecentral`.
- Validation (sans création) réussie pour Storage ADLS Gen2, Data Factory et Key Vault. Budget créé.

## Prochaine action : step 2.3 (Terraform, première brique)

Présente le step avec le format habituel (objectif, à faire, fiches, pièges, critère de sortie, « Reviens avec »).
Contenu attendu :
1. Vérifier `az account show` (bon abonnement) et `terraform -version`.
2. Ajouter `*.tfvars` au `.gitignore`.
3. Copier `infra/terraform.tfvars.example` en `infra/terraform.tfvars` : ID d'abonnement (`az account show --query id -o tsv`) et suffixe
   unique de 2 à 6 caractères.
4. Vérifier `az provider show -n Microsoft.Storage --query registrationState -o tsv` ; enregistrer si besoin
   (`az provider register -n Microsoft.Storage --wait`).
5. Dans `infra/` : `terraform init`, `fmt`, `validate`, `plan` (attendu : 3 à ajouter), `apply`, second `plan` (attendu : « No changes »).
6. Vérifier dans le portail : `rg-retailmod-dev`, le storage avec namespace hiérarchique, le filesystem `landing`.
7. Commiter `infra/` (avec `.terraform.lock.hcl`), sans `terraform.tfvars`, `.terraform/` ni `*.tfstate`.

**Les fichiers Terraform n'ont jamais été validés par `terraform validate`.** Si une erreur d'attribut apparaît (provider 5.x),
vérifie la documentation du provider avant de corriger.

**Critère de sortie** : 3 ressources créées, second `plan` sans changement, `infra/` commité proprement.

Ensuite : **step 2.4** (Key Vault + ADF + RBAC ; enregistrer `Microsoft.KeyVault` et `Microsoft.DataFactory`).

## Leçons à noter dans le journal de l'utilisateur (il les rédige dans ses mots)

- `localhost:1434` dans un navigateur affiche une erreur : SQL Server parle TDS, pas HTTP. Utiliser SSMS avec `localhost,1434` (virgule)
  et *Trust server certificate*.
- Le port 1433 est pris par le SQL Server Windows : d'où 1434.
- `ModifiedDate` d'AdventureWorks non fiable (décalage de 7 jours sur les commandes, valeurs uniques, dates en 2015).
- Le compte universitaire (Entra) ne peut pas créer d'abonnement Azure : « Le type de votre compte actuel n'est pas pris en charge ».
- Vérification Azure for Students par e-mail scolaire refusée ; connexion par GitHub acceptée.
- Validation d'adresse impossible pour le Maroc : « Utiliser cette adresse ».
- La policy d'Azure for Students limite les régions de déploiement : vérifier `allowedLocations` avant d'écrire du Terraform.
- `azurerm` est passé en version 5 : aucun resource provider enregistré par défaut.
- La source a été avancée de 3 jours : un chargement initial exact exige une remise à J0.

## Rappels de méthode

- Un step (ou un petit groupe de steps) à la fois, critère de sortie, « Reviens avec : ... ».
- Chaque script avec sa fiche (Quoi / Pourquoi / Pourquoi maintenant / Pièges).
- Fin de tâche : mini-quiz de 5 questions, puis mise à jour de ce fichier.
- Ne pas démarrer le trial Fabric avant P3.
- Ne jamais écrire de secret, d'ID d'abonnement ou de tenant, ni d'e-mail, dans Git ni dans une réponse.

### Résultat du step 2.3

- Branche de travail créée : `feature/t2-terraform`.
- `Microsoft.Storage` vérifié et déjà enregistré.
- `terraform init`, `terraform fmt` et `terraform validate` réussis.
- Provider `azurerm` verrouillé en version 5.12.0 dans `.terraform.lock.hcl`.
- Resource Group, Storage Account ADLS Gen2 et filesystem `landing` créés avec `terraform apply`.
- Second `terraform plan` : `No changes`.
- `terraform.tfvars`, `.terraform/` et `terraform.tfstate` restent ignorés par Git.
- Quiz T2.3 : 5/5.

### Prochaine action

Step 2.4 : préparer Key Vault, ADF avec identité managée et RBAC.