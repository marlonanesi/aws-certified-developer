# Lab — DynamoDB Streams com AWS Lambda (Change Data Capture)

> **Aviso de compatibilidade de comandos**
> Os comandos deste roteiro sao referencias e podem precisar de adaptacao
> conforme o SO e terminal utilizados (PowerShell, Bash, Zsh, CMD, etc.).
> Converta a sintaxe antes de executar se necessario.
>
> Sugestao de prompt para IA generativa:
> "Converta o comando abaixo para meu SO [Windows/macOS/Linux] e terminal
> [PowerShell/Bash/Zsh/CMD]. Adapte variaveis, redirecionamentos e pipes
> para o equivalente nesse ambiente: <cole o comando aqui>"

> **Aviso de custos:** Recursos criados na AWS podem gerar cobranças. O Lambda tem nível gratuito permanente de 1 milhão de invocações/mês. O DynamoDB Streams e Event Source Mapping não têm custo próprio, mas as leituras do stream consomem RCUs. A tabela usa modo **provisionado com 5 RCU e 5 WCU** — dentro do nível gratuito permanente de 25 RCU e 25 WCU, compartilhado entre todas as tabelas da conta. Revise a aba **Billing** ao final. **Desprovisione todos os recursos ao terminar** — o roteiro de cleanup remove todos os componentes criados.

---
## Objetivo

Habilitar DynamoDB Streams em uma tabela, criar uma função Lambda que processa eventos de mudança em tempo real (CDC — Change Data Capture), e observar os três tipos de evento: INSERT, MODIFY e REMOVE.

---
## Arquitetura

```
DynamoDB Table  →  DynamoDB Stream  →  Lambda Function  →  CloudWatch Logs
   (CRUD)           (CDC events)        (processamento)      (auditoria)
```

---
## Pré-requisitos

- AWS CLI configurada com permissões para DynamoDB, Lambda, IAM e CloudWatch Logs
- Python 3.x disponível localmente (para executar o script de geração de eventos)

---
## Parte 1 — Criar Tabela com Stream Habilitado

```
aws dynamodb create-table --table-name DVA-Lab-StreamsDemo --key-schema AttributeName=PK,KeyType=HASH AttributeName=SK,KeyType=RANGE --attribute-definitions AttributeName=PK,AttributeType=S AttributeName=SK,AttributeType=S --billing-mode PROVISIONED --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES

aws dynamodb wait table-exists --table-name DVA-Lab-StreamsDemo
echo "Tabela criada com Stream habilitado."
```

Anote o Stream ARN para uso posterior:

```
aws dynamodb describe-table --table-name DVA-Lab-StreamsDemo --query "Table.LatestStreamArn" --output text
```

---
## Parte 2 — Criar IAM Role para a Lambda

```
aws iam create-role --role-name DVA-Lab-StreamsLambdaRole --assume-role-policy-document file://trust-policy.json

aws iam attach-role-policy --role-name DVA-Lab-StreamsLambdaRole --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy --role-name DVA-Lab-StreamsLambdaRole --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaDynamoDBExecutionRole

echo "Role criada. Aguarde 10 segundos para propagacao..."
sleep 10
```

---
## Parte 3 — Criar e Publicar a Função Lambda

O arquivo `stream_processor.py` contém o handler que processa os eventos do stream.

1. Empacote o código:

   ```
   zip stream_processor.zip stream_processor.py
   ```

2. Obtenha o ARN da role:

   ```
   ROLE_ARN=$(aws iam get-role --role-name DVA-Lab-StreamsLambdaRole --query "Role.Arn" --output text)
   ```

3. Crie a função:

   ```
   aws lambda create-function --function-name DVA-Lab-StreamProcessor --runtime python3.12 --handler stream_processor.lambda_handler --role $ROLE_ARN --zip-file fileb://stream_processor.zip --timeout 30 --memory-size 128
   ```

---
## Parte 4 — Conectar Stream ao Lambda (Event Source Mapping)

