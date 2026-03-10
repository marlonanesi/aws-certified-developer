"""
Função Lambda instrumentada com AWS X-Ray SDK.

Demonstra:
- patch_all() para rastreamento automático de clientes boto3
- Subsegmentos manuais com xray_recorder.in_subsegment()
- Annotations (indexadas — usadas em filtros de busca de traces)
- Metadata (não indexada — contexto de debug)

Dependência: aws-xray-sdk
    pip install aws-xray-sdk

Requisitos de infraestrutura:
- Active Tracing habilitado na função Lambda
- Role com: xray:PutTraceSegments, xray:PutTelemetryRecords, xray:GetSamplingRules
- Tabela DynamoDB 'LabOrders' (PK: orderId, tipo String) na mesma região
"""
import json
import time

import boto3
from aws_xray_sdk.core import patch_all, xray_recorder

# patch_all() deve ser chamado ANTES de qualquer uso de cliente AWS
# Ele instrumenta automaticamente boto3, requests, httplib, entre outros
patch_all()

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("LabOrders")


def lambda_handler(event, context):
    order_id = event.get("orderId", "ORD-000")

    # Annotations são indexadas — aparecem nos filtros de busca de traces
    xray_recorder.current_segment().put_annotation("orderId", order_id)
    xray_recorder.current_segment().put_annotation("environment", "lab")

    # Metadata não é indexada — visível no detalhe do trace, mas não pesquisável
    xray_recorder.current_segment().put_metadata("event_payload", event)
    xray_recorder.current_segment().put_metadata(
        "function_version", context.function_version
    )

    # Subsegmento manual: representa uma etapa de negócio rastreada explicitamente
    with xray_recorder.in_subsegment("validacao-pedido") as subseg:
        subseg.put_annotation("validacao_status", "ok")
        time.sleep(0.02)  # ~20 ms simulados de validação

    # Subsegmento manual para a escrita no DynamoDB
    # (a chamada boto3 já seria rastreada pelo patch_all, mas o subsegmento
    #  manual permite adicionar contexto de negócio ao traço)
    with xray_recorder.in_subsegment("persistir-pedido"):
        if event.get("forceError"):
            # Simular erro para demonstrar traces com falha no Service Map
            xray_recorder.current_segment().put_annotation("error", True)
            raise ValueError(f"Erro simulado para orderId={order_id}")

        table.put_item(
            Item={
                "orderId": order_id,
                "status": "processado",
                "timestamp": str(time.time()),
            }
        )

    return {
        "statusCode": 200,
        "body": json.dumps({"orderId": order_id, "status": "ok"}),
    }
