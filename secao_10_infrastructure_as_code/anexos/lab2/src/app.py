import json
import os
import uuid
from datetime import datetime, timezone

import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


def list_todos(event, context):
    """Retorna todos os itens da tabela DynamoDB."""
    response = table.scan()
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(response["Items"]),
    }


def create_todo(event, context):
    """Cria um novo item na tabela DynamoDB."""
    body = json.loads(event.get("body") or "{}")

    item = {
        "id": str(uuid.uuid4()),
        "title": body.get("title", "Sem título"),
        "done": False,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }

    table.put_item(Item=item)

    return {
        "statusCode": 201,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(item),
    }
