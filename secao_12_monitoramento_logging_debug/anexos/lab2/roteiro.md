# Lab — Métricas Customizadas com PutMetricData e EMF

> **Compatibilidade de comandos CLI**
> Este roteiro apresenta blocos para **PowerShell** (Windows) e **Bash** (Linux/macOS/Git Bash/WSL).
> Comandos de empacotar/copiar arquivos diferem entre os terminais — ambas as versões estão documentadas.
> No Linux/macOS substitua `python` por `python3` onde necessário. CMD não é suportado.

> **Aviso de custos:** CloudWatch oferece Free Tier de 10 métricas customizadas por mês (permanente). Este lab publica poucas métricas e fica dentro do Free Tier na maioria dos casos. Lambda tem 1 milhão de invocações gratuitas por mês. **Desprovisione ao finalizar.**

---
## Objetivo

Comparar as duas formas de publicar métricas customizadas no CloudWatch: `PutMetricData` via SDK (chamada de API direta) e Embedded Metrics Format (EMF), que publica métricas embutidas em logs estruturados sem nenhuma chamada extra de API.

---
## Pré-requisitos

- AWS CLI configurada com credenciais válidas
- Python 3.x com `boto3` e `aws-embedded-metrics`:

  ```shell
  pip install boto3 aws-embedded-metrics
  ```

- Permissões IAM: `cloudwatch:PutMetricData`, `lambda:CreateFunction`, `lambda:UpdateFunctionCode`, `lambda:InvokeFunction`, `iam:CreateRole`, `iam:AttachRolePolicy`, `logs:DescribeLogGroups`

---
## Parte 1 — PutMetricData via Python (SDK)

O arquivo `put_metric.py` publica 10 pontos em Standard Resolution (`StorageResolution=60`) e 5 pontos em High-Resolution (`StorageResolution=1`). Antes de executar, abra o arquivo e ajuste a variável `REGION` no topo para a região que você está usando.

```
python put_metric.py
```

> No Linux/macOS use `python3 put_metric.py` se necessário.

Após a execução, acesse **CloudWatch → Metrics → Custom namespaces → MeuCurso/Pedidos**:

1. Selecione `PedidosPorMinuto` (Standard) — granularidade mínima de 1 minuto no gráfico.
2. Selecione `PedidosPorMinutoHR` (High-Res) — granularidade de até 1 segundo.
3. Altere a estatística para `Sum`, `Average` e `Maximum` e observe a diferença.
4. Use as dimensões `Ambiente=Producao` e `Regiao=Sul` para filtrar.

> **PutMetricData** gera uma chamada de API por invocação — em alto volume isso tem custo e impacto na performance do código chamador.

---
## Parte 2 — Criar a Role IAM para a Lambda

**PowerShell:**
```powershell
$trustPolicy = '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
aws iam create-role --role-name lab-emf-role --assume-role-policy-document $trustPolicy
```

**Bash:**
```bash
TRUST_POLICY='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
aws iam create-role --role-name lab-emf-role --assume-role-policy-document "$TRUST_POLICY"
```

```
aws iam attach-role-policy --role-name lab-emf-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy --role-name lab-emf-role --policy-arn arn:aws:iam::aws:policy/CloudWatchFullAccess
```

> Funciona em Bash e PowerShell.

Anote o ARN da role retornado (`arn:aws:iam::<ACCOUNT_ID>:role/lab-emf-role`).

> Aguarde ~10 segundos para a role propagar antes de criar a função.

---
## Parte 3 — Empacotar e Fazer Deploy da Lambda EMF

Antes de criar a função, obtenha o Account ID e a região configurados:

```
aws sts get-caller-identity --query Account --output text
aws configure get region
```

Substitua `<ACCOUNT_ID>` e `<REGION>` nos comandos desta parte pelos valores retornados acima.

Instale a dependência `aws-embedded-metrics` no diretório do pacote:

```
pip install aws-embedded-metrics -t ./package
```

Copie o código da função para o pacote. No terminal, a partir do diretório do lab:

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
Compress-Archive -Path .\package\* -DestinationPath lab_emf.zip -Force
```

**Bash:**
```bash
cd package && zip -r ../lab_emf.zip . && cd ..
```

Criar a função Lambda (substitua `<ACCOUNT_ID>` e `<REGION>`):

```
aws lambda create-function --function-name lab-emf-demo --runtime python3.12 --role arn:aws:iam::<ACCOUNT_ID>:role/lab-emf-role --handler lambda_function.lambda_handler --zip-file fileb://lab_emf.zip --timeout 30
```

Habilitar Active Tracing (opcional, para integrar com X-Ray no lab seguinte):

```
aws lambda update-function-configuration --function-name lab-emf-demo --tracing-config Mode=Active
```

---
## Parte 4 — Invocar a Lambda e Observar as Métricas EMF

> No PowerShell com AWS CLI v2, o parâmetro `--payload` com JSON inline requer a flag `--cli-binary-format raw-in-base64-out`. Adicione-a após `--payload '...'` em cada comando abaixo, ou salve o payload em um arquivo e use `--payload file://payload.json`.