```
$STREAM_ARN = aws dynamodb describe-table --table-name DVA-Lab-StreamsDemo --query "Table.LatestStreamArn" --output text

aws lambda create-event-source-mapping --function-name DVA-Lab-StreamProcessor --event-source-arn $STREAM_ARN --starting-position LATEST --batch-size 10 --maximum-batching-window-in-seconds 5
```

Verifique que o mapping está **Enabled**:

```
aws lambda list-event-source-mappings --function-name DVA-Lab-StreamProcessor --query "EventSourceMappings[*].{UUID:UUID,Estado:State,BatchSize:BatchSize}"
```

> Aguarde o estado `Enabled` antes de gerar eventos (pode levar 1–2 minutos).

---
## Parte 5 — Gerar Eventos e Observar no CloudWatch

1. Execute o script que gera INSERT, MODIFY e REMOVE:

   ```
   python gerar_eventos.py
   ```

2. Aguarde aproximadamente 30 segundos e busque os logs:

   ```
   LOG_GROUP="/aws/lambda/DVA-Lab-StreamProcessor"

   LOG_STREAM=$(aws logs describe-log-streams --log-group-name $LOG_GROUP --order-by LastEventTime --descending --limit 1 --query "logStreams[0].logStreamName" --output text)

   aws logs get-log-events --log-group-name $LOG_GROUP --log-stream-name "$LOG_STREAM" --query "events[*].message" --output text
   ```

3. No console, explore:
   - **DynamoDB > Tables > DVA-Lab-StreamsDemo > Exports and streams** ("Exportações e streams") — veja os Shard IDs
   - **Lambda > DVA-Lab-StreamProcessor > Configuration** ("Configuração") **> Triggers** ("Acionadores") — observe o trigger ativo
   - **CloudWatch > Log groups** — leia os logs estruturados gerados pelo processador

---
## Pontos de Verificação

- [ ] Tabela criada com `StreamViewType=NEW_AND_OLD_IMAGES`
- [ ] Event Source Mapping em estado **Enabled**
- [ ] Log do evento INSERT mostra os campos do novo item
- [ ] Log do evento MODIFY mostra o campo que mudou (status: pending → shipped → delivered)
- [ ] Log do evento REMOVE mostra os dados do item antes da exclusão
- [ ] Tipo de deleção identificado corretamente (manual vs TTL via `userIdentity`)

---
## Conceitos Reforçados

- **DynamoDB Streams** captura INSERT, MODIFY e REMOVE em near real-time
- **NEW\_AND\_OLD\_IMAGES** é o view type mais completo — mostra estado anterior e posterior
- **LATEST vs TRIM\_HORIZON**: LATEST processa apenas novos eventos; TRIM\_HORIZON reprocessa todo o histórico disponível (24h)
- **Batch size** e **batch window** agrupam eventos para reduzir invocações
- Deleções por **TTL** chegam no stream com `userIdentity.type = Service`
- Em caso de erro na Lambda, o batch inteiro é re-tentado — a Lambda deve ser **idempotente**
- Retenção do stream é de **24 horas** — eventos mais antigos são descartados automaticamente
- **Bisect on function error** divide o batch ao meio para isolar o item problemático

---
## Cleanup

> **Importante:** Remova todos os recursos para evitar cobranças.

```
# 1. Remover Event Source Mapping
$UUID = aws lambda list-event-source-mappings --function-name DVA-Lab-StreamProcessor --query "EventSourceMappings[0].UUID" --output text
aws lambda delete-event-source-mapping --uuid $UUID

# 2. Deletar Lambda
aws lambda delete-function --function-name DVA-Lab-StreamProcessor

# 3. Deletar tabela (stream é deletado junto)
aws dynamodb delete-table --table-name DVA-Lab-StreamsDemo

# 4. Deletar Role IAM
aws iam detach-role-policy --role-name DVA-Lab-StreamsLambdaRole --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam detach-role-policy --role-name DVA-Lab-StreamsLambdaRole --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaDynamoDBExecutionRole
aws iam delete-role --role-name DVA-Lab-StreamsLambdaRole

# 5. Deletar Log Group
aws logs delete-log-group --log-group-name /aws/lambda/DVA-Lab-StreamProcessor

Write-Host "Todos os recursos removidos."
```
