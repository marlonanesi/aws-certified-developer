#!/bin/bash
# create_app_lambda.sh
# Cria IAM role, empacota e implanta a funcao lab5-app no Lambda (sa-east-1).
# Execute a partir da pasta: secao_11_seguranca_desenvolvedores/anexos/lab5/
#   bash create_app_lambda.sh

set -e

REGION="sa-east-1"
FUNCTION_NAME="lab5-app"
RUNTIME="python3.12"
HANDLER="app_lambda.lambda_handler"
ROLE_NAME="lab5-app-role"
SECRET_NAME="prod/lab5/database"

# --- 1. IAM Role ---
TRUST_POLICY='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

echo "Criando IAM role $ROLE_NAME..."
ROLE_ARN=$(aws iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document "$TRUST_POLICY" \
    --query 'Role.Arn' --output text)

echo "Role ARN: $ROLE_ARN"

aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

SM_POLICY='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"secretsmanager:GetSecretValue","Resource":"arn:aws:secretsmanager:*:*:secret:prod/lab5/*"}]}'
aws iam put-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-name SecretsManagerRead \
    --policy-document "$SM_POLICY"

echo "Aguardando propagacao do role IAM (15s)..."
sleep 15

# --- 2. Empacotar ---
echo "Empacotando app_lambda.py..."
zip -j app_lambda.zip app_lambda.py

# --- 3. Criar a funcao Lambda ---
echo "Criando funcao Lambda $FUNCTION_NAME..."
FUNCTION_ARN=$(aws lambda create-function \
    --function-name "$FUNCTION_NAME" \
    --runtime "$RUNTIME" \
    --handler "$HANDLER" \
    --role "$ROLE_ARN" \
    --zip-file fileb://app_lambda.zip \
    --region "$REGION" \
    --environment "Variables={SECRET_NAME=$SECRET_NAME}" \
    --query 'FunctionArn' --output text)

echo "Function ARN: $FUNCTION_ARN"

rm app_lambda.zip

echo ""
echo "Concluido. Funcao $FUNCTION_NAME criada com sucesso."
echo "Teste com: aws lambda invoke --function-name $FUNCTION_NAME --region $REGION response.json && cat response.json"
