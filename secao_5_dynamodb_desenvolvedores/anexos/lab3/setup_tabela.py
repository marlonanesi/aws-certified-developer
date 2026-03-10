"""
Setup: cria a tabela DVA-Lab-QueryScan e popula com ~200 itens
para os testes comparativos de Query vs Scan.
"""
import boto3
import random
from decimal import Decimal

client = boto3.client('dynamodb', region_name='sa-east-1')
dynamodb = boto3.resource('dynamodb', region_name='sa-east-1')

TABLE_NAME = 'DVA-Lab-QueryScan'

# Criar tabela
try:
    client.create_table(
        TableName=TABLE_NAME,
        KeySchema=[
            {'AttributeName': 'PK', 'KeyType': 'HASH'},
            {'AttributeName': 'SK', 'KeyType': 'RANGE'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'PK', 'AttributeType': 'S'},
            {'AttributeName': 'SK', 'AttributeType': 'S'}
        ],
        BillingMode='PROVISIONED',
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    print(f"Criando tabela {TABLE_NAME}...")
    waiter = client.get_waiter('table_exists')
    waiter.wait(TableName=TABLE_NAME)
    print("Tabela criada e ativa.")
except client.exceptions.ResourceInUseException:
    print(f"Tabela {TABLE_NAME} ja existe.")

# Popular com dados variados
table = dynamodb.Table(TABLE_NAME)

statuses = ['pending', 'approved', 'shipped', 'delivered', 'cancelled']
categories = ['electronics', 'books', 'clothing', 'home', 'sports']
cities = ['SP', 'RJ', 'BH', 'POA', 'CWB']

print("Inserindo itens (batch)...")

with table.batch_writer() as batch:
    for i in range(1, 51):  # 50 usuarios
        user_id = f"USER#{i:04d}"
        batch.put_item(Item={
            'PK': user_id,
            'SK': 'PROFILE',
            'name': f'Usuario {i}',
            'email': f'user{i}@email.com',
            'city': random.choice(cities)
        })
        num_orders = random.randint(1, 4)
        for j in range(1, num_orders + 1):
            batch.put_item(Item={
                'PK': user_id,
                'SK': f'ORDER#{j:03d}',
                'month': f'{random.randint(1, 12):02d}',
                'total': Decimal(str(round(random.uniform(10, 999), 2))),
                'status': random.choice(statuses),
                'category': random.choice(categories),
                'description': f'Pedido {j} do usuario {i} com descricao longa para simular payload real'
            })

count = table.scan(Select='COUNT')['Count']
print(f"\nTabela populada: {count} itens no total.")
print("Execute query_vs_scan.py para iniciar os testes.")
