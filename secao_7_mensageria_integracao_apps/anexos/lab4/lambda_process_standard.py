def lambda_handler(event, context):
    """
    Processa um pedido do tipo 'standard'.
    Marca o status como 'processed' sem aplicar desconto.
    """
    return {
        **event,
        "processing": "standard",
        "status": "processed",
    }
