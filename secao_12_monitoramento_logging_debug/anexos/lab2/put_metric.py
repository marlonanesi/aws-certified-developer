"""
Publica métricas customizadas no CloudWatch via PutMetricData (boto3).

Simula carga variável de pedidos, demonstrando:
- Standard Resolution (StorageResolution=60): granularidade de 1 minuto
- High-Resolution (StorageResolution=1): granularidade de 1 segundo

Uso:
    python put_metric.py
"""
import boto3
import time

REGION = "us-east-1"
NAMESPACE = "MeuCurso/Pedidos"
DIMENSOES = [
    {"Name": "Ambiente", "Value": "Producao"},
    {"Name": "Regiao", "Value": "Sul"},
]

cw = boto3.client("cloudwatch", region_name=REGION)

# ============================================================
# Parte 1 — Standard Resolution (StorageResolution=60)
# ============================================================
valores_standard = [10, 35, 72, 48, 91, 23, 67, 15, 82, 44]

print("=== Standard Resolution (60s) ===")
for i, valor in enumerate(valores_standard, start=1):
    cw.put_metric_data(
        Namespace=NAMESPACE,
        MetricData=[
            {
                "MetricName": "PedidosPorMinuto",
                "Value": valor,
                "Unit": "Count",
                "Dimensions": DIMENSOES,
                "StorageResolution": 60,
            }
        ],
    )
    print(f"  [{i:>2}/{len(valores_standard)}] PedidosPorMinuto={valor} (Standard)")
    time.sleep(2)

print()
print("Aguarde ~1 minuto e verifique no console:")
print("  CloudWatch → Metrics → Custom namespaces → MeuCurso/Pedidos")
print()

# ============================================================
# Parte 2 — High-Resolution (StorageResolution=1)
# ============================================================
valores_hr = [20, 45, 80, 10, 95]

print("=== High-Resolution (1s) — altere StorageResolution para comparar ===")
for i, valor in enumerate(valores_hr, start=1):
    cw.put_metric_data(
        Namespace=NAMESPACE,
        MetricData=[
            {
                "MetricName": "PedidosPorMinutoHR",
                "Value": valor,
                "Unit": "Count",
                "Dimensions": DIMENSOES,
                "StorageResolution": 1,
            }
        ],
    )
    print(f"  [{i}/{len(valores_hr)}] PedidosPorMinutoHR={valor} (High-Res)")
    time.sleep(1)

print()
print("=== Concluido ===")
print("Compare PedidosPorMinuto x PedidosPorMinutoHR no console:")
print("  mesmo namespace, granularidade diferente no gráfico.")
