"""
Comparacao pratica entre Query e Scan no DynamoDB.

Requer a tabela DVA-Lab-QueryScan criada e populada por setup_tabela.py.
"""
import boto3
import time
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource('dynamodb', region_name='sa-east-1')
table = dynamodb.Table('DVA-Lab-QueryScan')


def sep(titulo):
    print(f"\n{'=' * 60}")
    print(f"  {titulo}")
    print('=' * 60)


# ============================================================
# TESTE 1: Query vs Scan para buscar pedidos de um usuario
# ============================================================
def teste1_query_vs_scan_por_usuario():
    sep("TESTE 1: Pedidos do USER#0001 — Query vs Scan")

    # Query — usa o indice da PK diretamente
    t0 = time.time()
    q = table.query(
        KeyConditionExpression=Key('PK').eq('USER#0001') & Key('SK').begins_with('ORDER#'),
        ReturnConsumedCapacity='TOTAL'
    )
    t_query = (time.time() - t0) * 1000

    print(f"\n  Query:")
    print(f"    Itens retornados: {q['Count']}")
    print(f"    RCUs consumidos:  {q['ConsumedCapacity']['CapacityUnits']}")
    print(f"    Tempo:            {t_query:.1f}ms")

    # Scan — le a tabela inteira e filtra depois
    t0 = time.time()
    s = table.scan(
        FilterExpression=Attr('PK').eq('USER#0001') & Attr('SK').begins_with('ORDER#'),
        ReturnConsumedCapacity='TOTAL'
    )
    t_scan = (time.time() - t0) * 1000

    print(f"\n  Scan + FilterExpression:")
    print(f"    Itens examinados: {s['ScannedCount']}")
    print(f"    Itens retornados: {s['Count']}")
    print(f"    RCUs consumidos:  {s['ConsumedCapacity']['CapacityUnits']}")
    print(f"    Tempo:            {t_scan:.1f}ms")

    if q['ConsumedCapacity']['CapacityUnits'] > 0:
        ratio = s['ConsumedCapacity']['CapacityUnits'] / q['ConsumedCapacity']['CapacityUnits']
        print(f"\n  Scan usou {ratio:.0f}x mais RCUs que Query para o mesmo resultado.")


# ============================================================
# TESTE 2: FilterExpression nao reduz RCUs (pegadinha de prova)
# ============================================================
def teste2_filter_nao_reduz_rcu():
    sep("TESTE 2: FilterExpression NAO reduz RCUs")

    # Scan sem filtro
    s_sem = table.scan(ReturnConsumedCapacity='TOTAL')

    # Scan com filtro restritivo
    s_com = table.scan(
        FilterExpression=Attr('status').eq('cancelled'),
        ReturnConsumedCapacity='TOTAL'
    )

    print(f"\n  Scan SEM FilterExpression:")
    print(f"    Itens examinados: {s_sem['ScannedCount']}")
    print(f"    Itens retornados: {s_sem['Count']}")
    print(f"    RCUs consumidos:  {s_sem['ConsumedCapacity']['CapacityUnits']}")

    print(f"\n  Scan COM FilterExpression (status=cancelled):")
    print(f"    Itens examinados: {s_com['ScannedCount']}")
    print(f"    Itens retornados: {s_com['Count']}")
    print(f"    RCUs consumidos:  {s_com['ConsumedCapacity']['CapacityUnits']}")

    print(f"\n  Conclusao: RCUs sao identicos. Filter ocorre APOS a leitura.")


