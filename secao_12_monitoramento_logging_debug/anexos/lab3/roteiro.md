# Lab — AWS X-Ray: Rastreamento Distribuído com Lambda e DynamoDB

> **Compatibilidade de comandos CLI**
> Este roteiro apresenta blocos para **PowerShell** (Windows) e **Bash** (Linux/macOS/Git Bash/WSL).
> Comandos de empacotar/copiar arquivos diferem entre os terminais — ambas as versões estão documentadas.
> CMD não é suportado; use PowerShell ou Bash.

> **Aviso de custos:** X-Ray tem Free Tier de 100.000 traces registrados e 1 milhão de traces recuperados por mês (permanente). Este lab gera menos de 20 traces. Lambda tem 1 milhão de invocações gratuitas. DynamoDB on-demand tem Free Tier permanente de 25 WCU/RCU. **Desprovisione ao finalizar.**

---
## Objetivo

Instrumentar uma função Lambda com o AWS X-Ray SDK, visualizar traces no console, analisar o Service Map (Lambda → DynamoDB), criar annotations e metadata, e configurar uma regra de sampling customizada.

---
## Pré-requisitos

- AWS CLI configurada com credenciais válidas
- Python 3.x com `aws-xray-sdk`:

  ```shell
  pip install aws-xray-sdk boto3
  ```

- Permissões IAM: `lambda:*`, `iam:CreateRole`, `iam:AttachRolePolicy`, `dynamodb:CreateTable`, `dynamodb:PutItem`, `xray:GetServiceGraph`, `xray:GetTraceSummaries`, `xray:CreateSamplingRule`, `xray:DeleteSamplingRule`

---
## Parte 1 — Criar a Infraestrutura de Suporte

### Tabela DynamoDB

```
aws dynamodb create-table --table-name LabOrders --attribute-definitions AttributeName=orderId,AttributeType=S --key-schema AttributeName=orderId,KeyType=HASH --billing-mode PAY_PER_REQUEST
```

Aguarde o status `ACTIVE`:

```
aws dynamodb describe-table --table-name LabOrders --query "Table.TableStatus"
```

### Role IAM para a Lambda

**PowerShell:**
```powershell
$trustPolicy = '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
aws iam create-role --role-name lab-xray-role --assume-role-policy-document $trustPolicy
```

**Bash:**
```bash
TRUST_POLICY='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
aws iam create-role --role-name lab-xray-role --assume-role-policy-document "$TRUST_POLICY"
```

```
aws iam attach-role-policy --role-name lab-xray-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy --role-name lab-xray-role --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

aws iam attach-role-policy --role-name lab-xray-role --policy-arn arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess
```

> A policy `AWSXRayDaemonWriteAccess` concede as permissões `xray:PutTraceSegments`, `xray:PutTelemetryRecords` e `xray:GetSamplingRules` necessárias para o X-Ray SDK enviar dados.

> Aguarde ~10 segundos para a role propagar.

---
## Parte 2 — Empacotar e Fazer Deploy da Lambda

Antes de criar a função, obtenha o Account ID:

```
aws sts get-caller-identity --query Account --output text
```

Substitua `<ACCOUNT_ID>` nos comandos desta parte pelo valor retornado acima.

Instale a dependência no diretório do pacote:

```
pip install aws-xray-sdk -t ./package
```

Copie o código da função:

**PowerShell:**
```powershell
Copy-Item lambda_function.py package\lambda_function.py
```

**Bash:**
```bash
cp lambda_function.py package/lambda_function.py
```

Compacte o pacote:

**PowerShell:**
```powershell
Compress-Archive -Path .\package\* -DestinationPath lab_xray.zip -Force
```

**Bash:**
```bash
cd package && zip -r ../lab_xray.zip . && cd ..
```

Criar a função Lambda (substitua `<ACCOUNT_ID>`):

