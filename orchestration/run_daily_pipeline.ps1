param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d{4}-\d{2}-\d{2}$')]
    [string]$LoadDate
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$python = "python"
$salesOrderHeaderPath = ".\data\landing\salesorderheader\salesorderheader_$LoadDate.parquet"
$customerPath = ".\data\landing\customer\customer_$LoadDate.parquet"

function Invoke-PipelineStep {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [scriptblock]$Action
    )

    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan

    & $Action

    if ($LASTEXITCODE -ne 0) {
        throw "L'étape '$Name' a échoué avec le code $LASTEXITCODE."
    }

    Write-Host "Étape réussie : $Name" -ForegroundColor Green
}

try {
    [datetime]::ParseExact(
        $LoadDate,
        "yyyy-MM-dd",
        [Globalization.CultureInfo]::InvariantCulture
    ) | Out-Null

    if (-not (Test-Path -LiteralPath $salesOrderHeaderPath -PathType Leaf)) {
        throw "Fichier SalesOrderHeader introuvable : $salesOrderHeaderPath"
    }

    if (-not (Test-Path -LiteralPath $customerPath -PathType Leaf)) {
        throw "Fichier Customer introuvable : $customerPath"
    }

    Write-Host "Début du pipeline pour : $LoadDate" -ForegroundColor Yellow

    Invoke-PipelineStep "Chargement Bronze SalesOrderHeader" {
        & $python ".\bronze\bronze_salesorderheader.py" `
            $salesOrderHeaderPath `
            $LoadDate
    }

    Invoke-PipelineStep "Transformation Silver SalesOrderHeader" {
        & $python ".\silver\silver_salesorderheader.py"
    }

    Invoke-PipelineStep "Contrôles Silver SalesOrderHeader" {
        & $python ".\silver\check_silver_salesorderheader.py"
    }

    Invoke-PipelineStep "Mise à jour SCD2 Customer" {
        & $python ".\silver\silver_customer_scd2.py" `
            "--changes-path" `
            $customerPath `
            "--change-date" `
            $LoadDate
    }

    Invoke-PipelineStep "Création Gold" {
        & $python ".\gold\gold_sales.py"
    }

    Invoke-PipelineStep "Contrôles Gold" {
        & $python ".\gold\check_gold_sales.py"
    }

    Write-Host ""
    Write-Host "Pipeline terminé avec succès pour : $LoadDate" `
        -ForegroundColor Green
}
catch {
    Write-Error "Pipeline échoué pour $LoadDate : $($_.Exception.Message)"
    exit 1
}
