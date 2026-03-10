# Lab 4 – Versões, Aliases e Canary Deployment

> **Compatibilidade de comandos CLI**
> Os comandos avulsos deste roteiro funcionam diretamente em **PowerShell** (Windows) e **Bash** (Linux/macOS/Git Bash) — basta colar e executar.
> Onde há diferença de sintaxe entre os dois shells, o roteiro apresenta as duas versões lado a lado.
> Para CMD ou outros terminais, converta a sintaxe com ajuda de IA generativa.

---
> **Custos e Free Tier**
> O AWS Lambda oferece **1 milhão de invocações gratuitas por mês** e **400.000 GB-segundos** (nível permanente). Versões e aliases não têm custo adicional.
>
> ⚠️ **Aviso importante:** qualquer recurso provisionado na AWS pode gerar custos mesmo dentro do free tier, que possui limites mensais. Ao concluir o lab, execute a etapa de limpeza para evitar cobranças inesperadas.

---
## Objetivo

Publicar versões imutáveis de uma função Lambda, criar aliases que apontam para versões específicas (`DEV` → `$LATEST`, `PROD` → v1) e realizar um canary deployment com tráfego dividido 90/10 entre v1 e v2.

---
## Pré-requisitos

- AWS CLI configurada com permissões em Lambda e IAM
- Uma IAM Role com a policy `AWSLambdaBasicExecutionRole` — anote o ARN

---
## Parte 1 – Criar a Função (Versão 1)

# Se ainda não apagou do lab3 pode usar é a mesma
# Criar a role com trust policy para Lambda - parte 1 
aws iam create-role --role-name lambda-exec-role --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

# Anexar a policy básica de execução - parte 2
aws iam attach-role-policy --role-name lambda-exec-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

$ROLE_ARN = "arn:aws:iam::<ACCOUNT_ID>:role/lambda-exec-role"

```
# Empacotar o código da versão 1
Compress-Archive -Path lambda_v1.py -DestinationPath lambda_versoes.zip -Force

aws lambda create-function --function-name gerenciamento-versoes --runtime python3.12 --handler lambda_v1.lambda_handler --zip-file fileb://lambda_versoes.zip --role $ROLE_ARN

aws lambda update-function-configuration --function-name gerenciamento-versoes --environment Variables='{APP_VERSAO=1.0.0,NOVA_FEATURE=false}'

aws lambda wait function-updated --function-name gerenciamento-versoes
```

---
## Parte 2 – Publicar Versões

### Publicar Versão 1

```
aws lambda publish-version --function-name gerenciamento-versoes --description "Versao 1 - Release inicial"
# Anote: "Version": "1"
```

### Atualizar para o código da Versão 2

```
# Empacotar o código v2 (arquivo lambda_v2.py desta pasta)
Copy-Item lambda_v2.py lambda_versoes_v2.py
Compress-Archive -Path lambda_v2.py -DestinationPath lambda_versoes.zip -Force

aws lambda update-function-code --function-name gerenciamento-versoes --zip-file fileb://lambda_versoes.zip

aws lambda update-function-configuration --function-name gerenciamento-versoes --handler lambda_v2.lambda_handler --environment Variables='{APP_VERSAO=2.0.0,NOVA_FEATURE=true}'

aws lambda wait function-updated --function-name gerenciamento-versoes

aws lambda publish-version --function-name gerenciamento-versoes --description "Versao 2 - Nova feature"
# Anote: "Version": "2"
```

### Verificar versões criadas

```
aws lambda list-versions-by-function --function-name gerenciamento-versoes --query 'Versions[*].[Version, Description]' --output table
```

---
## Parte 3 – Criar Aliases

```
# DEV aponta para $LATEST (sempre o código mais recente)
aws lambda create-alias --function-name gerenciamento-versoes --name DEV --function-version '$LATEST' --description "Ambiente de desenvolvimento"

# PROD aponta para v1 (estável e imutável)
aws lambda create-alias --function-name gerenciamento-versoes --name PROD --function-version 1 --description "Ambiente de producao - v1"
```

### Testar os aliases

```
# Invocar via DEV — deve retornar mensagem da v2 ($LATEST)
aws lambda invoke --function-name gerenciamento-versoes:DEV --payload '{}' --cli-binary-format raw-in-base64-out response_dev.json; Get-Content response_dev.json

# Invocar via PROD — deve retornar mensagem da v1
aws lambda invoke --function-name gerenciamento-versoes:PROD --payload '{}' --cli-binary-format raw-in-base64-out response_prod.json; Get-Content response_prod.json
```

Mesma função, mesmo endpoint, respostas diferentes — esse é o valor dos aliases.

---
## Parte 4 – Canary Deployment (Traffic Shifting 90/10)

```
# Direcionar 10% do tráfego PROD para v2, mantendo 90% na v1
aws lambda update-alias --function-name gerenciamento-versoes --name PROD --function-version 1 --routing-config '{"AdditionalVersionWeights": {"2": 0.1}}'

aws lambda get-alias --function-name gerenciamento-versoes --name PROD
```

### Simular tráfego e observar a distribuição

```
1..20 | ForEach-Object {
  $arquivo = "$env:TEMP\resp_$_.json"
  aws lambda invoke --function-name gerenciamento-versoes:PROD --payload '{}' --cli-binary-format raw-in-base64-out $arquivo | Out-Null
  $resposta = Get-Content $arquivo -Raw | ConvertFrom-Json
  $v = ($resposta.body | ConvertFrom-Json).versao
  Write-Host "Invocacao $_`: versao $v"
}
```

Aproximadamente 18 retornos na v1.0.0 e 2 na v2.0.0.

### Promover v2 para 100% (deploy concluído)

```
aws lambda update-alias --function-name gerenciamento-versoes --name PROD --function-version 2 --routing-config '{"AdditionalVersionWeights": {}}'
```

### Rollback para v1 (se necessário)

```
aws lambda update-alias --function-name gerenciamento-versoes --name PROD --function-version 1 --routing-config '{"AdditionalVersionWeights": {}}'
```

---
## Parte 5 – Inspecionar ARNs

```
# ARN da função ($LATEST — NÃO usar em produção como referência fixa)
aws lambda get-function --function-name gerenciamento-versoes --query 'Configuration.FunctionArn' --output text

# ARN da versão 1 (imutável)
aws lambda get-function --function-name gerenciamento-versoes:1 --query 'Configuration.FunctionArn' --output text

# ARN do alias PROD (estável — não muda mesmo quando atualizado para v2)
aws lambda get-alias --function-name gerenciamento-versoes --name PROD --query 'AliasArn' --output text
```

O ARN do alias **não muda** — os consumidores (API Gateway, EventBridge, etc.) sempre apontam para ele, sem precisar ser atualizados.

---
## Pontos de Verificação

- Versões numeradas são **imutáveis** — tentar editar uma versão no console é bloqueado pela AWS
- `$LATEST` sempre reflete o código após o último `Deploy`, mas **não é uma versão publicada**
- O ARN do alias permanece constante, independente de qual versão ele aponta
- Em produção, o canary deployment é tipicamente combinado com CloudWatch Alarms para rollback automático via CodeDeploy

---
## Limpeza

```
aws lambda delete-alias --function-name gerenciamento-versoes --name PROD
aws lambda delete-alias --function-name gerenciamento-versoes --name DEV
aws lambda delete-function --function-name gerenciamento-versoes
Remove-Item -Force lambda_versoes.zip, response_dev.json, response_prod.json -ErrorAction SilentlyContinue
Remove-Item -Force "$env:TEMP\resp_*.json" -ErrorAction SilentlyContinue
```
