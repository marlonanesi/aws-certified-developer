#!/bin/bash
# put-events.sh — Publica eventos no Event Bus customizado do Lab 3
# Pré-requisito: AWS CLI configurado e event bus lab3-bus criado

EVENT_BUS="lab3-bus"

echo "=== Evento 1: status=confirmed (deve acionar a regra e chegar na SQS) ==="
aws events put-events \
  --entries "[{
    \"Source\": \"lab3.orders\",
    \"DetailType\": \"OrderPlaced\",
    \"Detail\": \"{\\\"order_id\\\": \\\"ORD-001\\\", \\\"status\\\": \\\"confirmed\\\", \\\"amount\\\": 500}\",
    \"EventBusName\": \"$EVENT_BUS\"
  }]"

echo ""
echo "=== Evento 2: status=pending (NÃO deve chegar na SQS — filtro não satisfeito) ==="
aws events put-events \
  --entries "[{
    \"Source\": \"lab3.orders\",
    \"DetailType\": \"OrderPlaced\",
    \"Detail\": \"{\\\"order_id\\\": \\\"ORD-002\\\", \\\"status\\\": \\\"pending\\\", \\\"amount\\\": 200}\",
    \"EventBusName\": \"$EVENT_BUS\"
  }]"

echo ""
echo "Aguarde alguns segundos e verifique a fila SQS lab3-events-queue."
echo "Apenas o Evento 1 deve aparecer na fila."
