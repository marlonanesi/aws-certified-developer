# Lab 3 – Protegendo API Gateway com Cognito Authorizer

> **Compatibilidade de comandos CLI**
> Este roteiro apresenta blocos para **PowerShell** (Windows) e **Bash** (Linux/macOS/Git Bash/WSL).
> No PowerShell 5.1, usa-se `curl.exe` (binário real) para evitar o alias `Invoke-WebRequest`.
> No Bash, use `curl` normalmente. CMD não é suportado.

---
> **Custos e Free Tier**
> - **Amazon Cognito User Pools:** 50.000 MAUs gratuitos/mês (permanente)
> - **AWS Lambda:** 1 milhão de invocações gratuitas/mês (permanente)
> - **API Gateway REST:** 1 milhão de chamadas gratuitas/mês nos **primeiros 12 meses**
>
> Para volumes de teste deste lab, o custo tende a ser zero ou mínimo.
>
> ⚠️ **Aviso importante:** qualquer recurso provisionado na AWS pode gerar custos, mesmo dentro do free tier, que possui limites mensais. Ao concluir o lab, execute a etapa de limpeza para evitar cobranças inesperadas.

---
## Objetivo

Criar uma API REST no API Gateway protegida por Cognito User Pool Authorizer. Requisições sem token JWT válido são rejeitadas com `401 Unauthorized`. Requisições autenticadas chegam ao backend Lambda, que acessa os claims do token.

---
## Pré-requisitos

- Lab 2 concluído (User Pool configurado e usuário criado)
- AWS CLI configurado com permissões em Lambda, API Gateway e IAM
- `curl` ou Postman instalado

---
## Parte 1 – Criar a Função Lambda Backend

1. Console AWS → **Lambda → Create function** ("Criar função")
2. Function name: `lab3-backend`
3. Runtime: Python 3.12
4. Cole o código do arquivo `lambda_backend.py` incluído nesta pasta
5. Deploy

---
## Parte 2 – Criar a API REST

1. **API Gateway → Create API** ("Criar API") **→ REST API → Build** ("Compilar")
2. API name: `lab3-cognito-api`
3. **Actions → Create Resource** ("Criar recurso"): path `/items`
4. Com `/items` selecionado → **Actions → Create Method** ("Criar método") **→ GET**
   - Integration type: Lambda Function
   - Lambda Function: `lab3-backend`
   - ✅ Use Lambda Proxy Integration
5. **Actions → Deploy API**
   - Stage: `prod`
6. Anote a **Invoke URL**: `https://<API_ID>.execute-api.<REGION>.amazonaws.com/prod`

---
## Parte 3 – Configurar o Cognito Authorizer

1. No painel da API → **Authorizers → Create New Authorizer** ("Criar novo autorizador")
2. Name: `lab3-cognito-auth`
3. Type: **Cognito**
4. Cognito User Pool: selecionar o pool criado no Lab 2
5. Token Source: `Authorization`
6. **Create**

---
## Parte 4 – Aplicar o Authorizer no Método GET

1. **Resources → /items → GET → Method Request**
2. Authorization: selecionar `lab3-cognito-auth`
3. Salvar
4. **Actions → Deploy API** ("Implantar API") (reimplantar em `prod` para aplicar a mudança)

---
## Parte 5 – Testar com e sem Token

**PowerShell (Windows):**
```powershell
$API_URL = "https://<API_ID>.execute-api.<REGION>.amazonaws.com/prod"
$USER_POOL_ID = "<USER_POOL_ID>"
$APP_CLIENT_ID = "<APP_CLIENT_ID>"

# Testar SEM token — deve retornar 401
curl.exe -X GET "$API_URL/items"

# Obter token via CLI
$TOKEN = aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH --auth-parameters USERNAME=testuser@exemplo.com,PASSWORD=LabPass@2024 --client-id $APP_CLIENT_ID --query 'AuthenticationResult.IdToken' --output text

# Testar COM token — deve retornar 200
curl.exe -X GET "$API_URL/items" -H "Authorization: Bearer $TOKEN"

# Testar com token inválido — deve retornar 401
curl.exe -X GET "$API_URL/items" -H "Authorization: Bearer token_invalido"
```

**Bash (Linux/macOS/Git Bash/WSL):**
```bash
API_URL="https://<API_ID>.execute-api.<REGION>.amazonaws.com/prod"
USER_POOL_ID="<USER_POOL_ID>"
APP_CLIENT_ID="<APP_CLIENT_ID>"

# Testar SEM token — deve retornar 401
curl -X GET "$API_URL/items"

# Obter token via CLI
TOKEN=$(aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH --auth-parameters USERNAME=testuser@exemplo.com,PASSWORD=LabPass@2024 --client-id $APP_CLIENT_ID --query 'AuthenticationResult.IdToken' --output text)

# Testar COM token — deve retornar 200
curl -X GET "$API_URL/items" -H "Authorization: Bearer $TOKEN"

# Testar com token inválido — deve retornar 401
curl -X GET "$API_URL/items" -H "Authorization: Bearer token_invalido"
```

---
## Parte 6 – Verificar os Claims na Lambda

A resposta de sucesso exibe o `email` e o `sub` extraídos diretamente do token pelo API Gateway. O backend Lambda **não** valida o token — essa responsabilidade é do Authorizer.

Observe que:
- Quando o token é inválido → o API Gateway rejeita a requisição **antes** de invocar a Lambda
- Isso significa **zero custo de invocação Lambda** nas requisições não autorizadas

---
## Pontos de Verificação

- Status `401` com body `{"message":"Unauthorized"}` para requisições sem/com token inválido
- Status `200` com os claims `email` e `sub` visíveis na resposta para requisições autenticadas
- O `iss` no token deve corresponder ao User Pool; tokens de outro pool são rejeitados automaticamente

---
## Limpeza

```
# Deletar a API
aws apigateway delete-rest-api --rest-api-id <API_ID>

# Deletar a Lambda
aws lambda delete-function --function-name lab3-backend

# Deletar o User Pool (se não for usado em outros labs)
aws cognito-idp delete-user-pool --user-pool-id <USER_POOL_ID>
```

> Todos os comandos acima funcionam em Bash e PowerShell. Use `$USER_POOL_ID` (PS) ou `$USER_POOL_ID` (Bash) se a variável ainda estiver definida na sessão.
