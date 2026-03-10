import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    # Parallel retorna lista — normaliza para dict
    if isinstance(event, list):
        merged = {}
        for item in event:
            if isinstance(item, dict):
                merged.update(item)
        event = merged

    return {"final_status": "COMPLETED", **event}