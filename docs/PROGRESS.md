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

### Résultat du step 2.4

- `Microsoft.KeyVault` et `Microsoft.DataFactory` vérifiés et enregistrés.
- Key Vault créé avec l'autorisation RBAC.
- Data Factory créée avec une identité managée `SystemAssigned`.
- Rôle `Storage Blob Data Contributor` attribué à ADF sur le Storage Account.
- Rôle `Key Vault Secrets User` attribué à ADF sur le Key Vault.
- `terraform validate` réussi.
- `terraform apply` réussi : 4 ressources ajoutées, 0 modification, 0 destruction.
- Second `terraform plan` : `No changes`.
- Quiz T2.4 : 4/5.

### Prochaine action

Step 2.5 : créer le login SQL `adf_reader` en lecture seule et préparer son secret dans Key Vault.

### Résultat du step 2.5

- Script `legacy/create_adf_reader.sql` créé pour un login SQL dédié à ADF.
- Login `adf_reader` créé au niveau SQL Server.
- Utilisateur `adf_reader` créé dans `LegacyRetail`.
- Accès limité au rôle `db_datareader`.
- Secret `sql-adf-reader-password` créé dans Key Vault.
- Rôle `Key Vault Secrets Officer` attribué à l’identité Azure courante pour gérer le secret.
- `terraform plan` final : `No changes`.
- Quiz T2.5 : 5/5.

### Prochaine action

Step 2.6 : préparer le Self-hosted Integration Runtime (SHIR) pour la connexion ADF vers SQL Server local.

### Résultat du step 2.6

- Ressource SHIR `shir-retailmod-dev` créée avec Terraform.
- `terraform apply` réussi : 1 ressource ajoutée, 0 modification, 0 destruction.
- Second `terraform plan` : `No changes`.
- Extension Azure CLI `datafactory` vérifiée.
- Clé d'authentification récupérée sans être enregistrée ni partagée.
- Nœud SHIR installé et inscrit sur l'hôte Windows.
- Statut Azure Data Factory : `Running`.
- Quiz T2.6 : à compléter.

### Prochaine action

Step 2.7 : créer les linked services, les datasets et le premier pipeline ADF en full load vers ADLS Gen2.

### Résultat du step 2.7

- Linked Service Key Vault créé, testé et publié.
- Linked Service SQL Server créé, testé et publié via le SHIR.
- Linked Service ADLS Gen2 créé, testé et publié avec l'identité managée ADF.
- Dataset SQL `ds_sql_salesorderheader` créé.
- Dataset Parquet `ds_adls_salesorderheader_parquet` créé vers `landing/salesorderheader/full/salesorderheader.parquet`.
- Pipeline `pl_full_salesorderheader` créé et publié.
- Debug réussi : 28 470 lignes lues et 28 470 lignes copiées.
- Le volume reflète l'état courant de LegacyRetail, avancé de trois jours par rapport à J0.
- Quiz T2.7 : à compléter.

### Prochaine action

Step 2.8 : concevoir le pipeline générique piloté par métadonnées avec extraction incrémentale.
Réponses au quiz T2.7

### Résultat du step 2.8

- Stratégie retenue : fenêtre quotidienne basée sur `load_date`.
- Table `dbo.EtlTableConfig` créée pour piloter les extractions.
- Dataset `ds_sql_etl_table_config` créé.
- Pipeline `pl_incremental_generic` créé avec `Lookup → ForEach → Copy`.
- Dataset Parquet dynamique créé avec partition `load_date=AAAA-MM-JJ`.
- Extraction du 2014-05-01 réussie : 227 lignes lues et copiées.
- Relance du 2014-05-01 réussie : même volume, sans doublon apparent.
- Extraction vide du 2014-05-04 avant avancement de la source : 0 ligne, pipeline réussi.
- Source avancée au 2014-05-04 avec `dbo.usp_advance_one_day`.
- Extraction du 2014-05-04 réussie : 57 lignes lues et copiées.
- Quiz T2.8 : 5/5.

### Prochaine action

Step 2.9 : tester les artefacts ADF, vérifier les partitions et exporter les JSON ADF vers `adf/`.

### Résultat du step 2.9

- Dossier `adf/` créé pour versionner les artefacts ADF.
- Cinq objets ADF exportés en JSON :
  - `pl_full_salesorderheader`
  - `pl_incremental_generic`
  - `ds_sql_salesorderheader`
  - `ds_sql_etl_table_config`
  - `ds_adls_incremental_parquet`
- Les cinq fichiers JSON sont syntaxiquement valides.
- Aucun secret détecté dans les exports.
- Extraction vide testée avec succès : 0 ligne copiée.
- Relance du 2014-05-01 testée avec succès : 227 lignes copiées.
- Extraction du 2014-05-04 testée avec succès : 57 lignes copiées.
- Quiz T2.9 : 5/5.


## T3 — Bronze local

### Résultat de T3.1 à T3.5

