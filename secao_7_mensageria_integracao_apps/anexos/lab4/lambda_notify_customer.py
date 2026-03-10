import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Notifica o cliente sobre o pedido premium.
    Executada em paralelo com lambda_process_premium dentro do estado Parallel.

    Em produção, esta função enviaria um e-mail via SES ou uma notificação via SNS.
    """
    logger.info(f"Notifying customer for order: {event.get('order_id')}")
    return {"notification_sent": True, **event}
