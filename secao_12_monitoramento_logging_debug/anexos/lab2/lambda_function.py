"""
Função Lambda com Embedded Metrics Format (EMF).

Publica métricas diretamente via log estruturado — nenhuma chamada extra
de API ao CloudWatch. O agente do Lambda detecta o JSON com _aws e cria
as métricas automaticamente.

Dependência: aws-embedded-metrics
    pip install aws-embedded-metrics

Deploy:
    Instale a dependência no diretório do pacote, compacte e faça deploy
    conforme o roteiro.md deste lab.
"""
import json
import time

from aws_embedded_metrics import metric_scope


@metric_scope
async def lambda_handler(event, context, metrics):
    # Namespace e dimensões do EMF
    metrics.set_namespace("MeuCurso/Pedidos")
    metrics.set_dimensions(
        {"FunctionName": context.function_name, "Ambiente": "Lab"}
    )

    # Simular processamento com latência mensurável
    inicio = time.time()
    time.sleep(0.05)  # 50 ms simulados
    latencia_ms = (time.time() - inicio) * 1000

    # Publicar métricas via EMF — são escritas no log, não via API
    metrics.put_metric("Latencia", latencia_ms, "Milliseconds")
    metrics.put_metric("PedidosProcessados", 1, "Count")

    # Propriedades extras ficam no log mas NÃO viram métricas (não indexadas)
    metrics.set_property("OrderId", event.get("orderId", "desconhecido"))
    metrics.set_property("PayloadSize", len(json.dumps(event)))
    metrics.set_property("FunctionVersion", context.function_version)

    # Simular erro pontual para demonstrar métrica de falha
    if event.get("forceError"):
        metrics.put_metric("Erros", 1, "Count")
        raise ValueError(f"Erro simulado para orderId={event.get('orderId')}")

    return {
        "statusCode": 200,
        "body": json.dumps(
            {"orderId": event.get("orderId"), "latencia_ms": round(latencia_ms, 2)}
        ),
    }
