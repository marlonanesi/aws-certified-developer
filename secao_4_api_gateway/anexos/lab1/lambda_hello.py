"""
lambda_hello.py – Código da função Lambda do Lab 1

Cole este código no editor do console AWS (função api-lab1-hello) e clique em Deploy.
Requer Lambda Proxy Integration habilitada no API Gateway.
"""

import json


def lambda_handler(event, context):
    # Log do evento completo para debug — visível no CloudWatch
    print("Event:", json.dumps(event))

    http_method = event.get("httpMethod", "UNKNOWN")
    path = event.get("path", "/")
    query_params = event.get("queryStringParameters") or {}

    # Nome opcional via query string: GET /hello?name=Estudante
    name = query_params.get("name", "Mundo")

    # Validação simples — exercita resposta 400
    if name and len(name) < 2:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "name deve ter ao menos 2 caracteres"}),
        }

    # Processar body para requisições POST
    body_data = {}
    if http_method == "POST":
        raw_body = event.get("body") or "{}"
        body_data = json.loads(raw_body)
        name = body_data.get("name", name)

    # Resposta no formato obrigatório da Lambda Proxy Integration
    # statusCode, headers e body são OBRIGATÓRIOS
    # body DEVE ser string (json.dumps), não dict
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "X-Custom-Header": "lab1-demo",
        },
        "body": json.dumps(
            {
                "message": f"Olá, {name}! Bem-vindo ao API Gateway.",
                "method": http_method,
                "path": path,
            }
        ),
    }
