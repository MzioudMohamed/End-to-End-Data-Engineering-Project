# Spécification du projet : modernisation d'un décisionnel legacy vers Microsoft Fabric

> Document de référence pour Copilot et pour l'utilisateur. L'état d'avancement est dans `docs/PROGRESS.md`.
> Les passages marqués **(à valider)** sont des propositions : présente les options et recommande, mais laisse l'utilisateur trancher.
> Les noms de ressources, régions et versions ci-dessous étaient exacts fin octobre 2026 ; vérifie dans la documentation officielle
> ce qui change vite (Azure, Terraform, Fabric).

## 1. Objectifs et contraintes

**Objectifs**
- **Éducatif** : apprendre comment un pipeline data s'implémente de bout en bout en production ; chaque techno inconnue est apprise
  sur une petite brique avant d'être intégrée.
- **Valeur CV** : projet crédible face à un recruteur marocain (Azure Data Factory et Microsoft Fabric sont indispensables).

**Contraintes**

| Contrainte | Détail |
|---|---|
| Budget | 0 € (projet éducatif, ne tourne pas durablement) |
| Temps | 4 h par jour, environ 10 semaines |
| Machine | Windows 11, 16 Go de RAM, SSD de 100 Go |
| Conteneurisation | Obligatoire (Docker Compose) |
| Code | Simple, peu de scripts, explicable ligne par ligne, bonnes pratiques respectées |
| Cible emploi | Générale (pas d'employeur ni de secteur imposé) |

## 2. Profil de l'utilisateur

Junior. Niveaux de 0 (jamais vu) à 3 (à l'aise) :

| Domaine | Niveau | Domaine | Niveau |
|---|---|---|---|
| SQL / T-SQL | 3 | Power BI | 2 |
| Python / PySpark | 2 | Azure (Entra ID, Key Vault, RBAC) | 0 |
| SQL Server | 2 | Terraform | 0 |
| SSIS | 0 | Docker | 2 |
| Azure Data Factory | 0 | GitHub Actions / CI-CD | 0 |
| Microsoft Fabric | 0 | Delta Lake | 0 |
| Architecture médaillon | 2 | Modélisation dimensionnelle (étoile, SCD2) | 2 |

## 3. Architecture cible

```
┌─ Docker Compose (local) ─────────────────┐
│ SQL Server : LegacyRetail                │      API REST
│ dossier CSV                              │      (ex. jours fériés)
└──────────────┬───────────────────────────┘          │
               │ SHIR (installé sur l'hôte Windows)   │
               ▼                                      ▼
      ┌──────────────── Azure (Terraform) ───────────────┐
      │ ADF : 1 pipeline générique (Lookup → ForEach → Copy)
      │                  ▼
      │ ADLS Gen2 /landing (Parquet, partition load_date)
      │ Key Vault · Log Analytics
      └──────────────────┬───────────────────────────────┘
                         │ shortcut OneLake
      ┌──────────────────▼──────── Fabric (dev / prod) ──┐
      │ Bronze ─► Silver ─► Gold ─► Power BI (Direct Lake)
      │ Notebooks PySpark · T-SQL · Fabric Pipeline
      └──────────────────────────────────────────────────┘
```

**Pourquoi ADF et Fabric ensemble**
- ADF extrait le legacy : fort sur l'hybride (self-hosted integration runtime) et CI/CD mature (templates ARM).
- Fabric transforme et sert : médaillon, Warehouse, Power BI.
- Scénario réaliste : une entreprise qui a déjà ADF et adopte Fabric. Microsoft propose un parcours de migration ADF vers Fabric,
  à citer comme évolution (bonus de fin de projet).
- ADLS `landing` découple l'extraction de la transformation, permet de rejouer et sert d'audit.

## 4. Technologies par étape

| Étape | Technologies |
|---|---|
| Source legacy | SQL Server 2022 (Docker), T-SQL ; SSIS : 1 package optionnel limité à une journée |
| Ingestion | Azure Data Factory, SHIR, connecteur REST |
| Landing | ADLS Gen2, Key Vault |
| Bronze / Silver | Fabric Lakehouse, shortcut OneLake, PySpark, Delta Lake (`MERGE` pour le SCD2) |
| Gold | Fabric Warehouse ou Lakehouse (à trancher en T5), T-SQL |
| BI | Power BI (Direct Lake) |
| Orchestration | Fabric Pipelines, déclencheurs ADF |
| Qualité et sécurité | pytest, contrôles dans les notebooks, Key Vault, Entra ID (RBAC) |
| IaC | Terraform (`azurerm` 5.x et `microsoft/fabric`) |
| CI/CD | GitHub Actions, OIDC, `fabric-cicd`, export ARM d'ADF |
| Monitoring | Azure Monitor, Log Analytics (minimal : 1 diagnostic setting + 1 alerte) |
| Conteneurs | Docker Compose (SQL Server ; plus tard image dev/CI avec PySpark et pytest) |

**Volontairement coupé ou simplifié** : Purview (remplacé par le lineage et le catalogue OneLake natifs, avec captures), Azure-SSIS IR
(coûteux), Dataflow Gen2 (optionnel, un seul usage), simulateur Python (remplacé par du T-SQL), environnements multiples côté Azure
(un seul resource group au départ).

## 5. Source legacy

### 5.1 AdventureWorks2022 (archive)
Base OLTP de Microsoft restaurée dans le conteneur (`legacy/restore_adventureworks.sql`). Ventes du 31 mai 2011 au 30 juin 2014 :
31 465 commandes, 121 317 lignes de détail. Volume faible, voulu : la valeur vient des patterns d'ingénierie. Le pipeline **ne lit
jamais** AdventureWorks, uniquement `LegacyRetail`.

### 5.2 Pourquoi une base `LegacyRetail`
AdventureWorks est figée : ni incrémental ni SCD2 ne sont démontrables. `LegacyRetail` joue le legacy vivant. Aucun script Python :
la simulation est en T-SQL.

### 5.3 Tables de `LegacyRetail` (schéma `dbo`)

| Table | Colonnes principales | Lignes à J0 |
|---|---|---|
| `Territory` | TerritoryID, Name, CountryRegionCode, TerritoryGroup | 10 |
| `ProductCategory` | ProductCategoryID, Name | 4 |
| `ProductSubcategory` | ProductSubcategoryID, ProductCategoryID, Name | 37 |
| `Product` | ProductID, Name, ProductNumber, Color, StandardCost, ListPrice, ProductSubcategoryID | 504 |
| `Customer` | CustomerID, CustomerName, CustomerType ('Individual' ou 'Store'), TerritoryID | 17 406 |
| `SalesOrderHeader` | SalesOrderID, OrderDate, CustomerID, TerritoryID, OnlineOrderFlag, SubTotal, TaxAmt, Freight | 28 115 |
| `SalesOrderDetail` | SalesOrderDetailID, SalesOrderID, ProductID, OrderQty, UnitPrice, UnitPriceDiscount, LineTotal | 110 561 |
| `SimulationState` | Id (=1), LastDay | 1 |

Toutes les tables (sauf `SimulationState`) ont `ModifiedDate datetime2(0)`, avec un index sur les tables à watermark, qui sert
de colonne de suivi des changements. Il n'y a pas de clés étrangères (PK seulement).

### 5.4 Règles de la simulation
- **J0 = 2014-04-30** : état initial. Référentiels et dimensions estampillés J0 ; commandes estampillées à leur date de commande.
  Seuls les clients ayant déjà commandé sont chargés.
- **61 jours rejouables** : du 2014-05-01 au 2014-06-30.
- `dbo.usp_advance_one_day` (fichier `legacy/advance_one_day.sql`) rejoue le jour suivant `LastDay` : nouveaux clients, commandes et
  lignes du jour, 15 clients changent de territoire (`TerritoryID % 10 + 1`), 3 produits augmentent de 5 % (`ListPrice`).
  Les lignes modifiées reçoivent `ModifiedDate` = minuit du jour simulé. Le choix des lignes est reproductible
  (`CHECKSUM(id, @day)`).
- Le jour est **atomique** (transaction, `XACT_ABORT ON`). Une erreur n'avance pas `LastDay`. Au-delà de la dernière date de
  l'archive, la procédure lève l'erreur 50001.
- La procédure n'est **pas idempotente** (chaque appel avance d'un jour), c'est voulu : elle simule le temps. C'est le **pipeline**
  qui doit être idempotent.
- `legacy/create_legacy_retail.sql` supprime et recrée `LegacyRetail` : c'est le bouton de remise à zéro (retour à J0).
- **Le legacy ne garde que l'état courant** : une ligne modifiée écrase l'ancienne valeur. C'est ce qui rend le SCD2 pertinent :
  l'historique est reconstruit par le pipeline à partir des extractions quotidiennes.

### 5.5 Constats vérifiés
- Le premier jour rejoué (2014-05-01) a produit 227 commandes, 46 lignes de clients modifiées (15 changements de territoire plus
  les nouveaux clients) et 3 produits repriced (ProductID 514, 515, 517).
- **Le `ModifiedDate` d'AdventureWorks n'est pas fiable** : décalé d'environ 7 jours sur les commandes, une seule valeur pour
  `Customer`, deux pour `Product`, dates jusqu'en 2015 pour `Person`. D'où le contrôle de `ModifiedDate` dans `LegacyRetail`.
- Un jour peut ne rien changer pour une table (les référentiels `Territory`, `ProductCategory`, `ProductSubcategory` renvoient 0 ligne
  en incrémental) : une extraction vide ne doit **ni faire échouer le pipeline ni avancer un watermark à tort**.
- **Point d'attention T2** : la source a été avancée de 3 jours pour les tests (`LastDay` = 2014-05-03). Les lignes modifiées depuis J0
  ont perdu leur valeur de J0 (`Customer.TerritoryID`, `Product.ListPrice`). Un chargement initial « tel que J0 » n'est donc plus exact.
  **Avant le chargement initial, remettre la source à J0** en relançant `legacy/create_legacy_retail.sql` (action destructive, à faire
  confirmer par l'utilisateur), puis rejouer les jours un par un en parallèle des exécutions du pipeline.

### 5.6 Limites assumées (à écrire dans le README)
- Un watermark sur `ModifiedDate` **ne voit pas les `DELETE`** ; en production : CDC ou Change Tracking.
- Volume faible. La valeur du projet : incrémental, SCD2, tests, IaC, CI/CD, réconciliation.

## 6. Principes de production

- **Idempotence** : relancer un jour réécrit la partition `load_date` correspondante, sans doublon.
- **Incrémental** : extraction pilotée par `ModifiedDate` ; chargement initial distinct des chargements quotidiens.
- **Reprise sur erreur** : un jour en échec se relance seul.
- **SCD2** : dates de validité et indicateur de version courante ; la première version est valide depuis l'origine pour que les faits
  antérieurs à J0 retrouvent leur dimension.
- **Secrets** : jamais dans Git (`.env` et `terraform.tfvars` ignorés, Key Vault côté Azure, OIDC en CI, clé d'authentification du SHIR
  jamais commitée).
- **Environnements** : 2 workspaces Fabric (dev, prod) rattachés au même trial.
- **Coûts et observabilité** : alerte de budget, un diagnostic setting, une alerte.

## 7. Environnements, accès et coûts

- **Poste** : un SQL Server Windows est aussi installé (port 1433). Le conteneur est donc exposé sur le port **1434**
  (connexion `localhost,1434`, option *Trust server certificate*). Arrêter le service SQL Server Windows économise de la RAM.
  `.wslconfig` limite WSL2 à 6 Go. Un navigateur sur `localhost:1434` affiche une erreur : c'est normal (protocole TDS, pas HTTP).
- **Fabric** : tenant universitaire (ancien) ; le trial de 60 jours est **disponible mais non démarré**. Il démarre en phase P3.
  La licence actuelle est « Compte gratuit ». Le compte universitaire est un compte professionnel/scolaire (Entra) : il convient pour
  Fabric mais **ne peut pas créer d'abonnement Azure** (l'inscription affiche « type de compte non pris en charge »).
- **Azure** : abonnement **Azure for Students** actif (100 $ de crédit, 12 mois, sans carte). Obtenu en se connectant avec **GitHub**
  (Student Developer Pack actif) ; la vérification par e-mail scolaire avait échoué. Le compte Microsoft associé a été créé via
  GitHub : se reconnecter au portail et à la CLI avec *Sign-in options → GitHub*. L'abonnement est non transférable : ne pas relancer
  d'inscription. Validation d'adresse impossible pour le Maroc : utiliser « Utiliser cette adresse ».
- **Tenants** : l'abonnement Azure est dans un tenant **différent** de celui de Fabric. Authentifications séparées, traitées au moment
  du shortcut (P3) et du CI/CD (T8).
- **Régions autorisées par la policy** d'Azure for Students : `switzerlandnorth`, `denmarkeast`, `francecentral`, `spaincentral`,
  `austriaeast`. **Région retenue : `francecentral`** (mature, tous les services nécessaires). Les tests de validation de Storage ADLS
  Gen2, Data Factory et Key Vault ont réussi. Un budget a été créé dans Cost Management.
- **Service principals** : la création d'une app registration est possible dans le tenant universitaire (testé). Non vérifié : le
  paramètre de tenant qui autorise les service principals à appeler les APIs Fabric (géré par un administrateur). Fallback :
  intégration Git de Fabric et `fabric-cicd` en local ; le reste du CI/CD reste dans GitHub Actions.
- **Terraform** : `azurerm` est en version **5.x** (5.0 en juillet 2026). Le provider **n'enregistre aucun resource provider par
  défaut** : vérifier `az provider show -n <Namespace> --query registrationState -o tsv` et enregistrer au besoin
  (`Microsoft.Storage`, `Microsoft.KeyVault`, `Microsoft.DataFactory`, plus tard `Microsoft.OperationalInsights`).
- **SHIR et gateway** : composants Windows, installés sur l'hôte (hors Docker).

## 8. Plan de réalisation

### 8.1 Tâches (une tâche = une étape du pipeline)

| # | Tâche | Livrable |
|---|---|---|
| T1 | Environnement et source legacy | Source rejouable par `docker compose up` et scripts SQL versionnés |
| T2 | Ingestion (legacy vers landing) | Terraform (RG, ADLS, Key Vault, ADF), SHIR, fichiers Parquet quotidiens dans `landing` |
| T3 | Bronze | Tables Delta brutes avec colonnes d'audit, d'abord en local, puis dans Fabric |
| T4 | Silver | Tables nettoyées et historisées (SCD2) |
| T5 | Gold | Modèle en étoile et réconciliation avec le legacy |
| T6 | Orchestration | Exécution quotidienne de bout en bout, reprise sur erreur |
| T7 | Qualité et sécurité | Tests pytest, contrôles de qualité, Key Vault, RBAC |
| T8 | IaC et CI/CD | Terraform étendu à Fabric, GitHub Actions, déploiement dev vers prod |
| T9 | Monitoring | Journaux dans Log Analytics et alerte |
| T10 | BI et documentation | Rapport Power BI, README, schémas, courte vidéo |

### 8.2 Phases (~10 semaines)

| Phase | Semaines | Contenu | Coût |
|---|---|---|---|
| P1 | 1-2 | Docker Compose, `LegacyRetail`, PySpark et Delta en local (Bronze, Silver, SCD2), pytest, CI minimale | 0 € |
| P2 | 3-4 | Terraform (RG, ADLS, Key Vault, ADF), SHIR, pipeline ADF vers `landing` | Crédit Azure |
| P3 | 5-7 | **Démarrage du trial Fabric** ; Lakehouse, shortcut, notebooks portés, Gold, Pipelines, Power BI | Trial |
| P4 | 8-9 | CD (`fabric-cicd`, ARM d'ADF), dev et prod, monitoring | Trial |
| P5 | 10 | README, schémas, réconciliation legacy contre Gold, vidéo et captures | 0 € |

Après le trial, la capacité Fabric disparaît : tout doit être rejouable depuis Git, avec captures et vidéo.

## 9. Tâche T2 : ingestion (legacy vers landing)

**Objectif** : chaque jour, ADF extrait les changements de `LegacyRetail` vers ADLS Gen2, sous
`landing/<table>/load_date=AAAA-MM-JJ/`. Relancer un jour écrase la même partition, sans doublon.

| Step | Contenu | Apprentissage | Statut |
|---|---|---|---|
| 2.1 | Abonnement Azure, régions autorisées, tests de validation, budget | Azure Policy, tenants | Fait |
| 2.2 | Azure CLI et Terraform (`winget`), `az login`, `az account show`, `terraform -version` | CLI, tenant | À confirmer |
| 2.3 | Terraform brique 1 : resource group + storage ADLS Gen2 + filesystem `landing` | Terraform, state | **Prochain** (fichiers fournis) |
| 2.4 | Terraform : Key Vault + ADF (identité managée) + rôles RBAC | Key Vault, RBAC | À faire |
| 2.5 | Login SQL en lecture seule (pas `sa`), secret dans Key Vault | Moindre privilège | À faire |
| 2.6 | SHIR : ressource Terraform, installation sur l'hôte, connexion à `localhost,1434` | Integration Runtime | À faire |
| 2.7 | Premier pipeline : Copy d'une table en full load vers Parquet | Copy activity | À faire |
| 2.8 | Pipeline générique : Lookup (config) → ForEach → Copy, avec extraction incrémentale | Pipelines pilotés par métadonnées | À faire |
| 2.9 | Tests : relance du même jour, extraction vide, jours suivants ; export JSON vers Git (`adf/`) | Idempotence | À faire |

### 9.1 Step 2.3 : fichiers Terraform fournis (dossier `infra/`)

| Fichier | Contenu |
|---|---|
| `providers.tf` | Terraform ≥ 1.9, provider `hashicorp/azurerm ~> 5.0`, `subscription_id` issu d'une variable, `features {}`. Authentification par `az login`. |
| `variables.tf` | `subscription_id` ; `location` (défaut `francecentral`, validation sur les 5 régions autorisées) ; `project` (défaut `retailmod`) ; `env` (défaut `dev`) ; `suffix` (2 à 6 caractères `[a-z0-9]`, validé) |
| `main.tf` | `locals.tags` ; `azurerm_resource_group.main` (`rg-<project>-<env>`) ; `azurerm_storage_account.lake` (`st<project><env><suffix>`, Standard, LRS, StorageV2, `is_hns_enabled`, TLS 1.2, pas d'accès public) ; `azurerm_storage_data_lake_gen2_filesystem.landing` (`landing`, via `storage_account_id`) |
| `outputs.tf` | `resource_group_name`, `storage_account_name`, `landing_filesystem` |
| `terraform.tfvars.example` | Modèle à copier en `terraform.tfvars` (ID d'abonnement via `az account show --query id -o tsv`, suffixe unique) |

Préparation : ajouter `*.tfvars` au `.gitignore`. Vérifier l'enregistrement de `Microsoft.Storage`. Exécution : `terraform init`, `fmt`,
`validate`, `plan` (attendu : 3 à ajouter), `apply`, puis un second `plan` (attendu : « No changes »). Commiter `infra/` y compris
`.terraform.lock.hcl`, jamais `terraform.tfvars`, `.terraform/` ni `*.tfstate`.

Pièges : `StorageAccountAlreadyTaken` (changer le suffixe), `MissingSubscriptionRegistration` (resource provider à enregistrer),
mauvais abonnement actif (`az account set`), suppression du `terraform.tfstate` (Terraform oublie ses ressources).
Ces fichiers n'ont pas pu être validés par `terraform validate` lors de leur génération : si une erreur d'attribut apparaît (provider
5.x), consulter la documentation du provider et corriger.

### 9.2 Propositions de conception pour 2.4 à 2.9 **(à valider)**
- **Key Vault** (2.4) : autorisation par RBAC. **ADF** avec identité managée de type System-assigned. Rôles : identité d'ADF →
  `Storage Blob Data Contributor` sur le storage et `Key Vault Secrets User` sur le Key Vault ; l'utilisateur → `Key Vault Secrets Officer`
  pour créer le secret. Les rôles mettent quelques minutes à se propager. Enregistrer `Microsoft.KeyVault` et `Microsoft.DataFactory`.
  Vérifier les noms d'attributs de `azurerm_key_vault` et `azurerm_data_factory` dans la documentation du provider 5.x.
- **Compte de lecture** (2.5) : login `adf_reader` avec `db_datareader` sur `LegacyRetail` uniquement ; mot de passe fort stocké dans le
  Key Vault (secret) et jamais dans Git. **Attention** : `DROP DATABASE` supprime l'utilisateur de base mais pas le login ; recréer le
  mapping de l'utilisateur après chaque remise à zéro (par exemple à la fin de `create_legacy_retail.sql`, gardé par un test d'existence
  du login).
- **SHIR** (2.6) : ressource Terraform d'integration runtime auto-hébergé, puis installation sur l'hôte Windows et enregistrement avec
  la clé d'authentification (**secret : ne jamais la commiter**). Connexion à `localhost,1434`.
- **Linked services** (2.7) : SQL Server via le SHIR (mot de passe lu dans Key Vault), ADLS Gen2 par identité managée, Key Vault par
  identité managée. Datasets paramétrés.
- **Format de landing** : `landing/<table>/load_date=AAAA-MM-JJ/<table>.parquet`. Le **nom de fichier fixe** fait qu'une relance écrase
  le fichier (idempotence).
- **Chargement initial** : extraction complète (`ModifiedDate <= '2014-04-30'`) vers la partition `load_date=2014-04-30`
  (`load_type = full`), **après remise de la source à J0** (voir section 5.5).
- **Chargement quotidien** : paramètre `load_date` du pipeline ; fenêtre
  `ModifiedDate >= @load_date AND ModifiedDate < DATEADD(DAY, 1, @load_date)`. Idempotent par construction.
  Alternative à discuter en 2.8 : watermark persisté (table de contrôle ou fichier dans ADLS), plus complexe à rendre idempotent.
- **Configuration** : une liste de tables (schéma, table, `load_type`, colonne de watermark) lue par un Lookup ; un seul pipeline
  générique, pas un pipeline par table.
- **Extraction vide** : ne pas échouer, tracer « 0 ligne » ; décider en 2.8 s'il faut écrire un fichier vide ou rien.

## 10. Structure du dépôt

**Actuelle**
```
.
├── docker-compose.yml          # service sqlserver (port 1434, healthcheck, volume, montage ./legacy/backup)
├── .env.example
├── .gitignore                  # à compléter avec *.tfvars
├── .github/
│   └── copilot-instructions.md
├── legacy/
│   ├── restore_adventureworks.sql
│   ├── create_legacy_retail.sql
│   └── advance_one_day.sql
├── infra/                      # step 2.3 : providers.tf, variables.tf, main.tf, outputs.tf, terraform.tfvars.example
└── docs/                       # PROJECT.md, PROGRESS.md ; journal.md à confirmer
```
Le `README.md` **n'existe pas encore**.

**Cible** : `adf/` (export JSON), `fabric/notebooks/` (~4 notebooks), `sql/` (~3 fichiers T-SQL pour le Gold), `tests/` (pytest),
`.github/workflows/` (`ci.yml`, `deploy.yml`), `Dockerfile` (image dev/CI, plus tard), `README.md`.

## 11. Décisions figées

- Source : AdventureWorks2022 en archive, `LegacyRetail` comme legacy vivant, J0 = 2014-04-30, simulation en T-SQL (pas de Python).
- Architecture : ADF extrait, ADLS `landing`, Fabric transforme et sert.
- SQL Server conteneurisé sur le port 1434. Le pipeline ne lit jamais AdventureWorks.
- Trial Fabric démarré seulement en P3.
- Azure : abonnement Azure for Students, région `francecentral`, un seul resource group au départ.
- Terraform : `azurerm ~> 5.0`, état local ignoré par Git, `terraform.tfvars` ignoré, nommage `rg-<projet>-<env>` et
  `st<projet><env><suffixe>`, ADLS Gen2 créé avec `azurerm_storage_data_lake_gen2_filesystem`.
- Scripts générés par Copilot avec une fiche (Quoi / Pourquoi / Pourquoi maintenant / Pièges) ; README et journal écrits par l'utilisateur.

## 12. Décisions ouvertes

- Gold dans le Warehouse (T-SQL) ou le Lakehouse (Delta) : à trancher en T5.
- Lecture locale du Bronze : directement depuis SQL Server (JDBC) ou via un export : à trancher en T3.
- Extraction quotidienne : fenêtre par `load_date` ou watermark persisté : à trancher en 2.8.
- Recréation de l'utilisateur `adf_reader` après remise à zéro : à trancher en 2.5.
- SSIS : un seul package limité à une journée, abandonné s'il bloque.
- Dataflow Gen2 : optionnel. Purview : bonus éventuel.
- Authentification CI/CD de Fabric : dépend du paramètre de tenant sur les service principals.

## 13. Risques et parades

| Risque | Parade |
|---|---|
| Régions limitées par la policy d'Azure for Students | Liste connue, `location` validée dans `variables.tf` |
| Changements incompatibles de `azurerm` 5.x | Vérifier la documentation du provider, `terraform validate` avant `plan` |
| Resource providers non enregistrés | Vérifier `az provider show` avant chaque nouveau type de ressource |
| Source avancée au-delà de J0 | Remise à J0 avant le chargement initial (section 5.5) |
| Trial Fabric limité à 60 jours | Démarrage tardif, tout rejouable depuis Git, captures et vidéo |
| Service principals non autorisés sur les APIs Fabric | Intégration Git de Fabric et `fabric-cicd` en local |
| Deux tenants (Azure et Fabric) | Authentifications séparées, traitées en P3 et T8 |
| RAM de 16 Go | `.wslconfig` à 6 Go, mémoire SQL Server plafonnée, arrêt du SQL Server Windows |
| Dataset de tutoriel | Valeur portée par l'ingénierie (incrémental, SCD2, tests, IaC, CI/CD, réconciliation) |
| Dépassement des crédits Azure | Alerte de budget, ressources détruites hors session |
