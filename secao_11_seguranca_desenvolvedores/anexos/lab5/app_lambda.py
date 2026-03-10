"""
app_lambda.py – Lambda de aplicação que consome segredos do Secrets Manager

Copie para o editor da função Lambda no console AWS.
Variável de ambiente necessária: SECRET_NAME = prod/lab5/database

IAM Policy necessária no execution role:
{
  "Effect": "Allow",
  "Action": "secretsmanager:GetSecretValue",
  "Resource": "arn:aws:secretsmanager:*:*:secret:prod/lab5/*"
}
"""

import boto3
import json
import os

# Cache em memória — persiste entre invocações enquanto o container Lambda estiver ativo
_secret_cache: dict = {}


def get_secret(secret_name: str) -> dict:
    if secret_name in _secret_cache:
        return _secret_cache[secret_name]

    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_name)
    secret = json.loads(response["SecretString"])
    _secret_cache[secret_name] = secret
    return secret


def lambda_handler(event, context):
    secret_name = os.environ.get("SECRET_NAME", "prod/lab5/database")

    try:
        credentials = get_secret(secret_name)
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Conexão simulada com sucesso",
            "host": credentials.get("host"),
            "port": credentials.get("port"),
            "username": credentials.get("username"),
            # Nunca retorne senhas em produção
        }),
    }
