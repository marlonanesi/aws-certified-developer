"""
lambda_stages.py – Código da função Lambda do Lab 2

Atualiza a função api-lab1-hello para exibir informações de stage e alias.
Cole este código no editor do console, clique em Deploy, depois publique versão 1
e crie os aliases dev e prod conforme o roteiro.
"""

import json
import os


def lambda_handler(event, context):
    print("Event:", json.dumps(event))

    query_params = event.get("queryStringParameters") or {}
    name = query_params.get("name", "Mundo")

    # Stage Variables são enviadas pelo API Gateway no evento (Proxy Integration)
    stage_variables = event.get("stageVariables") or {}
    stage_alias = stage_variables.get("lambdaAlias", "nao-definido")

    # Variável de ambiente da própria função (opcional — para comparação)
    env_var = os.environ.get("ENVIRONMENT", "nao-configurado")

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "message": f"Olá, {name}!",
                "stageAlias": stage_alias,
                "functionVersion": context.function_version,
                "envVar": env_var,
            }
        ),
    }
