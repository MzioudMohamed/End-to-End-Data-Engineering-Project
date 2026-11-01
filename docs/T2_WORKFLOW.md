# Tâche T2 — Workflow complet de l'ingestion Azure

## 1. Vue générale du workflow du projet

Le projet modernise une plateforme décisionnelle legacy SQL Server vers Azure et Microsoft Fabric.

Le workflow global est :

```text
SQL Server LegacyRetail
        |
        | Self-hosted Integration Runtime
        v
Azure Data Factory
        |
        | Copy Activity
        v
ADLS Gen2 - landing
        |
        | Shortcut OneLake
        v
Fabric Bronze
        |
        v
Fabric Silver
        |
        v
Fabric Gold
        |
        v
Power BI Direct Lake