"""
lambda_v1.py – Código da Versão 1 da função Lambda (Lab 4)

Empacote como: zip lambda_versoes.zip lambda_v1.py
Handler: lambda_v1.lambda_handler
"""

import json
import os


def lambda_handler(event, context):
    versao = os.environ.get("APP_VERSAO", "1.0.0")
    feature = os.environ.get("NOVA_FEATURE", "false")

    print(f"Executando versao: {versao}")
    print(f"Nova feature ativa: {feature}")

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "versao": versao,
                "mensagem": "Versao 1 em execucao. Comportamento estavel.",
                "nova_feature": feature == "true",
            }
        ),
    }
