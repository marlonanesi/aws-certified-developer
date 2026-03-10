# LAB 120 — Métricas Customizadas com EMF na Prática
> **USO INTERNO — Guia do Instrutor**

## Objetivo
Demonstrar PutMetricData via SDK Python e EMF via função Lambda, comparando os dois na prática.

---

## Pré-requisitos
- Python 3.x com boto3 instalado (`pip install boto3 aws-embedded-metrics`)
- Role IAM com: `cloudwatch:PutMetricData`, `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`
- Lambda com runtime Python 3.11+ e a layer `aws-embedded-metrics` ou instalada no pacote

---

## Roteiro do Lab

### Parte 1 — PutMetricData Local (8 min)

Criar arquivo `put_metric.py`:
```python
import boto3
import time

cw = boto3.client('cloudwatch', region_name='us-east-1')

# Publicar uma série de valores simulando carga variável
valores = [10, 35, 72, 48, 91, 23, 67, 15, 82, 44]

for i, valor in enumerate(valores):
    cw.put_metric_data(
        Namespace='MeuCurso/Pedidos',
        MetricData=[
            {
                'MetricName': 'PedidosPorMinuto',
                'Value': valor,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Ambiente', 'Value': 'Producao'},
                    {'Name': 'Regiao', 'Value': 'Sul'}
                ],
                'StorageResolution': 60  # Standard
            }
        ]
    )
    print(f"Publicado ponto {i+1}: {valor} pedidos/min")
    time.sleep(2)

print("Aguarde ~1 minuto e verifique no console CloudWatch")
```

```bash
python put_metric.py
```

No console: CloudWatch → Metrics → Custom → `MeuCurso/Pedidos` → visualizar `PedidosPorMinuto`

**Mostre:** dimensões como filtro, mudança de estatística (Sum, Average, Maximum), período

### Parte 2 — High-Resolution (3 min)
Alterar `StorageResolution` para `1` e rodar de novo:
```python
'StorageResolution': 1  # High-Resolution — 1 segundo
```
No console: mostrar que agora o gráfico tem granularidade de 1 segundo, e ressaltar o custo 5x maior.

### Parte 3 — EMF em Lambda (10 min)

Criar função Lambda `lab-emf-demo` com código:
```python
import json
import time
from aws_embedded_metrics import metric_scope

@metric_scope
async def handler(event, context, metrics):
    # Configurar dimensões e namespace
    metrics.set_namespace("MeuCurso/Pedidos")
    metrics.set_dimensions({"FunctionName": context.function_name, "Ambiente": "Lab"})
    
    # Simular processamento
    start = time.time()
    time.sleep(0.05)  # 50ms de processamento simulado
    latencia = (time.time() - start) * 1000
    
    # Publicar métricas via EMF (zero chamada de API!)
    metrics.put_metric("Latencia", latencia, "Milliseconds")
    metrics.put_metric("PedidosProcessados", 1, "Count")
    
    # Propriedades adicionais ficam no log mas não viram métrica
    metrics.set_property("OrderId", event.get("orderId", "unknown"))
    metrics.set_property("PayloadSize", len(json.dumps(event)))
    
    return {"statusCode": 200, "body": "OK"}
```

**Deploy via console ou CLI:**
```bash
# Empacotar (instalar dependência primeiro)
pip install aws-embedded-metrics -t ./package
cp lambda_function.py ./package/
cd package && zip -r ../lab_emf.zip . && cd ..

# Deploy
aws lambda update-function-code \
  --function-name lab-emf-demo \
  --zip-file fileb://lab_emf.zip
```

**Invocar várias vezes:**
```bash
for i in $(seq 1 10); do
  aws lambda invoke \
    --function-name lab-emf-demo \
    --payload '{"orderId": "ORD-'$i'"}' \
    response.json
  echo "Invocação $i"
done
```

**No console:**
1. CloudWatch → Logs → `/aws/lambda/lab-emf-demo` → ver o JSON estruturado nos logs
2. CloudWatch → Metrics → Custom → `MeuCurso/Pedidos` → ver `Latencia` e `PedidosProcessados`
3. Comparar: **o log e a métrica são o mesmo evento** — mostrar a correlação

### Parte 4 — Comparação Visual (3 min)
Criar um dashboard com:
- Widget 1: `PedidosPorMinuto` (do PutMetricData) — Line chart
- Widget 2: `Latencia` do Lambda (do EMF) — Number com p99
- Mostrar os dois lado a lado

---

## Pontos de Atenção para Gravação
- Instalar `aws-embedded-metrics` antes de gravar a parte do Lambda
- Aguardar ~1 min após invocações para métricas aparecerem
- Mostrar o JSON raw do log para demonstrar como o EMF se parece
- Reforçar: EMF = log com estrutura especial. Não há chamada extra de API.

## Cleanup
```bash
aws lambda delete-function --function-name lab-emf-demo
# Deletar namespace de métricas: não há API direta, métricas expiram conforme retenção
```