```
aws lambda create-function --function-name lab-xray-demo --runtime python3.12 --role arn:aws:iam::<ACCOUNT_ID>:role/lab-xray-role --handler lambda_function.lambda_handler --zip-file fileb://lab_xray.zip --timeout 30
```

---
## Parte 3 — Habilitar Active Tracing no Lambda

```
aws lambda update-function-configuration --function-name lab-xray-demo --tracing-config Mode=Active
```

Confirmar:

```
aws lambda get-function-configuration --function-name lab-xray-demo --query "TracingConfig"
```

> **Active** = X-Ray coleta traces de todas as invocações (respeitando as regras de sampling). **PassThrough** = X-Ray só registra traces se a invocação pai já estiver instrumentada.

---
## Parte 4 — Gerar Traces

> No PowerShell com AWS CLI v2, o parâmetro `--payload` com JSON inline requer a flag `--cli-binary-format raw-in-base64-out`. Adicione-a após `--payload '...'` em cada comando abaixo, ou salve o payload em um arquivo e use `--payload file://payload.json`.

Invocar com diferentes orderId para gerar histórico de traces:

```
aws lambda invoke --function-name lab-xray-demo --payload '{"orderId": "ORD-001"}' response.json
aws lambda invoke --function-name lab-xray-demo --payload '{"orderId": "ORD-002"}' response.json
aws lambda invoke --function-name lab-xray-demo --payload '{"orderId": "ORD-003"}' response.json
aws lambda invoke --function-name lab-xray-demo --payload '{"orderId": "ORD-004"}' response.json
aws lambda invoke --function-name lab-xray-demo --payload '{"orderId": "ORD-005"}' response.json
```

Simular um trace com erro:

```
aws lambda invoke --function-name lab-xray-demo --payload '{"orderId": "ERR-001", "forceError": true}' response.json
```

> Aguarde ~30 segundos para os traces aparecerem no console X-Ray.

---
## Parte 5 — Analisar no Console X-Ray

### Service Map

1. Acesse **X-Ray → Service Map**.
2. Identifique os nós: **Client → Lambda (lab-xray-demo) → DynamoDB (LabOrders)**.
3. Clique no nó Lambda: observe latência média, taxa de erro (o ERR-001 deve aparecer em vermelho), taxa de throttle.
4. Clique no nó DynamoDB: observe a latência da operação `PutItem` rastreada automaticamente pelo `patch_all()`.

### Traces

1. Acesse **X-Ray → Traces**.
2. No campo de filtro exibido no topo da lista de traces, digite a expressão abaixo e pressione Enter:
   `annotation.orderId = "ORD-003"`
3. Abra o trace e observe a hierarquia de segmentos:
   - Segmento Lambda (duração total)
   - Subsegmento `validacao-pedido` (~20 ms)
   - Subsegmento `persistir-pedido`
   - Subsegmento DynamoDB `PutItem` (rastreado automaticamente)
4. Clique em **Annotations** — veja `orderId` e `environment` (indexadas, pesquisáveis).
5. Clique em **Metadata** — veja `event_payload` e `function_version` (não indexadas, apenas para debug).
6. Abra o trace do `ERR-001` — observe o segmento marcado como **Fault** e a anotação `error=true`.

### Diferença entre Annotation e Metadata

| | Annotation | Metadata |
|---|---|---|
| Indexada para busca | ✅ Sim | ❌ Não |
| Visível no detalhe do trace | ✅ Sim | ✅ Sim |
| Tipo de dado | String, Number, Boolean | Qualquer objeto |
| Uso | Filtros de trace (`annotation.key = "valor"`) | Contexto de debug |

---
## Parte 6 — Regra de Sampling Customizada (Bônus)

A regra de sampling padrão registra 5% das requisições após o primeiro request por segundo (reservoir size=1, rate=0.05). Para o lab, onde o volume é baixo, isto pode já amostrar 100% — mas o conceito é importante para produção.

Criar regra customizada que registra 100% das invocações da função deste lab:

