# =============================================================================
# deploy-lambdas.ps1 — Lab 4: Cria as 5 funções Lambda para o Step Functions
# Ambiente: Windows / PowerShell
# Pré-requisitos: AWS CLI configurado (aws configure), permissões IAM,
#                 PowerShell 5.1+ ou PowerShell 7+
# =============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Configurações — ajuste se necessário
# ---------------------------------------------------------------------------
$REGION   = aws configure get region
if (-not $REGION) { $REGION = "us-east-1" }

$ACCOUNT_ID = (aws sts get-caller-identity --query "Account" --output text)
$RUNTIME    = "python3.12"
$ROLE_NAME  = "lab4-lambda-basic-role"

$FUNCTIONS = @(
    @{ Name = "lab4-validate-order";   File = "lambda_validate_order.py";   Handler = "lambda_validate_order.lambda_handler" }
    @{ Name = "lab4-process-premium";  File = "lambda_process_premium.py";  Handler = "lambda_process_premium.lambda_handler" }
    @{ Name = "lab4-process-standard"; File = "lambda_process_standard.py"; Handler = "lambda_process_standard.lambda_handler" }
    @{ Name = "lab4-notify-customer";  File = "lambda_notify_customer.py";  Handler = "lambda_notify_customer.lambda_handler" }
    @{ Name = "lab4-finalize-order";   File = "lambda_finalize_order.py";   Handler = "lambda_finalize_order.lambda_handler" }
)

# ---------------------------------------------------------------------------
# Helper: escreve com cor
# ---------------------------------------------------------------------------
function Write-Step { param($msg) Write-Host "`n>>> $msg" -ForegroundColor Cyan }
function Write-Ok   { param($msg) Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "    [WARN] $msg" -ForegroundColor Yellow }

# ---------------------------------------------------------------------------
# 1. Garantir IAM Role básica para Lambda
# ---------------------------------------------------------------------------
Write-Step "Verificando IAM Role '$ROLE_NAME'..."

$ROLE_ARN = aws iam get-role --role-name $ROLE_NAME --query "Role.Arn" --output text 2>$null
if ($LASTEXITCODE -ne 0 -or -not $ROLE_ARN) {
    Write-Warn "Role nao encontrada. Criando..."

    $TRUST_POLICY = @"
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "lambda.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
"@

    $TRUST_FILE = [System.IO.Path]::GetTempFileName() + ".json"
    $TRUST_POLICY | Set-Content -Encoding UTF8 $TRUST_FILE

    $ROLE_ARN = aws iam create-role `
        --role-name $ROLE_NAME `
        --assume-role-policy-document "file://$TRUST_FILE" `
        --query "Role.Arn" --output text

    aws iam attach-role-policy `
        --role-name $ROLE_NAME `
        --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" | Out-Null

    Remove-Item $TRUST_FILE -Force
    Write-Ok "Role criada: $ROLE_ARN"
    Write-Warn "Aguardando 10s para propagacao da role na AWS..."
    Start-Sleep -Seconds 10
} else {
    Write-Ok "Role ja existe: $ROLE_ARN"
}

# ---------------------------------------------------------------------------
# 2. Criar/atualizar cada função Lambda
# ---------------------------------------------------------------------------
$ARNS = @{}

foreach ($fn in $FUNCTIONS) {
    Write-Step "Processando: $($fn.Name)"

    # Zipar o arquivo .py
    $ZIP_PATH = Join-Path $PSScriptRoot "$($fn.Name).zip"
    Compress-Archive -Path (Join-Path $PSScriptRoot $fn.File) -DestinationPath $ZIP_PATH -Force
    Write-Ok "Arquivo zipado: $($fn.Name).zip"

    # Verificar se a função já existe
    $EXISTS = aws lambda get-function --function-name $fn.Name --region $REGION --query "Configuration.FunctionArn" --output text 2>$null

    if ($LASTEXITCODE -eq 0 -and $EXISTS) {
        # Atualizar código existente
        $ARN = aws lambda update-function-code `
            --function-name $fn.Name `
            --zip-file "fileb://$ZIP_PATH" `
            --region $REGION `
            --query "FunctionArn" --output text
        Write-Ok "Codigo atualizado."
    } else {
        # Criar nova função
        $ARN = aws lambda create-function `
            --function-name $fn.Name `
            --runtime $RUNTIME `
            --role $ROLE_ARN `
            --handler $fn.Handler `
            --zip-file "fileb://$ZIP_PATH" `
            --timeout 30 `
            --region $REGION `
            --query "FunctionArn" --output text
        Write-Ok "Funcao criada."
    }

    $ARNS[$fn.Name] = $ARN
    Remove-Item $ZIP_PATH -Force
}

# ---------------------------------------------------------------------------
# 3. Exibir ARNs para uso na definição ASL
# ---------------------------------------------------------------------------
Write-Host "`n============================================================" -ForegroundColor Magenta
Write-Host " ARNs das Lambdas — cole no state-machine-definition.json" -ForegroundColor Magenta
Write-Host "============================================================" -ForegroundColor Magenta

foreach ($entry in $ARNS.GetEnumerator()) {
    Write-Host ""
    Write-Host "  $($entry.Key)" -ForegroundColor Yellow
    Write-Host "  $($entry.Value)"
}

Write-Host "`n============================================================" -ForegroundColor Magenta
Write-Host " Substitua os placeholders ARN_lab4-* no arquivo ASL acima" -ForegroundColor Magenta
Write-Host "============================================================`n" -ForegroundColor Magenta
