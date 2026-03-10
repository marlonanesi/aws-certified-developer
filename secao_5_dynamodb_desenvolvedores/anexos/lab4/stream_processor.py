import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Processa eventos do DynamoDB Stream.
    View Type esperado: NEW_AND_OLD_IMAGES

    Tipos de evento: INSERT | MODIFY | REMOVE
    """
    logger.info(f"Recebidos {len(event['Records'])} registros do Stream.")

    for record in event['Records']:
        event_name = record['eventName']          # INSERT | MODIFY | REMOVE
        event_id   = record['eventID']
        dynamodb   = record.get('dynamodb', {})

        # Chaves do item
        keys = dynamodb.get('Keys', {})
        pk = keys.get('PK', {}).get('S', 'N/A')
        sk = keys.get('SK', {}).get('S', 'N/A')

        logger.info(f"{'=' * 50}")
        logger.info(f"Evento: {event_name} | PK={pk} | SK={sk} | ID={event_id}")

        if event_name == 'INSERT':
            new_image = dynamodb.get('NewImage', {})
            logger.info("  NOVO ITEM:")
            for attr, typed_val in new_image.items():
                val = list(typed_val.values())[0]
                logger.info(f"    {attr}: {val}")

            # Logica de negocio de exemplo
            if sk.startswith('ORDER#'):
                logger.info(f"  [ACAO] Novo pedido criado para {pk} — enviar confirmacao.")

        elif event_name == 'MODIFY':
            old_image = dynamodb.get('OldImage', {})
            new_image = dynamodb.get('NewImage', {})

            # Detectar atributos alterados
            all_keys = set(list(old_image) + list(new_image))
            changes = []
            for attr in all_keys:
                old_val = list(old_image[attr].values())[0] if attr in old_image else None
                new_val = list(new_image[attr].values())[0] if attr in new_image else None
                if old_val != new_val:
                    changes.append(f"{attr}: {old_val} -> {new_val}")

            logger.info(f"  MODIFICACOES ({len(changes)} campo(s)):")
            for change in changes:
                logger.info(f"    {change}")

            # Detectar mudanca de status
            old_status = old_image.get('status', {}).get('S', '')
            new_status = new_image.get('status', {}).get('S', '')
            if old_status != new_status and new_status == 'shipped':
                logger.info(f"  [ACAO] Pedido {sk} de {pk} enviado — notificar cliente.")

        elif event_name == 'REMOVE':
            old_image = dynamodb.get('OldImage', {})
            logger.info("  ITEM REMOVIDO:")
            for attr, typed_val in old_image.items():
                val = list(typed_val.values())[0]
                logger.info(f"    {attr}: {val}")

            # Distinguir TTL de deleção manual
            user_identity = record.get('userIdentity', {})
            if (user_identity.get('type') == 'Service' and
                    'dynamodb.amazonaws.com' in user_identity.get('principalId', '')):
                logger.info("  [ORIGEM] Deleção automatica por TTL.")
            else:
                logger.info("  [ORIGEM] Delecao manual pela aplicacao.")

    return {
        'statusCode': 200,
        'body': f"Processados {len(event['Records'])} registros."
    }