**PowerShell:**
```powershell
$samplingRule = '{"RuleName":"lab-xray-full","Priority":1,"ReservoirSize":10,"FixedRate":1.0,"URLPath":"*","Host":"*","HTTPMethod":"*","ServiceName":"lab-xray-demo","ServiceType":"AWS::Lambda::Function","ResourceARN":"*","Version":1}'
aws xray create-sampling-rule --sampling-rule $samplingRule
```

**Bash:**
```bash
SAMPLING_RULE='{"RuleName":"lab-xray-full","Priority":1,"ReservoirSize":10,"FixedRate":1.0,"URLPath":"*","Host":"*","HTTPMethod":"*","ServiceName":"lab-xray-demo","ServiceType":"AWS::Lambda::Function","ResourceARN":"*","Version":1}'
aws xray create-sampling-rule --sampling-rule "$SAMPLING_RULE"
```

Verificar as regras ativas:

```
aws xray get-sampling-rules --query "SamplingRuleRecords[*].SamplingRule.{Nome:RuleName,Prioridade:Priority,Taxa:FixedRate}"
```

> Regras com menor número de prioridade têm precedência. A regra `Default` tem prioridade 10000.

---
## Pontos de Verificação

- [ ] Tabela `LabOrders` criada com status `ACTIVE`
- [ ] Lambda `lab-xray-demo` criada com Active Tracing habilitado
- [ ] Pelo menos 5 invocações normais e 1 com `forceError=true` realizadas
- [ ] Service Map exibe os nós: Lambda → DynamoDB, com latência e taxa de erro
- [ ] Trace do `ORD-003` localizado via filtro de annotation `annotation.orderId = "ORD-003"`
- [ ] Hierarquia de subsegmentos visível: `validacao-pedido` → `persistir-pedido` → DynamoDB PutItem
- [ ] Diferença entre Annotations (indexadas) e Metadata (não indexada) observada no console
- [ ] (Bônus) Regra de sampling `lab-xray-full` criada e listada

---
## Conceitos Reforçados

- `patch_all()` deve ser chamado **antes** de qualquer importação de cliente AWS — instrumenta automaticamente boto3, requests, httplib
- **Segment** é criado pelo SDK do Lambda automaticamente por invocação; **Subsegment** é criado pelo código (`in_subsegment()`)
- **Annotations** são indexadas e pesquisáveis — use para IDs de negócio, ambiente, versão; são cobradas no custo de armazenamento de traces
- **Metadata** não é indexada — use para payloads e contexto de debug; não aparece nos filtros de busca
- **Active Tracing** no Lambda bypassa o daemon local — o próprio runtime do Lambda envia os segments ao X-Ray
- **Sampling rules** controlam qual fração das requisições gera trace — evitam custo excessivo em produção
- O Service Map é gerado a partir dos traces — não requer configuração extra; apenas traces chegando ao X-Ray

---
## Cleanup

Deletar regra de sampling:

```
aws xray delete-sampling-rule --rule-name lab-xray-full
```

Desabilitar Active Tracing:

```
aws lambda update-function-configuration --function-name lab-xray-demo --tracing-config Mode=PassThrough
```

Deletar função Lambda:

```
aws lambda delete-function --function-name lab-xray-demo
```

Deletar log group:

```
aws logs delete-log-group --log-group-name /aws/lambda/lab-xray-demo
```

Deletar tabela DynamoDB:

```
aws dynamodb delete-table --table-name LabOrders
```

Deletar role IAM:

```
aws iam detach-role-policy --role-name lab-xray-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam detach-role-policy --role-name lab-xray-role --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

aws iam detach-role-policy --role-name lab-xray-role --policy-arn arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess

aws iam delete-role --role-name lab-xray-role
```

Remover arquivos locais:

**PowerShell:**
```powershell
Remove-Item -Recurse -Force package, lab_xray.zip, response.json -ErrorAction SilentlyContinue
```

**Bash:**
```bash
rm -rf package lab_xray.zip response.json
```
