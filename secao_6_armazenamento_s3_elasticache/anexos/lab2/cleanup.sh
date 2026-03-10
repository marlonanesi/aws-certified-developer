#!/bin/bash
# cleanup.sh — Remove todos os recursos criados pelo Lab 2

set -e

BUCKET_NAME="dva-lab2-eventos-$(aws sts get-caller-identity --query Account --output text)"
FUNCTION_NAME="dva-lab2-s3-processor"
ROLE_NAME="dva-lab2-lambda-s3-role"

echo "=== Iniciando limpeza ==="
echo "Bucket: $BUCKET_NAME"
echo ""

# 1. Remover notificação do bucket (config vazia)
echo "[1/5] Removendo configuração de notificação..."
aws s3api put-bucket-notification-configuration \
  --bucket "$BUCKET_NAME" \
  --notification-configuration '{}' 2>/dev/null || echo "  (ignorado — bucket pode não existir)"

# 2. Esvaziar e remover bucket
echo "[2/5] Esvaziando e removendo bucket..."
aws s3 rm "s3://$BUCKET_NAME" --recursive 2>/dev/null || true
aws s3 rb "s3://$BUCKET_NAME" 2>/dev/null || echo "  (ignorado — bucket pode não existir)"

# 3. Remover função Lambda
echo "[3/5] Removendo função Lambda..."
aws lambda delete-function --function-name "$FUNCTION_NAME" 2>/dev/null || echo "  (ignorado — função pode não existir)"

# 4. Remover log group do CloudWatch
echo "[4/5] Removendo log group..."
aws logs delete-log-group \
  --log-group-name "/aws/lambda/$FUNCTION_NAME" 2>/dev/null || echo "  (ignorado — log group pode não existir)"

# 5. Remover IAM Role e políticas
echo "[5/5] Removendo IAM Role..."
aws iam detach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole 2>/dev/null || true

aws iam detach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess 2>/dev/null || true

aws iam delete-role --role-name "$ROLE_NAME" 2>/dev/null || echo "  (ignorado — role pode não existir)"

# Arquivos temporários locais
rm -f notification-config-filled.json lambda_function.zip teste-evento.txt foto.jpg dados.csv relatorio.pdf

echo ""
echo "=== Limpeza concluída ==="
