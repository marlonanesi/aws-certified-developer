import boto3
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='sa-east-1')
table = dynamodb.Table('DVA-Lab-Orders')

# ============================================================
# CREATE — PutItem
# ============================================================
def create_items():
    items = [
        {
            'PK': 'USER#001',
            'SK': 'PROFILE',
            'name': 'Maria Silva',
            'email': 'maria@email.com',
            'city': 'Sao Paulo'
        },
        {
            'PK': 'USER#001',
            'SK': 'ORDER#A001',
            'total': Decimal('199.90'),
            'status': 'delivered',
            'category': 'electronics'
        },
        {
            'PK': 'USER#001',
            'SK': 'ORDER#A002',
            'total': Decimal('349.50'),
            'status': 'pending',
            'category': 'books'
        },
        {
            'PK': 'USER#001',
            'SK': 'ORDER#A003',
            'total': Decimal('89.00'),
            'status': 'shipped',
            'category': 'clothing'
        },
        {
            'PK': 'USER#002',
            'SK': 'PROFILE',
            'name': 'Joao Santos',
            'email': 'joao@email.com',
            'city': 'Rio de Janeiro'
        },
        {
            'PK': 'USER#002',
            'SK': 'ORDER#A001',
            'total': Decimal('550.00'),
            'status': 'delivered',
            'category': 'electronics'
        },
    ]

    for item in items:
        table.put_item(Item=item)
        print(f"  Inserido: PK={item['PK']}, SK={item['SK']}")

    print(f"\n{len(items)} itens inseridos.\n")


# ============================================================
# READ — GetItem (item unico)
# ============================================================
def read_single_item():
    response = table.get_item(Key={'PK': 'USER#001', 'SK': 'PROFILE'})
    item = response.get('Item', {})
    print("GetItem — Perfil do USER#001:")
    print(f"  Nome:   {item.get('name')}")
    print(f"  Email:  {item.get('email')}")
    print(f"  Cidade: {item.get('city')}\n")


# ============================================================
# READ — Query (multiplos itens com begins_with)
# ============================================================
def read_user_orders():
    from boto3.dynamodb.conditions import Key

    response = table.query(
        KeyConditionExpression=Key('PK').eq('USER#001') & Key('SK').begins_with('ORDER#'),
        ReturnConsumedCapacity='TOTAL'
    )
    rcu = response['ConsumedCapacity']['CapacityUnits']
    print(f"Query — Pedidos do USER#001 ({response['Count']} encontrados | RCUs: {rcu}):")
    for item in response['Items']:
        print(f"  {item['SK']} | Total: R${item['total']} | Status: {item['status']}")
    print()


# ============================================================
# UPDATE — UpdateItem (atualiza apenas campos especificados)
# ============================================================
def update_item():
    response = table.update_item(
        Key={'PK': 'USER#001', 'SK': 'ORDER#A002'},
        UpdateExpression='SET #s = :new_status, updated_at = :now',
        ExpressionAttributeNames={'#s': 'status'},  # 'status' e palavra reservada
        ExpressionAttributeValues={
            ':new_status': 'shipped',
            ':now': datetime.utcnow().isoformat()
        },
        ReturnValues='ALL_NEW'
    )
    updated = response['Attributes']
    print("UpdateItem — Pedido ORDER#A002:")
    print(f"  Novo status:  {updated['status']}")
    print(f"  Atualizado em: {updated.get('updated_at')}\n")


# ============================================================
# DELETE — DeleteItem
# ============================================================
def delete_item():
    response = table.delete_item(
        Key={'PK': 'USER#001', 'SK': 'ORDER#A003'},
        ReturnValues='ALL_OLD'
    )
    deleted = response.get('Attributes', {})
    print(f"DeleteItem — Removido: {deleted.get('SK', 'N/A')} | Total: R${deleted.get('total', 'N/A')}\n")


# ============================================================
# EXECUTAR
# ============================================================
if __name__ == '__main__':
    print("=" * 55)
    print("DynamoDB — Operacoes CRUD")
    print("=" * 55)

    print("\n[1] CREATE — Inserindo itens...")
    create_items()

    print("[2] READ — GetItem (item unico)...")
    read_single_item()

    print("[3] READ — Query (pedidos do usuario)...")
    read_user_orders()

    print("[4] UPDATE — Atualizando status do pedido...")
    update_item()

    print("[5] DELETE — Removendo pedido...")
    delete_item()

    print("[3] READ — Query apos update e delete...")
    read_user_orders()

    print("=" * 55)
    print("Concluido.")
    print("=" * 55)
