import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Processa mensagens recebidas de uma fila SQS via Event Source Mapping.

    O SQS envia um lote de mensagens (batch) em `event['Records']`.
    Cada registro contém o corpo da mensagem em `record['body']`.

    Se a função lançar uma exceção, o SQS considera o batch como falha
    e incrementa o ReceiveCount. Após atingir o maxReceiveCount, a
    mensagem é movida para a DLQ (Dead Letter Queue).
    """
    records = event.get("Records", [])

    if not records:
        logger.warning("Event does not contain 'Records'. Possibly a direct/test invocation. Event: %s", json.dumps(event))
        return {"statusCode": 200, "body": "No records to process"}

    logger.info(f"Received {len(records)} message(s)")

    for record in records:
        body = record["body"]
        message_id = record["messageId"]

        logger.info(f"Processing message {message_id}: {body}")

        try:
            data = json.loads(body)
            logger.info(f"Processed order: {data}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in message {message_id}: {body}")
            # Re-lançar a exceção faz o SQS considerar esta mensagem como falha.
            # Após maxReceiveCount tentativas, ela vai para a DLQ.
            raise

    return {"statusCode": 200, "body": "Messages processed"}
