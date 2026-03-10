"""
Setup: insere dados adicionais na tabela DVA-Lab-Orders
para suportar as queries via GSI do lab2.

Execute ANTES de criar os GSIs — os dados ja precisam estar presentes
quando os indices forem construidos (DynamoDB indexa itens existentes
automaticamente ao criar um GSI).
"""
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='sa-east-1')
table = dynamodb.Table('DVA-Lab-Orders')

orders = [
    {
        'PK': 'USER#001', 'SK': 'ORDER#B001',
        'date': '2024-04-01', 'total': Decimal('750.00'),
        'status': 'pending', 'category': 'electronics'
    },
    {
        'PK': 'USER#002', 'SK': 'ORDER#B001',
        'date': '2024-03-15', 'total': Decimal('120.00'),
        'status': 'pending', 'category': 'books'
    },
    {
        'PK': 'USER#002', 'SK': 'ORDER#B002',
        'date': '2024-04-10', 'total': Decimal('89.90'),
        'status': 'shipped', 'category': 'clothing'
    },
    {
        'PK': 'USER#003', 'SK': 'PROFILE',
        'name': 'Ana Costa', 'email': 'ana@email.com',
        'city': 'Curitiba'
    },
    {
        'PK': 'USER#003', 'SK': 'ORDER#B001',
        'date': '2024-02-28', 'total': Decimal('299.00'),
        'status': 'delivered', 'category': 'electronics'
    },
    {
        'PK': 'USER#003', 'SK': 'ORDER#B002',
        'date': '2024-04-05', 'total': Decimal('45.00'),
        'status': 'pending', 'category': 'books'
    },
]

print(f"Inserindo {len(orders)} itens adicionais...")
for item in orders:
    table.put_item(Item=item)
    print(f"  OK: {item['PK']} | {item['SK']}")

print(f"\n{len(orders)} itens inseridos. Pode criar os GSIs agora.")
