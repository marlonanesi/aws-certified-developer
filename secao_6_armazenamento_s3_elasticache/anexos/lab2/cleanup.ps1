# cleanup.ps1 — Remove todos os recursos criados pelo Lab 2
#
# Como executar:
#   cd path\to\lab2
#   .\cleanup.ps1
#
# Caso PowerShell bloqueie a execução, rode antes:
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

$ErrorActionPreference = "Stop"

$ACCOUNT_ID    = aws sts get-caller-identity --query Account --output text
$BUCKET_NAME   = "dva-lab2-eventos-$ACCOUNT_ID"
$FUNCTION_NAME = "dva-lab2-s3-processor"
$ROLE_NAME     = "dva-lab2-lambda-s3-role"

Write-Host "=== Iniciando limpeza ==="
Write-Host "Bucket: $BUCKET_NAME"
Write-Host ""

# 1. Remover notificação do bucket (config vazia)
Write-Host "[1/5] Removendo configuração de notificação..."
try {
    aws s3api put-bucket-notification-configuration `
        --bucket $BUCKET_NAME `
        --notification-configuration '{}'
} catch {
    Write-Host "  (ignorado — bucket pode não existir)"
}

# 2. Esvaziar e remover bucket
Write-Host "[2/5] Esvaziando e removendo bucket..."
try { aws s3 rm "s3://$BUCKET_NAME" --recursive } catch {}
try {
    aws s3 rb "s3://$BUCKET_NAME"
} catch {
    Write-Host "  (ignorado — bucket pode não existir)"
}

# 3. Remover função Lambda
Write-Host "[3/5] Removendo função Lambda..."
try {
    aws lambda delete-function --function-name $FUNCTION_NAME
} catch {
    Write-Host "  (ignorado — função pode não existir)"
}

# 4. Remover log group do CloudWatch
Write-Host "[4/5] Removendo log group..."
try {
    aws logs delete-log-group --log-group-name "/aws/lambda/$FUNCTION_NAME"
} catch {
    Write-Host "  (ignorado — log group pode não existir)"
}

# 5. Remover IAM Role e políticas
Write-Host "[5/5] Removendo IAM Role..."
try { aws iam detach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole } catch {}
try { aws iam detach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess } catch {}
try {
    aws iam delete-role --role-name $ROLE_NAME
} catch {
    Write-Host "  (ignorado — role pode não existir)"
}

# Arquivos temporários locais
Remove-Item -Force -ErrorAction SilentlyContinue `
    notification-config-filled.json, lambda_function.zip, `
    teste-evento.txt, foto.jpg, dados.csv, relatorio.pdf

Write-Host ""
Write-Host "=== Limpeza concluída ==="
