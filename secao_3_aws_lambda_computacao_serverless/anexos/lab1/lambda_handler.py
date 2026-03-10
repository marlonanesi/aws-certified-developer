"""
lambda_handler.py – Código da função Lambda do Lab 1

Cole este código no editor do console AWS e clique em Deploy.
"""

import json
import os


def lambda_handler(event, context):
    # Lendo dados do evento
    name = event.get("name", "Mundo")
    action = event.get("action", "greet")

    # Lendo variável de ambiente configurada no console
    environment = os.environ.get("APP_ENV", "dev")

    # Informações do contexto (injetadas pelo runtime)
    remaining_time = context.get_remaining_time_in_millis()
    function_name = context.function_name
    request_id = context.aws_request_id

    print(f"[{environment}] Invocando função: {function_name}")
    print(f"Request ID: {request_id}")
    print(f"Tempo restante: {remaining_time}ms")
    print(f"Evento recebido: {json.dumps(event)}")

    if action == "greet":
        message = f"Olá, {name}! Ambiente: {environment}"
    elif action == "echo":
        message = f"Echo: {json.dumps(event)}"
    else:
        message = f"Ação desconhecida: {action}"

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "message": message,
                "requestId": request_id,
                "remainingTime": remaining_time,
            }
        ),
    }
