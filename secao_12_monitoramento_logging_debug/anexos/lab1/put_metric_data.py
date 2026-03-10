"""
Publica métricas customizadas no CloudWatch via PutMetricData.

Namespace: MeuCurso/Lab
Métrica:   PedidosSimulados
Dimensão:  Ambiente=Dev

Uso:
    python put_metric_data.py
"""
import boto3
import time

REGION = "us-east-1"
NAMESPACE = "MeuCurso/Lab"
METRIC_NAME = "PedidosSimulados"
DIMENSAO = [{"Name": "Ambiente", "Value": "Dev"}]

cw = boto3.client("cloudwatch", region_name=REGION)


def publicar(valor: float, resolucao: int = 60) -> None:
    """
    Publica um ponto de dado no CloudWatch.

    Args:
        valor: Valor numérico da métrica
        resolucao: 60 = Standard, 1 = High-Resolution (5x mais caro)
    """
    cw.put_metric_data(
        Namespace=NAMESPACE,
        MetricData=[
            {
                "MetricName": METRIC_NAME,
                "Value": valor,
                "Unit": "Count",
                "Dimensions": DIMENSAO,
                "StorageResolution": resolucao,
            }
        ],
    )


if __name__ == "__main__":
    # 1. Publicar ponto único de demonstração
    print("=== Publicando ponto único (valor=42) ===")
    publicar(42)
    print("  Publicado: PedidosSimulados=42")
    print()

    # 2. Publicar série de valores para gerar histórico no gráfico
    valores = [10, 25, 50, 15, 38, 72, 5, 90, 30, 60]
    print(f"=== Publicando série de {len(valores)} pontos (Standard Resolution) ===")
    for i, v in enumerate(valores, start=1):
        publicar(v, resolucao=60)
        print(f"  [{i:>2}/{len(valores)}] PedidosSimulados={v}")
        time.sleep(2)

    print()
    print("=== Publicando com High-Resolution (StorageResolution=1) ===")
    valores_hr = [20, 45, 80]
    for i, v in enumerate(valores_hr, start=1):
        publicar(v, resolucao=1)
        print(f"  [{i}/{len(valores_hr)}] PedidosSimulados={v} (High-Res)")
        time.sleep(1)

    print()
    print("Concluido. Aguarde ~1 minuto e verifique no console:")
    print("  CloudWatch → Metrics → Custom namespaces → MeuCurso/Lab")
