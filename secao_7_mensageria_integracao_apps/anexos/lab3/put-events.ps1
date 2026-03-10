# put-events.ps1 — Publica eventos no Event Bus customizado do Lab 3
# Pré-requisito: AWS CLI configurado e event bus lab3-bus criado
#
# Como executar:
#   cd path\to\lab3
#   .\put-events.ps1
#
# Caso PowerShell bloqueie a execução, rode antes:
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

$EVENT_BUS = "lab3-bus"

Write-Host "=== Evento 1: status=confirmed (deve acionar a regra e chegar na SQS) ==="
$entry1 = '[{"Source":"lab3.orders","DetailType":"OrderPlaced","Detail":"{\"order_id\":\"ORD-001\",\"status\":\"confirmed\",\"amount\":500}","EventBusName":"lab3-bus"}]'
aws events put-events --entries $entry1

Write-Host ""
Write-Host "=== Evento 2: status=pending (NAO deve chegar na SQS — filtro nao satisfeito) ==="
$entry2 = '[{"Source":"lab3.orders","DetailType":"OrderPlaced","Detail":"{\"order_id\":\"ORD-002\",\"status\":\"pending\",\"amount\":200}","EventBusName":"lab3-bus"}]'
aws events put-events --entries $entry2

Write-Host ""
Write-Host "Aguarde alguns segundos e verifique a fila SQS lab3-events-queue."
Write-Host "Apenas o Evento 1 deve aparecer na fila."