- Source Bronze retenue : fichiers Parquet de la landing ADLS, sans lecture JDBC directe.
- Parquet full load téléchargé localement depuis ADLS Gen2.
- Environnement `.venv-bronze` créé avec Python 3.11.9.
- PySpark `3.5.5` et Delta Lake `3.2.0` installés et vérifiés.
- Source `LegacyRetail` remise à J0 : `2014-04-30`.
- Compte `adf_reader` recréé dans `LegacyRetail` avec le rôle `db_datareader`.
- Parquet full load recréé à J0 : 28 115 lignes.
- Script `bronze/bronze_salesorderheader.py` créé pour écrire une table Delta locale.
- Colonnes d'audit ajoutées : `load_date`, `source_system`, `ingestion_timestamp`.
- Partition `2014-04-30` chargée : 28 115 lignes.
- Partition `2014-05-01` chargée : 227 lignes.
- Table Delta vérifiée : 28 342 lignes au total.
- Rejouabilité vérifiée sur J0 et le 2014-05-01, sans doublon.
- Dossier `_delta_log` présent.
- Quiz T3 : 5/5.

### Décisions et limites

- Bronze est d'abord exécutée localement, avant son portage dans Fabric.
- Le script traite actuellement `SalesOrderHeader` uniquement.
- Le chemin `data/` reste local et ignoré par Git.
- Les avertissements Spark liés au plan ou au nettoyage des répertoires temporaires Windows ne bloquent pas le résultat.

### Prochaine action

T3.6 : ajouter une vérification simple de qualité des données Bronze avant de clôturer T3.

### Résultat du step T3.6

- Script `bronze/check_bronze_salesorderheader.py` créé.
- Contrôle du volume : 28 342 lignes.
- Contrôle des `SalesOrderID` nuls : 0.
- Contrôle des groupes dupliqués : 0.
- Contrôle des colonnes d'audit : aucune colonne manquante.
- Contrôles Bronze réussis.
- Quiz final T3 : 5/5.

### Résultat de la tâche T3

- Bronze locale construite à partir des fichiers Parquet de la landing ADLS.
- Environnement Python isolé avec Python 3.11.9, PySpark 3.5.5 et Delta Lake 3.2.0.
- Table Delta `data/bronze/salesorderheader` créée avec les colonnes d'audit `load_date`, `source_system` et `ingestion_timestamp`.
- Chargement initial J0 : 28 115 lignes dans la partition `2014-04-30`.
- Chargement incrémental : 227 lignes dans la partition `2014-05-01`.
- Total Bronze : 28 342 lignes.
- Rejouabilité vérifiée sur les deux partitions, sans doublon.
- Dossier `_delta_log` présent.
- Contrôles de qualité réussis.
- Les données locales du dossier `data/` restent ignorées par Git.

### Prochaine action

Commencer T4 : Silver locale, nettoyage, contrôles de qualité et préparation du SCD2.

## T4 — Silver locale et SCD2

### Résultats

- Silver `SalesOrderHeader` créée à partir de Bronze.
- 28 342 lignes nettoyées et typées.
- Contrôles Silver réussis : clés non nulles, aucun doublon, montants valides.
- Snapshots Customer J0 et 2014-05-01 extraits via ADF.
- Dimension Customer SCD2 créée dans `data/silver/customer`.
- 17 406 clients J0 traités.
- 46 lignes de changement traitées.
- 15 anciennes versions clôturées.
- 46 nouvelles versions créées au 2014-05-01.
- Total SCD2 : 17 452 lignes.
- Aucune version courante multiple.
- Périodes invalides : 0.
- Quiz T4 : 4/5.

### Décisions et limites

- Silver est exécutée localement avec PySpark et Delta Lake.
- `Customer` est la première dimension historisée en SCD2.
- Le script SCD2 traite actuellement J0 et une seule journée de changement.
- Le portage Fabric est prévu en phase P3.

### Prochaine action

Commencer T5 : modèle Gold en étoile et réconciliation avec le legacy.

## T5 — Gold locale

### Jalon T5.4

- Modèle en étoile Delta créé localement.
- `dim_customer` créée avec 17 452 versions SCD2.
- `dim_date` créée avec 1 067 dates.
- `dim_territory` créée avec 10 territoires.
- `fact_sales` créée avec 28 342 commandes.
- Jointure temporelle avec Customer SCD2 validée.
- Aucun fait sans `customer_sk`.
- Aucun `SalesOrderID` dupliqué.
- Aucun fait sans `date_key`.
- Contrôles Gold réussis.

### Prochaine action

T5.5 : réconcilier les volumes et montants Gold avec `LegacyRetail`.

### T5.5 — Réconciliation Gold / Legacy

- Réconciliation effectuée entre `fact_sales` et `LegacyRetail`.
- Résultats identiques :
  - Commandes : 28 342
  - SubTotal : 107890830.3639
  - TaxAmt : 10030530.3770
  - Freight : 3134541.4001
- Le modèle Gold conserve donc les volumes et mesures du système legacy.
- T5 terminé.
- Trial Fabric toujours non démarré, conformément au planning.

Quiz T5 : 5/5.