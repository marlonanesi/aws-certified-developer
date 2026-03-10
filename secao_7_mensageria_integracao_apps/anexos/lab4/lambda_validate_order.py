import json
import random


def lambda_handler(event, context):
    """
    Valida os dados de entrada de um pedido.

    Simula 10% de chance de falha para demonstrar o mecanismo de Retry
    configurado na state machine com IntervalSeconds=2, MaxAttempts=3, BackoffRate=2.

    Retorna o evento enriquecido com o campo 'validated'.
    """
    order_id = event.get("order_id", "UNKNOWN")
    amount = event.get("amount", 0)

    # Simula falha transitória (10% de probabilidade) para testar o Retry declarativo
    if random.random() < 0.1:
        raise Exception("Validation service temporarily unavailable")

    return {
        "order_id": order_id,
        "amount": amount,
        "order_type": event.get("order_type", "standard"),
        "validated": True,
    }
