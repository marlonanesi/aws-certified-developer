"""
Consultas via GSI na tabela DVA-Lab-Orders.

Requer:
  - Tabela DVA-Lab-Orders com dados do lab1 + setup_dados.py
  - GSI 'status-date-index'    (PK=status, SK=date)
  - GSI 'category-total-index' (PK=category, SK=total)
Ambos com ProjectionType=ALL e status Active.
"""
import boto3
import time
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource('dynamodb', region_name='sa-east-1')
table = dynamodb.Table('DVA-Lab-Orders')


def sep(titulo):
    print(f"\n{'=' * 55}")
    print(f"  {titulo}")
    print('=' * 55)


# ============================================================
# 1. Pedidos por status (Query no GSI status-date-index)
# ============================================================
def query_por_status(status_valor):
    sep(f"Query por status='{status_valor}'")

    response = table.query(
        IndexName='status-date-index',
        KeyConditionExpression=Key('status').eq(status_valor),
        ReturnConsumedCapacity='TOTAL'
    )

    rcu = response['ConsumedCapacity']['CapacityUnits']
    print(f"  Itens encontrados: {response['Count']} | RCUs: {rcu}")
    for item in response['Items']:
        print(f"  {item['PK']} | {item['SK']} | date={item.get('date', '-')} | total={item.get('total', '-')}")


# ============================================================
# 2. Pedidos pending em intervalo de datas
# ============================================================
def query_pending_por_data(inicio, fim):
    sep(f"Query pending entre {inicio} e {fim}")

    response = table.query(
        IndexName='status-date-index',
        KeyConditionExpression=(
            Key('status').eq('pending') &
            Key('date').between(inicio, fim)
        ),
        ReturnConsumedCapacity='TOTAL'
    )

    rcu = response['ConsumedCapacity']['CapacityUnits']
    print(f"  Itens encontrados: {response['Count']} | RCUs: {rcu}")
    for item in response['Items']:
        print(f"  {item['PK']} | {item['SK']} | date={item.get('date')} | total={item.get('total', '-')}")


# ============================================================
# 3. Pedidos por categoria, ordenados por total DESC
# ============================================================
def query_por_categoria(categoria):
    sep(f"Query categoria='{categoria}' (total DESC)")

    response = table.query(
        IndexName='category-total-index',
        KeyConditionExpression=Key('category').eq(categoria),
        ScanIndexForward=False,  # DESC — maior total primeiro
        ReturnConsumedCapacity='TOTAL'
    )

    rcu = response['ConsumedCapacity']['CapacityUnits']
    print(f"  Itens encontrados: {response['Count']} | RCUs: {rcu}")
    for item in response['Items']:
        print(f"  {item['PK']} | {item['SK']} | total={item['total']} | status={item.get('status', '-')}")


# ============================================================
# 4. Pedidos em categoria com total acima de minimo
# ============================================================
def query_caros_em_categoria(categoria, minimo):
    sep(f"Query categoria='{categoria}' com total >= {minimo}")

    response = table.query(
        IndexName='category-total-index',
        KeyConditionExpression=(
            Key('category').eq(categoria) &
            Key('total').gte(Decimal(str(minimo)))
        ),
        ReturnConsumedCapacity='TOTAL'
    )

    rcu = response['ConsumedCapacity']['CapacityUnits']
    print(f"  Itens encontrados: {response['Count']} | RCUs: {rcu}")
    for item in response['Items']:
        print(f"  {item['PK']} | {item['SK']} | total={item['total']}")


# ============================================================
# 5. Comparacao: Scan+Filter vs Query via GSI
# ============================================================
def comparar_scan_vs_gsi():
    sep("Comparacao: Scan+Filter vs Query via GSI")

    # Abordagem ruim — Scan com FilterExpression
    t0 = time.time()
    scan_resp = table.scan(
        FilterExpression=Attr('status').eq('pending'),
        ReturnConsumedCapacity='TOTAL'
    )
    t_scan = (time.time() - t0) * 1000

    print(f"\n  Scan + FilterExpression:")
    print(f"    Itens examinados: {scan_resp['ScannedCount']}")
    print(f"    Itens retornados: {scan_resp['Count']}")
    print(f"    RCUs consumidos:  {scan_resp['ConsumedCapacity']['CapacityUnits']}")
    print(f"    Tempo:            {t_scan:.1f}ms")

    # Abordagem correta — Query via GSI
    t0 = time.time()
    query_resp = table.query(
        IndexName='status-date-index',
        KeyConditionExpression=Key('status').eq('pending'),
        ReturnConsumedCapacity='TOTAL'
    )
    t_query = (time.time() - t0) * 1000

    print(f"\n  Query via GSI (status-date-index):")
    print(f"    Itens examinados: {query_resp['Count']}")
    print(f"    Itens retornados: {query_resp['Count']}")
    print(f"    RCUs consumidos:  {query_resp['ConsumedCapacity']['CapacityUnits']}")
    print(f"    Tempo:            {t_query:.1f}ms")

    economizados = scan_resp['ScannedCount'] - query_resp['Count']
    print(f"\n  GSI evitou ler {economizados} itens desnecessarios.")


# ============================================================
# EXECUTAR
# ============================================================
if __name__ == '__main__':
    print("=" * 55)
    print("DynamoDB — Consultas via GSI")
    print("=" * 55)

    query_por_status('pending')
    query_por_status('delivered')
    query_pending_por_data('2024-03-01', '2024-04-30')
    query_por_categoria('electronics')
    query_por_categoria('books')
    query_caros_em_categoria('electronics', 300)
    comparar_scan_vs_gsi()

    print("\n" + "=" * 55)
    print("Concluido.")
    print("=" * 55)
