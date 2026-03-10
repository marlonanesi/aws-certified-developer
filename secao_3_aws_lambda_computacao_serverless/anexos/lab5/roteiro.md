# Lab 5 – DLQ e Destinations para Tratamento de Erros

> **Compatibilidade de comandos CLI**
> Os comandos avulsos deste roteiro funcionam diretamente em **PowerShell** (Windows) e **Bash** (Linux/macOS/Git Bash) — basta colar e executar.
> Onde há diferença de sintaxe entre os dois shells, o roteiro apresenta as duas versões lado a lado.
> Para CMD ou outros terminais, converta a sintaxe com ajuda de IA generativa.

---
> **Custos e Free Tier**
> - **AWS Lambda:** 1 milhão de invocações gratuitas/mês (permanente)
> - **Amazon SQS:** 1 milhão de requisições gratuitas/mês (permanente)
> - **Amazon CloudWatch Logs:** 5 GB de ingestão gratuita/mês (primeiros 12 meses)
>
> Para os volumes de teste deste lab, o custo tende a ser zero.
>
> ⚠️ **Aviso importante:** qualquer recurso provisionado na AWS pode gerar custos mesmo dentro do free tier, que possui limites mensais. Ao concluir o lab, execute a etapa de limpeza para evitar cobranças inesperadas.

---
## Objetivo

Configurar **Lambda Destinations** para capturar resultados de invocações assíncronas — tanto sucessos (`OnSuccess`) quanto falhas (`OnFailure`) — e comparar com o modelo legado de DLQ. Observar o fluxo completo de retries e o conteúdo das mensagens nas filas SQS.

---
## Pré-requisitos

- AWS CLI configurada com permissões em Lambda, SQS e IAM
- `python3` disponível localmente (para parse de JSON nas saídas)

---
## Arquitetura do Lab

```
Invocação assíncrona (CLI)
    └─> Lambda
          ├─ Sucesso  ──> SQS: lambda-destino-sucesso
          └─ Falha    ──> SQS: lambda-destino-falha
                (após 2 retentativas automáticas)
```

---
## Parte 1 – Criar as Filas SQS

```
# Fila para eventos bem-sucedidos
aws sqs create-queue --queue-name lambda-destino-sucesso --attributes VisibilityTimeout=60

# Fila para eventos com falha (Destination de falha)
aws sqs create-queue --queue-name lambda-destino-falha --attributes VisibilityTimeout=60

# Capturar ARNs
$FILA_SUCESSO_URL = aws sqs get-queue-url --queue-name lambda-destino-sucesso --query QueueUrl --output text
$FILA_SUCESSO_ARN = aws sqs get-queue-attributes --queue-url $FILA_SUCESSO_URL --attribute-names QueueArn --query Attributes.QueueArn --output text

$FILA_FALHA_URL = aws sqs get-queue-url --queue-name lambda-destino-falha --query QueueUrl --output text
$FILA_FALHA_ARN = aws sqs get-queue-attributes --queue-url $FILA_FALHA_URL --attribute-names QueueArn --query Attributes.QueueArn --output text

Write-Host "Sucesso ARN: $FILA_SUCESSO_ARN"
Write-Host "Falha ARN: $FILA_FALHA_ARN"
```

---
## Parte 2 – Criar a IAM Role

```
# Trust policy (arquivo trust-policy.json incluído nesta pasta)
aws iam create-role --role-name lambda-dlq-role --assume-role-policy-document file://trust-policy.json

aws iam attach-role-policy --role-name lambda-dlq-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Criar policy inline com permissão para enviar mensagens SQS
@"
{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Allow", "Action": "sqs:SendMessage", "Resource": ["$FILA_SUCESSO_ARN", "$FILA_FALHA_ARN"]}]
}
"@ | Set-Content sqs-policy.json

aws iam put-role-policy --role-name lambda-dlq-role --policy-name SQSSendMessagePolicy --policy-document file://sqs-policy.json

$ROLE_ARN = aws iam get-role --role-name lambda-dlq-role --query Role.Arn --output text
Write-Host "Role ARN: $ROLE_ARN"

Start-Sleep -Seconds 10  # aguardar propagação da role
```

---
## Parte 3 – Criar a Função Lambda

```
Compress-Archive -Path lambda_dlq_demo.py -DestinationPath lambda_dlq_demo.zip -Force

aws lambda create-function --function-name demo-dlq-destinations --runtime python3.12 --handler lambda_dlq_demo.lambda_handler --zip-file fileb://lambda_dlq_demo.zip --role $ROLE_ARN --timeout 30

aws lambda wait function-active --function-name demo-dlq-destinations
```

---
## Parte 4 – Configurar Destinations

