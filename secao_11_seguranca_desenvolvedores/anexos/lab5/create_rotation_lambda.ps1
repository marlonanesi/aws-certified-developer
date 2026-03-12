# create_rotation_lambda.ps1
# Cria IAM role, empacota e implanta a funcao lab5-rotation no Lambda (sa-east-1).
# Execute a partir da pasta: secao_11_seguranca_desenvolvedores/anexos/lab5/
#   .\create_rotation_lambda.ps1

$ErrorActionPreference = "Stop"

$REGION        = "sa-east-1"
$FUNCTION_NAME = "lab5-rotation"
$RUNTIME       = "python3.12"
$HANDLER       = "rotation_lambda.lambda_handler"
$ROLE_NAME     = "lab5-rotation-role"

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

$smPolicy = '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["secretsmanager:GetSecretValue","secretsmanager:PutSecretValue","secretsmanager:UpdateSecretVersionStage","secretsmanager:DescribeSecret"],"Resource":"*"}]}'
aws iam put-role-policy `
    --role-name $ROLE_NAME `
    --policy-name SecretsManagerRotation `
    --policy-document $smPolicy

Write-Host "Aguardando propagacao do role IAM (15s)..."
Start-Sleep -Seconds 15

# --- 2. Empacotar ---
Write-Host "Empacotando rotation_lambda.py..."
Compress-Archive -Path rotation_lambda.py -DestinationPath rotation_lambda.zip -Force

# --- 3. Criar a funcao Lambda ---
Write-Host "Criando funcao Lambda $FUNCTION_NAME..."
$FUNCTION_ARN = aws lambda create-function `
    --function-name $FUNCTION_NAME `
    --runtime $RUNTIME `
    --handler $HANDLER `
    --role $ROLE_ARN `
    --zip-file fileb://rotation_lambda.zip `
    --region $REGION `
    --query 'FunctionArn' --output text

Write-Host "Function ARN: $FUNCTION_ARN"

# --- 4. Permissao para o Secrets Manager invocar a Lambda ---
aws lambda add-permission `
    --function-name $FUNCTION_NAME `
    --statement-id allow-secrets-manager `
    --action lambda:InvokeFunction `
    --principal secretsmanager.amazonaws.com `
    --region $REGION | Out-Null

Remove-Item rotation_lambda.zip

Write-Host ""
Write-Host "Concluido. Use o ARN abaixo na etapa de configuracao de rotacao:"
Write-Host $FUNCTION_ARN