Invocar individualmente com diferentes orderId:

```
aws lambda invoke --function-name lab-emf-demo --payload '{"orderId": "ORD-001"}' response.json
aws lambda invoke --function-name lab-emf-demo --payload '{"orderId": "ORD-002"}' response.json
aws lambda invoke --function-name lab-emf-demo --payload '{"orderId": "ORD-003"}' response.json
aws lambda invoke --function-name lab-emf-demo --payload '{"orderId": "ORD-004"}' response.json
aws lambda invoke --function-name lab-emf-demo --payload '{"orderId": "ORD-005"}' response.json
```

Simular um erro:

```
aws lambda invoke --function-name lab-emf-demo --payload '{"orderId": "ERR-001", "forceError": true}' response.json
```

Aguarde ~30 segundos e acesse os logs:

```
aws logs tail /aws/lambda/lab-emf-demo --since 5m
```

Nos logs, observe o JSON estruturado com o campo `_aws` — esse é o payload EMF que o agente CloudWatch interpreta para criar as métricas.

**No console:**
1. **CloudWatch → Logs → `/aws/lambda/lab-emf-demo`** → abra um log event e identifique o JSON EMF com `_aws.CloudWatchMetrics`.
2. **CloudWatch → Metrics → Custom namespaces → MeuCurso/Pedidos** → veja `Latencia` e `PedidosProcessados` — criadas pelo EMF sem uma única chamada `PutMetricData`.
3. Compare: `Latencia` criada pelo EMF vs `PedidosPorMinuto` criada pelo `put_metric.py` — mesmo destino, abordagens completamente diferentes.

---
## Parte 5 — Criar Dashboard Comparativo

1. Acesse **CloudWatch → Dashboards → Create dashboard** → nome: `Lab-EMF-Dashboard`.
2. Adicione:
   - **Line** → `MeuCurso/Pedidos / PedidosPorMinuto` (`put_metric.py`)
   - **Number** → `MeuCurso/Pedidos / Latencia` (EMF) com estatística p99
3. Salve e observe os dois widgets lado a lado.

---
## Pontos de Verificação

- [ ] `put_metric.py` executado — `PedidosPorMinuto` e `PedidosPorMinutoHR` visíveis no console
- [ ] Diferença de granularidade entre Standard (60s) e High-Resolution (1s) observada
- [ ] Lambda `lab-emf-demo` criada e invocada pelo menos 5 vezes
- [ ] JSON com campo `_aws` identificado nos logs da Lambda
- [ ] Métricas `Latencia` e `PedidosProcessados` aparecendo no namespace `MeuCurso/Pedidos` sem chamada explícita a PutMetricData
- [ ] Métrica `Erros` aparecendo após a invocação com `forceError=true`

---
## Conceitos Reforçados

- **PutMetricData** gera uma chamada de API por publicação — adequado para scripts e serviços fora do Lambda
- **EMF** embute a métrica no log: zero chamada de API extra, sem impacto na latência da função, sem custo adicional de API
- O payload EMF é um JSON com `_aws.CloudWatchMetrics` — o agente de log Lambda o detecta automaticamente
- `set_property()` adiciona campos ao log mas **não** cria métricas — adequado para contexto de debug
- `set_dimensions()` define as dimensões das métricas EMF — afeta a cardinalidade e o custo
- High-Resolution (`StorageResolution=1`) custa 5x mais que Standard (`StorageResolution=60`) por ponto
- Métricas EMF aparecem no CloudWatch com ~1 minuto de delay (mesmo delay do PutMetricData)

---
## Cleanup

Remover função Lambda:

```
aws lambda delete-function --function-name lab-emf-demo
```

Remover log group:

```
aws logs delete-log-group --log-group-name /aws/lambda/lab-emf-demo
```

Remover role IAM:

```
aws iam detach-role-policy --role-name lab-emf-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam detach-role-policy --role-name lab-emf-role --policy-arn arn:aws:iam::aws:policy/CloudWatchFullAccess

aws iam delete-role --role-name lab-emf-role
```

Remover arquivos locais gerados:

**PowerShell:**
```powershell
Remove-Item -Recurse -Force package, lab_emf.zip, response.json -ErrorAction SilentlyContinue
```

**Bash:**
```bash
rm -rf package lab_emf.zip response.json
```
