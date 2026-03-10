def lambda_handler(event, context):
    """
    Processa um pedido do tipo 'premium'.
    Aplica desconto de 10% e marca o status como 'processed'.

    O Step Functions passa o output deste estado como input do próximo.
    """
    return {
        **event,
        "processing": "premium",
        "discount": 0.10,
        "status": "processed",
    }