# ============================================================
# TESTE 3: ProjectionExpression
# ============================================================
def teste3_projection_expression():
    sep("TESTE 3: ProjectionExpression — payload vs RCUs")

    # Sem projection — todos os atributos
    q_todos = table.query(
        KeyConditionExpression=Key('PK').eq('USER#0010') & Key('SK').begins_with('ORDER#'),
        ReturnConsumedCapacity='TOTAL'
    )

    # Com projection — apenas 3 atributos
    q_proj = table.query(
        KeyConditionExpression=Key('PK').eq('USER#0010') & Key('SK').begins_with('ORDER#'),
        ProjectionExpression='PK, SK, #t',
        ExpressionAttributeNames={'#t': 'total'},
        ReturnConsumedCapacity='TOTAL'
    )

    attrs_todos = len(q_todos['Items'][0]) if q_todos['Items'] else 0
    attrs_proj = len(q_proj['Items'][0]) if q_proj['Items'] else 0

    print(f"\n  Query SEM Projection:")
    print(f"    Atributos por item: {attrs_todos}")
    print(f"    RCUs consumidos:    {q_todos['ConsumedCapacity']['CapacityUnits']}")

    print(f"\n  Query COM Projection (PK, SK, total):")
    print(f"    Atributos por item: {attrs_proj}")
    print(f"    RCUs consumidos:    {q_proj['ConsumedCapacity']['CapacityUnits']}")

    print(f"\n  Conclusao: Projection reduz bytes na rede; RCUs calculados pelo tamanho no storage.")


# ============================================================
# TESTE 4: Paginacao com Limit e LastEvaluatedKey
# ============================================================
def teste4_paginacao():
    sep("TESTE 4: Paginacao com Limit e LastEvaluatedKey")

    PAGE_SIZE = 5
    total_items = 0
    total_pages = 0
    total_rcus = 0
    last_key = None

    print(f"\n  Scan paginado com Limit={PAGE_SIZE}:")

    while True:
        params = {
            'Limit': PAGE_SIZE,
            'ReturnConsumedCapacity': 'TOTAL'
        }
        if last_key:
            params['ExclusiveStartKey'] = last_key

        resp = table.scan(**params)
        total_pages += 1
        total_items += resp['Count']
        total_rcus += resp['ConsumedCapacity']['CapacityUnits']
        last_key = resp.get('LastEvaluatedKey')

        if total_pages <= 3:
            has_more = "continua..." if last_key else "fim"
            print(f"    Pagina {total_pages}: {resp['Count']} itens | RCUs: {resp['ConsumedCapacity']['CapacityUnits']} | {has_more}")
        elif total_pages == 4:
            print(f"    ... (paginando)")

        if not last_key:
            break

    print(f"\n  Total: {total_items} itens em {total_pages} paginas | RCUs totais: {total_rcus:.1f}")
    print(f"  Conclusao: Limit controla itens EXAMINADOS por request, nao retornados.")


# ============================================================
# TESTE 5: ScanIndexForward — ordenacao por Sort Key
# ============================================================
def teste5_scan_index_forward():
    sep("TESTE 5: Ordenacao com ScanIndexForward")

    asc = table.query(
        KeyConditionExpression=Key('PK').eq('USER#0001') & Key('SK').begins_with('ORDER#'),
        ScanIndexForward=True
    )

    desc = table.query(
        KeyConditionExpression=Key('PK').eq('USER#0001') & Key('SK').begins_with('ORDER#'),
        ScanIndexForward=False
    )

    print(f"\n  ScanIndexForward=True  (ASC — padrao):")
    for item in asc['Items']:
        print(f"    {item['SK']}")

    print(f"\n  ScanIndexForward=False (DESC):")
    for item in desc['Items']:
        print(f"    {item['SK']}")

    print(f"\n  Conclusao: ScanIndexForward controla a ordem pela Sort Key sem custo adicional.")


# ============================================================
# EXECUTAR
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("  DynamoDB — Query vs Scan: Comparacao Pratica")
    print("=" * 60)

    teste1_query_vs_scan_por_usuario()
    teste2_filter_nao_reduz_rcu()
    teste3_projection_expression()
    teste4_paginacao()
    teste5_scan_index_forward()

    sep("Resumo")
    print("  Query    — rapida, barata, usa PK  -> USE em producao")
    print("  Scan     — lenta, cara, le tudo    -> EVITE em producao")
    print("  Filter   — nao reduz RCUs          -> pegadinha classsica")
    print("  Project  — reduz rede, nao RCUs    -> util para payloads grandes")
    print("  Limit    — itens examinados, nao retornados")
    print("  Forward  — ScanIndexForward=False para DESC")
    print()
