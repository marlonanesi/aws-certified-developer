"""
Gera eventos INSERT, MODIFY e REMOVE na tabela DVA-Lab-StreamsDemo
para testar o processamento via DynamoDB Streams + Lambda.

Execute apos o Event Source Mapping estar em estado Enabled.
"""
import boto3
import time
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='sa-east-1')
table = dynamodb.Table('DVA-Lab-StreamsDemo')

print("=" * 55)
print("  Gerando eventos no DynamoDB Stream")
print("=" * 55)

# INSERT — perfil do usuario
print("\n[1] INSERT — criando perfil do usuario...")
table.put_item(Item={
    'PK': 'USER#100',
    'SK': 'PROFILE',
    'name': 'Carlos Mendes',
    'email': 'carlos@email.com',
    'city': 'Florianopolis'
})
time.sleep(2)

# INSERT — pedido
print("[2] INSERT — criando pedido...")
table.put_item(Item={
    'PK': 'USER#100',
    'SK': 'ORDER#001',
    'total': Decimal('299.90'),
    'status': 'pending',
    'category': 'electronics'
})
time.sleep(2)

# MODIFY — status: pending → shipped
print("[3] MODIFY — atualizando status para 'shipped'...")
table.update_item(
    Key={'PK': 'USER#100', 'SK': 'ORDER#001'},
    UpdateExpression='SET #s = :val',
    ExpressionAttributeNames={'#s': 'status'},
    ExpressionAttributeValues={':val': 'shipped'}
)
time.sleep(2)

# MODIFY — status: shipped → delivered
print("[4] MODIFY — atualizando status para 'delivered'...")
table.update_item(
    Key={'PK': 'USER#100', 'SK': 'ORDER#001'},
    UpdateExpression='SET #s = :val',
    ExpressionAttributeNames={'#s': 'status'},
    ExpressionAttributeValues={':val': 'delivered'}
)
time.sleep(2)

# REMOVE — delecao manual do perfil
print("[5] REMOVE — deletando perfil do usuario...")
table.delete_item(Key={'PK': 'USER#100', 'SK': 'PROFILE'})

print("\nEventos gerados.")
print("Aguarde cerca de 30 segundos e verifique os logs do Lambda no CloudWatch.")
