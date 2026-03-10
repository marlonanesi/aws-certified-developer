# Lab 2 – Múltiplos Stages e Stage Variables

> **Aviso de compatibilidade de comandos**
> Os comandos deste roteiro sao referencias e podem precisar de adaptacao
> conforme o SO e terminal utilizados (PowerShell, Bash, Zsh, CMD, etc.).
> Converta a sintaxe antes de executar se necessario.
>
> Sugestao de prompt para IA generativa:
> "Converta o comando abaixo para meu SO [Windows/macOS/Linux] e terminal
> [PowerShell/Bash/Zsh/CMD]. Adapte variaveis, redirecionamentos e pipes
> para o equivalente nesse ambiente: <cole o comando aqui>"

---
> **Custos e Free Tier**
> - **Amazon API Gateway REST API:** 1 milhão de chamadas gratuitas/mês nos **primeiros 12 meses**
> - **AWS Lambda:** 1 milhão de invocações gratuitas/mês (nível permanente)
>
> ⚠️ **Aviso importante:** qualquer recurso provisionado na AWS pode gerar custos mesmo dentro do free tier, que possui limites mensais. Ao concluir o lab, execute a etapa de limpeza para evitar cobranças inesperadas.

---
## Objetivo

Usar **Stage Variables** para apontar diferentes stages (`dev` e `prod`) para aliases distintos da mesma função Lambda, sem alterar o código ou a estrutura da API.

---
## Arquitetura

```
Mesmo API Gateway
    ├── Stage: dev  (Stage Variable: lambdaAlias = dev)  → Lambda alias :dev ($LATEST)
    └── Stage: prod (Stage Variable: lambdaAlias = prod) → Lambda alias :prod (versão 1)
```

---
## Pré-requisitos

- Lab 1 concluído (API `lab1-hello-api` e função `api-lab1-hello` existentes)
- AWS CLI configurada com permissões em Lambda e API Gateway

---
## Parte 1 – Atualizar o Código da Lambda

Substitua o código da função `api-lab1-hello` pelo conteúdo do arquivo `lambda_stages.py` incluído nesta pasta e clique em **Deploy** ("Implantar").

O novo código lê a Stage Variable `lambdaAlias` do evento para exibir o ambiente ativo na resposta.

---
## Parte 2 – Criar Aliases na Lambda

### Alias `dev` → $LATEST

```
aws lambda create-alias --function-name api-lab1-hello --name dev --function-version '$LATEST' --description "Desenvolvimento - sempre o codigo mais recente"
```

### Publicar versão 1 e criar alias `prod`

```
# Publicar versão imutável
aws lambda publish-version --function-name api-lab1-hello --description "Versao estavel para producao"

# Criar alias prod apontando para v1
aws lambda create-alias --function-name api-lab1-hello --name prod --function-version 1 --description "Producao - versao estavel"
```

---
## Parte 3 – Reconfigurar a Integração com Stage Variable

1. No API Gateway → método **GET** em `/hello` → **Integration Request**
2. Em **Lambda Function**, substitua o nome fixo pelo ARN com Stage Variable:

```
arn:aws:lambda:<REGION>:<ACCOUNT_ID>:function:api-lab1-hello:${stageVariables.lambdaAlias}
```

> Substitua `<REGION>` pela sua região (ex: `us-east-1`) e `<ACCOUNT_ID>` pelo ID da sua conta AWS (12 dígitos, visível em: `aws sts get-caller-identity --query Account --output text`).

3. **Save**

---
## Parte 4 – Adicionar Permissões de Invocação para Cada Alias

Ao usar Stage Variables no ARN da Lambda, o API Gateway precisa de permissão explícita para cada alias:

```
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$REGION = aws configure get region
$API_ID = "<SEU_API_ID>"  # visível na URL do stage ou no console (ex: abc1234xyz)

# Permissão para o stage dev invocar o alias dev
aws lambda add-permission --function-name "api-lab1-hello:dev" --statement-id "AllowAPIGatewayDev" --action lambda:InvokeFunction --principal apigateway.amazonaws.com --source-arn "arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/dev/GET/hello"

# Permissão para o stage prod invocar o alias prod
aws lambda add-permission --function-name "api-lab1-hello:prod" --statement-id "AllowAPIGatewayProd" --action lambda:InvokeFunction --principal apigateway.amazonaws.com --source-arn "arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/prod/GET/hello"
```

---
## Parte 5 – Configurar Stage Variables em Cada Stage

### Stage `dev`

1. **Stages → dev → Stage Variables → Add Stage Variable**
   - Name: `lambdaAlias` | Value: `dev`
2. Salvar

### Stage `prod` (criar novo stage)

1. **Actions → Deploy API → [New Stage]** → Stage name: `prod` → **Deploy**
2. **Stages → prod → Stage Variables → Add Stage Variable**
   - Name: `lambdaAlias` | Value: `prod`
3. Salvar

---
## Parte 6 – Testar e Validar

```
$DEV_URL = "https://<API_ID>.execute-api.<REGION>.amazonaws.com/dev"
$PROD_URL = "https://<API_ID>.execute-api.<REGION>.amazonaws.com/prod"

# Stage dev — deve mostrar stageAlias: dev, functionVersion: $LATEST
curl "$DEV_URL/hello?name=Estudante"

# Stage prod — deve mostrar stageAlias: prod, functionVersion: 1
curl "$PROD_URL/hello?name=Estudante"
```

---
## Parte 7 – Configurações Independentes por Stage

### Throttling diferenciado

**Stage dev:** **Stages → dev → Stage Settings → Edit**
- Rate: 10 req/s | Burst: 5

**Stage prod:** **Stages → prod → Stage Settings → Edit**
- Rate: 1000 req/s | Burst: 500

### Logs diferenciados

Em cada stage → **Logs/Tracing**:
- `dev`: nível INFO + full request/response (útil para debug)
- `prod`: nível ERROR apenas (performance e custo)

> Mudanças de configuração de stage não exigem novo deploy da API.

---
## Pontos de Verificação

- O campo `stageAlias` na resposta muda corretamente entre `dev` e `prod`
- Com `functionVersion: $LATEST` no dev e `functionVersion: 1` no prod — os aliases estão corretos
- Alterar o código e fazer deploy **sem publicar nova versão** afeta o alias `dev` mas **não afeta prod**
- Qualquer alteração na configuração da API (integração, método, recurso) exige novo **Deploy API** para ter efeito

---
## Limpeza

```
# Remover aliases da Lambda
aws lambda delete-alias --function-name api-lab1-hello --name dev
aws lambda delete-alias --function-name api-lab1-hello --name prod

# Remover stage prod da API (ou deletar a API inteira)
aws apigateway delete-stage --rest-api-id <API_ID> --stage-name prod
```
