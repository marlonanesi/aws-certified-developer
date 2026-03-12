# create_app_lambda.ps1
# Cria IAM role, empacota e implanta a funcao lab5-app no Lambda (sa-east-1).
# Execute a partir da pasta: secao_11_seguranca_desenvolvedores/anexos/lab5/
#   .\create_app_lambda.ps1

$ErrorActionPreference = "Stop"

$REGION        = "sa-east-1"
$FUNCTION_NAME = "lab5-app"
$RUNTIME       = "python3.12"
$HANDLER       = "app_lambda.lambda_handler"
$ROLE_NAME     = "lab5-app-role"
$SECRET_NAME   = "prod/lab5/database"

# --- 1. IAM Role ---
$trustPolicy = '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

Write-Host "Criando IAM role $ROLE_NAME..."
$ROLE_ARN = aws iam create-role `
    --role-name $ROLE_NAME `
    --assume-role-policy-document $trustPolicy `
    --query 'Role.Arn' --output text

Write-Host "Role ARN: $ROLE_ARN"

aws iam attach-role-policy `
    --role-name $ROLE_NAME `
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

$smPolicy = '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"secretsmanager:GetSecretValue","Resource":"arn:aws:secretsmanager:*:*:secret:prod/lab5/*"}]}'
aws iam put-role-policy `
    --role-name $ROLE_NAME `
    --policy-name SecretsManagerRead `
    --policy-document $smPolicy

Write-Host "Aguardando propagacao do role IAM (15s)..."
Start-Sleep -Seconds 15

# --- 2. Empacotar ---
Write-Host "Empacotando app_lambda.py..."
Compress-Archive -Path app_lambda.py -DestinationPath app_lambda.zip -Force

# --- 3. Criar a funcao Lambda ---
Write-Host "Criando funcao Lambda $FUNCTION_NAME..."
$FUNCTION_ARN = aws lambda create-function `
    --function-name $FUNCTION_NAME `
    --runtime $RUNTIME `
    --handler $HANDLER `
    --role $ROLE_ARN `
    --zip-file fileb://app_lambda.zip `
    --region $REGION `
    --environment "Variables={SECRET_NAME=$SECRET_NAME}" `
    --query 'FunctionArn' --output text

Write-Host "Function ARN: $FUNCTION_ARN"

Remove-Item app_lambda.zip

Write-Host ""
Write-Host "Concluido. Funcao $FUNCTION_NAME criada com sucesso."
Write-Host "Teste com: aws lambda invoke --function-name $FUNCTION_NAME --region $REGION response.json; Get-Content response.json"
