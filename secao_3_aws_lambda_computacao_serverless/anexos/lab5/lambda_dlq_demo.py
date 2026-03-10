"""
lambda_dlq_demo.py – Código da função Lambda do Lab 5 (DLQ e Destinations)

Empacote como: zip lambda_dlq_demo.zip lambda_dlq_demo.py
Handler: lambda_dlq_demo.lambda_handler
"""

import json
import random
import time


def lambda_handler(event, context):
    print(f"Evento recebido: {json.dumps(event)}")

    acao = event.get("acao", "sucesso")

    if acao == "falhar":
        # Simula uma falha de negócio — o Lambda encaminhará para OnFailure após os retries
        raise ValueError(f"Erro simulado: operacao '{acao}' falhou intencionalmente!")

    elif acao == "timeout":
        # Simula processamento demorado — ultrapassa o timeout configurado (30 s)
        time.sleep(35)

    elif acao == "exception_aleatoria":
        # 50% de chance de falhar — útil para demonstrar distribuição nas filas
        if random.random() < 0.5:
            raise RuntimeError("Erro aleatorio de sistema!")

    # Caso de sucesso
    resultado = {
        "processado": True,
        "acao": acao,
        "dados_originais": event,
        "mensagem": f"Operacao '{acao}' concluida com sucesso!",
    }

    print(f"Sucesso: {json.dumps(resultado)}")
    return resultado
