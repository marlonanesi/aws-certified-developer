#!/bin/bash
# setup.sh — Infraestrutura completa do Lab 2: S3 Events + Lambda
# Pré-requisito: AWS CLI configurado, lambda_function.py no diretório atual

set -e

BUCKET_NAME="dva-lab2-eventos-$(aws sts get-caller-identity --query Account --output text)"
FUNCTION_NAME="dva-lab2-s3-processor"
ROLE_NAME="dva-lab2-lambda-s3-role"

echo "=== Bucket: $BUCKET_NAME ==="
echo "=== Função: $FUNCTION_NAME ==="
echo ""

# 1. Criar IAM Role para a Lambda
echo "[1/6] Criando IAM Role..."
aws iam create-role \
  --role-name "$ROLE_NAME" \
  --assume-role-policy-document file://lambda-trust-policy.json

ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query Role.Arn --output text)
echo "Role ARN: $ROLE_ARN"

# 2. Anexar políticas à Role
echo "[2/6] Anexando políticas..."
aws iam attach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

echo "Aguardando propagação da Role (10s)..."
sleep 10

# 3. Empacotar e criar a função Lambda
echo "[3/6] Criando função Lambda..."
zip lambda_function.zip lambda_function.py

aws lambda create-function \
  --function-name "$FUNCTION_NAME" \
  --runtime python3.12 \
  --role "$ROLE_ARN" \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda_function.zip \
  --timeout 30

LAMBDA_ARN=$(aws lambda get-function --function-name "$FUNCTION_NAME" --query Configuration.FunctionArn --output text)
echo "Lambda ARN: $LAMBDA_ARN"

# 4. Criar bucket S3
echo "[4/6] Criando bucket S3..."
REGION=$(aws configure get region)
if [ "$REGION" = "us-east-1" ]; then
  aws s3api create-bucket --bucket "$BUCKET_NAME"
else
  aws s3api create-bucket \
    --bucket "$BUCKET_NAME" \
    --create-bucket-configuration LocationConstraint="$REGION"
fi

# 5. Adicionar resource-based policy na Lambda (S3 precisa de permissão para invocá-la)
echo "[5/6] Adicionando resource-based policy na Lambda..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws lambda add-permission \
  --function-name "$FUNCTION_NAME" \
  --statement-id "S3InvokePermission" \
  --action "lambda:InvokeFunction" \
  --principal s3.amazonaws.com \
  --source-arn "arn:aws:s3:::$BUCKET_NAME" \
  --source-account "$ACCOUNT_ID"

# 6. Configurar notificação de eventos no bucket
echo "[6/6] Configurando notificação de eventos no bucket..."
sed "s|LAMBDA_ARN_PLACEHOLDER|$LAMBDA_ARN|g" notification-config.json > notification-config-filled.json

aws s3api put-bucket-notification-configuration \
  --bucket "$BUCKET_NAME" \
  --notification-configuration file://notification-config-filled.json

rm -f notification-config-filled.json lambda_function.zip

echo ""
echo "=== Setup concluído! ==="
echo "Bucket   : $BUCKET_NAME"
echo "Lambda   : $FUNCTION_NAME"
echo ""
echo "Teste: aws s3 cp <arquivo> s3://$BUCKET_NAME/uploads/"
echo "Logs : aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