```
$destConfig = '{"OnSuccess":{"Destination":"' + $FILA_SUCESSO_ARN + '"},"OnFailure":{"Destination":"' + $FILA_FALHA_ARN + '"}}'
aws lambda put-function-event-invoke-config --function-name demo-dlq-destinations --maximum-retry-attempts 2 --maximum-event-age-in-seconds 3600 --destination-config $destConfig

# Verificar
aws lambda get-function-event-invoke-config --function-name demo-dlq-destinations
```

---
## Parte 5 – Testar o Fluxo

### Teste 1 – Invocação com sucesso

```
# --invocation-type Event = assíncrono (retorna status 202 imediatamente)
aws lambda invoke --function-name demo-dlq-destinations --invocation-type Event --payload '{"acao": "sucesso", "pedido_id": "PED-001"}' --cli-binary-format raw-in-base64-out "$env:TEMP\invoke_out.json" | Out-Null

Start-Sleep -Seconds 5

aws sqs receive-message --queue-url $FILA_SUCESSO_URL --max-number-of-messages 5
```

A mensagem na fila de sucesso contém o evento original, a resposta da função e metadados (request ID, versão).

### Teste 2 – Invocação com falha

```
aws lambda invoke --function-name demo-dlq-destinations --invocation-type Event --payload '{"acao": "falhar", "pedido_id": "PED-ERRO-002"}' --cli-binary-format raw-in-base64-out "$env:TEMP\invoke_out.json" | Out-Null

Write-Host "Aguardando 2 retentativas automaticas + envio para DLQ (~90 segundos)..."
Start-Sleep -Seconds 90

aws sqs receive-message --queue-url $FILA_FALHA_URL --max-number-of-messages 1
```

### Teste 3 – Múltiplas invocações (mix sucesso/falha)

```
foreach ($ACAO in @("sucesso", "sucesso", "falhar", "sucesso", "falhar")) {
  $ID = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
  aws lambda invoke --function-name demo-dlq-destinations --invocation-type Event --payload "{`"acao`": `"$ACAO`", `"id`": `"$ID`"}" --cli-binary-format raw-in-base64-out "$env:TEMP\invoke_out.json" | Out-Null
  Write-Host "Enviado: $ACAO"
  Start-Sleep -Seconds 1
}

Write-Host "Aguardando processamento completo (~2 minutos para as falhas)..."
Start-Sleep -Seconds 120

Write-Host "=== Mensagens na fila de sucesso ==="
aws sqs get-queue-attributes --queue-url $FILA_SUCESSO_URL --attribute-names ApproximateNumberOfMessages

Write-Host "=== Mensagens na fila de falha ==="
aws sqs get-queue-attributes --queue-url $FILA_FALHA_URL --attribute-names ApproximateNumberOfMessages
```

---
## Parte 6 – Comparação: Destinations vs DLQ Legada

| | Destinations | DLQ Legada |
|---|---|---|
| Captura eventos de sucesso | ✅ `OnSuccess` | ❌ |
| Captura eventos de falha | ✅ `OnFailure` | ✅ |
| Payload na fila | Evento + resposta + contexto completo | Apenas o evento original |
| Destinos suportados | SQS, SNS, Lambda, EventBridge | SQS, SNS |
| Configuração de retries | ✅ Controlável | Herdado do event source |
## Parte 7 – Reprocessamento de Mensagens com Falha

```
$MSG = aws sqs receive-message --queue-url $FILA_FALHA_URL --max-number-of-messages 1

Write-Host "Mensagem para reprocessar:"
$MSG | python -c "import sys, json; d=json.loads(sys.stdin.read()); body=json.loads(d['Messages'][0]['Body']); print(json.dumps(body, indent=2))" 2>$null

# Após corrigir o problema, reenviar com acao de sucesso
aws lambda invoke --function-name demo-dlq-destinations --invocation-type Event --payload '{"acao": "sucesso", "reprocessado": true, "pedido_id": "PED-ERRO-002"}' --cli-binary-format raw-in-base64-out "$env:TEMP\invoke_out.json" | Out-Null
```

---
## Pontos de Verificação

- Status `202` na invocação assíncrona significa "aceito", não "concluído"
- O Lambda realmente aguarda as 2 retentativas antes de enviar para o Destination de falha — o delay de ~90 s é real
- Compare o conteúdo das mensagens nas duas filas: a de falha inclui `errorType` e `errorMessage`
- Logs no CloudWatch Logs Insights permitem filtrar por `RequestId` para rastrear toda a cadeia

---
## Limpeza

```
aws lambda delete-function --function-name demo-dlq-destinations
aws sqs delete-queue --queue-url $FILA_SUCESSO_URL
aws sqs delete-queue --queue-url $FILA_FALHA_URL
aws iam detach-role-policy --role-name lambda-dlq-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam delete-role-policy --role-name lambda-dlq-role --policy-name SQSSendMessagePolicy
aws iam delete-role --role-name lambda-dlq-role
Remove-Item -Force lambda_dlq_demo.zip, sqs-policy.json -ErrorAction SilentlyContinue
```
