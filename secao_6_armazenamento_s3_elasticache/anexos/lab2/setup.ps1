# setup.ps1 — Infraestrutura completa do Lab 2: S3 Events + Lambda
# Pré-requisito: AWS CLI configurado, lambda_function.py no diretório atual
#
# Como executar:
#   cd path\to\lab2
#   .\setup.ps1
#
# Caso PowerShell bloqueie a execução, rode antes:
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

$ErrorActionPreference = "Stop"

$ACCOUNT_ID    = aws sts get-caller-identity --query Account --output text
$BUCKET_NAME   = "dva-lab2-eventos-$ACCOUNT_ID"
$FUNCTION_NAME = "dva-lab2-s3-processor"
$ROLE_NAME     = "dva-lab2-lambda-s3-role"

Write-Host "=== Bucket: $BUCKET_NAME ==="
Write-Host "=== Função: $FUNCTION_NAME ==="
Write-Host ""

# 1. Criar IAM Role para a Lambda
Write-Host "[1/6] Criando IAM Role..."
aws iam create-role `
    --role-name $ROLE_NAME `
    --assume-role-policy-document file://lambda-trust-policy.json

$ROLE_ARN = aws iam get-role --role-name $ROLE_NAME --query Role.Arn --output text
Write-Host "Role ARN: $ROLE_ARN"

# 2. Anexar políticas à Role
Write-Host "[2/6] Anexando políticas..."
aws iam attach-role-policy `
    --role-name $ROLE_NAME `
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy `
    --role-name $ROLE_NAME `
    --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

Write-Host "Aguardando propagação da Role (10s)..."
Start-Sleep -Seconds 10

# 3. Empacotar e criar a função Lambda
Write-Host "[3/6] Criando função Lambda..."
Compress-Archive -Path lambda_function.py -DestinationPath lambda_function.zip -Force

aws lambda create-function `
    --function-name $FUNCTION_NAME `
    --runtime python3.12 `
    --role $ROLE_ARN `
    --handler lambda_function.lambda_handler `
    --zip-file fileb://lambda_function.zip `
    --timeout 30

$LAMBDA_ARN = aws lambda get-function `
    --function-name $FUNCTION_NAME `
    --query Configuration.FunctionArn `
    --output text
Write-Host "Lambda ARN: $LAMBDA_ARN"

# 4. Criar bucket S3
Write-Host "[4/6] Criando bucket S3..."
$REGION = aws configure get region
if ($REGION -eq "us-east-1") {
    aws s3api create-bucket --bucket $BUCKET_NAME
} else {
    aws s3api create-bucket `
        --bucket $BUCKET_NAME `
        --create-bucket-configuration LocationConstraint=$REGION
}

# 5. Adicionar resource-based policy na Lambda (S3 precisa de permissão para invocá-la)
Write-Host "[5/6] Adicionando resource-based policy na Lambda..."
aws lambda add-permission `
    --function-name $FUNCTION_NAME `
    --statement-id "S3InvokePermission" `
    --action "lambda:InvokeFunction" `
    --principal s3.amazonaws.com `
    --source-arn "arn:aws:s3:::$BUCKET_NAME" `
    --source-account $ACCOUNT_ID

# 6. Configurar notificação de eventos no bucket
Write-Host "[6/6] Configurando notificação de eventos no bucket..."
(Get-Content notification-config.json) -replace 'LAMBDA_ARN_PLACEHOLDER', $LAMBDA_ARN |
    Set-Content notification-config-filled.json

aws s3api put-bucket-notification-configuration `
    --bucket $BUCKET_NAME `
    --notification-configuration file://notification-config-filled.json

Remove-Item -Force -ErrorAction SilentlyContinue notification-config-filled.json, lambda_function.zip

Write-Host ""
Write-Host "=== Setup concluído! ==="
Write-Host "Bucket   : $BUCKET_NAME"
Write-Host "Lambda   : $FUNCTION_NAME"
Write-Host ""
Write-Host "Teste: aws s3 cp <arquivo> s3://$BUCKET_NAME/uploads/"
Write-Host "Logs : aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
