# LAB 123 — AWS X-Ray na Prática
> **USO INTERNO — Guia do Instrutor**

## Objetivo
Instrumentar uma aplicação Lambda simples com X-Ray SDK, visualizar traces no console, criar annotations e demonstrar o Service Map.

---

## Pré-requisitos
- Função Lambda Python com Active Tracing habilitado
- Role com permissões: `xray:PutTraceSegments`, `xray:PutTelemetryRecords`, `xray:GetSamplingRules`
- DynamoDB table `LabOrders` (PK: `orderId` String) na mesma região
- S3 bucket com leitura pública (ou qualquer bucket que o role Lambda possa ler)

---

## Roteiro do Lab

### Parte 1 — Habilitar Active Tracing no Lambda (3 min)
1. Console Lambda → selecionar função → **Configuration → Monitoring and operations tools**
2. Habilitar **Active tracing (X-Ray)**
3. Verificar que o role tem as permissões de X-Ray (CloudWatch mostrará erro se não tiver)

Via CLI (alternativa para mostrar IaC):
```bash
aws lambda update-function-configuration \
  --function-name lab-xray-demo \
  --tracing-config Mode=Active
```

### Parte 2 — Criar Função Lambda Instrumentada (10 min)

Código `lambda_function.py`:
```python
import json
import boto3
import time
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

# Patcha automaticamente boto3, requests, etc.
patch_all()

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('LabOrders')

def handler(event, context):
    order_id = event.get('orderId', 'ORD-001')
    
    # Adicionar annotation — vai aparecer nos filtros de busca
    xray_recorder.current_segment().put_annotation('orderId', order_id)
    xray_recorder.current_segment().put_annotation('environment', 'lab')
    
    # Adicionar metadata — contexto de debug, não indexado
    xray_recorder.current_segment().put_metadata('event_payload', event)
    xray_recorder.current_segment().put_metadata('function_version', context.function_version)
    
    # Subsegmento manual para operação de negócio
    with xray_recorder.in_subsegment('validacao-pedido') as subseg:
        subseg.put_annotation('status', 'valid')
        time.sleep(0.02)  # simula validação
    
    # Chamada ao DynamoDB — automaticamente rastreada pelo patch_all
    with xray_recorder.in_subsegment('persistir-pedido'):
        table.put_item(Item={
            'orderId': order_id,
            'status': 'processado',
            'timestamp': str(time.time())
        })
    
    return {
        'statusCode': 200,
        'body': json.dumps({'orderId': order_id, 'status': 'ok'})
    }
```

**Deploy:**
```bash
pip install aws-xray-sdk -t ./package
cp lambda_function.py ./package/
cd package && zip -r ../lab_xray.zip . && cd ..

aws lambda update-function-code \
  --function-name lab-xray-demo \
  --zip-file fileb://lab_xray.zip
```

### Parte 3 — Gerar Traces (5 min)
```bash
# Invocar várias vezes com diferentes orderId
for i in ORD-001 ORD-002 ORD-003 ORD-004 ORD-005; do
  aws lambda invoke \
    --function-name lab-xray-demo \
    --payload "{"orderId": "$i"}" \
    response.json
  echo "Invocado com orderId=$i"
  sleep 1
done

# Simular um erro (tabela que não existe)
aws lambda invoke \
  --function-name lab-xray-demo \
  --payload '{"orderId": "ERR-001", "forceError": true}' \
  response.json
```

### Parte 4 — Analisar no Console X-Ray (8 min)

**Service Map:**
1. Console → X-Ray → **Service Map**
2. Mostrar os nós: Client → Lambda → DynamoDB
3. Clicar no nó Lambda: ver latência média, taxa de erro, percentis
4. Clicar no nó DynamoDB: ver latência de cada chamada PutItem

**Traces:**
1. X-Ray → **Traces**
2. Filtrar por annotation: `annotation.orderId = "ORD-003"`
3. Abrir o trace → mostrar a hierarquia: Segment Lambda → Subsegment validacao-pedido → Subsegment DynamoDB PutItem
4. Mostrar os tempos de cada subsegmento
5. Ir em **Metadata** e mostrar o event_payload que não aparece no filtro
6. Ir em **Annotations** e mostrar orderId e environment

**X-Ray Analytics (bônus):**
1. X-Ray → **Analytics**
2. Criar filtro `annotation.environment = "lab"` no grupo de referência
3. Mostrar histograma de latência
4. Mostrar a tabela de annotations mais frequentes

### Parte 5 — Regra de Sampling Customizada (3 min)
1. X-Ray → **Sampling rules → Create sampling rule**
2. Nome: `lab-checkout-full`
3. Service name: `lab-xray-demo`
4. URL path: `/checkout*`
5. Reservoir: 10, Rate: 1.0 (100%)
6. Mostrar que mudança entra em vigor sem nenhum deploy

---

## Pontos de Atenção para Gravação
- `patch_all()` deve ser chamado ANTES de qualquer importação de serviço AWS
- Aguardar ~30 segundos após invocações para traces aparecerem no console
- Mostrar o Service Map ANTES de abrir um trace individual — impacto visual é maior
- Reforçar: annotations são indexadas, metadata não — a prova cobra muito isso
- Se DynamoDB demorar para aparecer no Service Map, invocar mais 2-3 vezes

## Cleanup
```bash
# Deletar sampling rule
aws xray delete-sampling-rule --rule-name lab-checkout-full

# Desabilitar Active Tracing
aws lambda update-function-configuration \
  --function-name lab-xray-demo \
  --tracing-config Mode=PassThrough

# Limpar tabela DynamoDB
aws dynamodb delete-table --table-name LabOrders
```
