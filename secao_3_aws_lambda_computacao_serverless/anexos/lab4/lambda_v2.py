"""
lambda_v2.py – Código da Versão 2 da função Lambda (Lab 4)

Após publicar a Versão 1, substitua o código por este arquivo e publique a Versão 2.
Empacote como: zip lambda_versoes.zip lambda_v2.py
Handler: lambda_v2.lambda_handler
"""

import json
import os


def lambda_handler(event, context):
    versao = os.environ.get("APP_VERSAO", "2.0.0")
    feature = os.environ.get("NOVA_FEATURE", "false")

    print(f"Executando versao: {versao}")

    if feature == "true":
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "versao": versao,
                    "mensagem": "Nova feature ativa! Resultado aprimorado.",
                    "nova_feature": True,
                    "dados_extras": {
                        "algoritmo": "v2",
                        "performance": "otimizado",
                    },
                }
            ),
        }

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "versao": versao,
                "mensagem": "Versao 2 em execucao.",
                "nova_feature": False,
            }
        ),
    }
