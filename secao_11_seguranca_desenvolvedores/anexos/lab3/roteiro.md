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

- AWS CLI configurado com permissões em Lambda, API Gateway e IAM
- `curl` ou Postman instalado
- **User Pool do Lab 2 ativo** com o usuário `testuser@exemplo.com` e o App Client `lab2-cli-client` (sem secret) criados

> Se a limpeza do Lab 2 foi executada e o User Pool foi deletado, recrie-o seguindo a Parte 1 do Lab 2 completa (incluindo a criação do `lab2-cli-client` via CLI). Não é necessário repetir as Partes 2 a 6 do Lab 2.

---
## Parte 1 – Criar a Função Lambda Backend

1. Console AWS → **Lambda → Create function** ("Criar função")
2. Function name: `lab3-backend`
3. Runtime: Python 3.12
4. No editor de código inline (Code source → Edit code inline), substitua o conteúdo pelo do arquivo `lambda_backend.py` desta pasta; clique em **Deploy**

---
## Parte 2 – Criar a API REST

1. **API Gateway → Create API** ("Criar API") **→ REST API → Build** ("Compilar")
2. API name: `lab3-cognito-api`
3. **Actions → Create Resource** ("Criar recurso"): path `/items`
4. Com `/items` selecionado → **Actions → Create Method** ("Criar método") **→ GET**
   - Integration type: Lambda Function
   - Lambda Function: `lab3-backend`
   - ✅ Use Lambda Proxy Integration
5. **Actions → Deploy API / Implantar API**
   - Stage: `prod` / Novo Estágio
6. Anote a **Invoke URL**: `https://<API_URL>.execute-api.<REGION>.amazonaws.com/prod`

---
## Parte 3 – Configurar o Cognito Authorizer

1. No painel da API → **Autorizadores** → **Criar autorizador**
2. **"Nome do autorizador"**: `lab3-cognito-auth`
3. **"Tipo de autorizador"**: selecionar **Cognito**
4. **"Grupo de usuários do Cognito"**: selecionar a região `sa-east-1` e o pool criado no Lab 2
5. **"Origem do token"**: digitar `Authorization` — é o nome do header HTTP que conterá o token JWT
6. **"Validação de token"**: deixar em branco
7. Clique em **"Criar autorizador"**

---
## Parte 4 – Aplicar o Authorizer no Método GET

1. No menu lateral, clique em **"Recursos"**
2. Na árvore de recursos, selecione **GET** abaixo de `/items`
3. No painel à direita, clique em **"Solicitação de método"** ("Method Request")
4. Clique em **"Editar"**
5. No campo **"Autorizador"**, selecione `lab3-cognito-auth`
6. Clique em **"Salvar"**
7. No menu lateral, clique em **"Recursos"** → botão **"Implantar API"** → estágio `prod` → **"Implantar"**

---
## Parte 5 – Testar com e sem Token

Defina as variáveis antes de executar os testes. Substitua pelos valores reais:

**PowerShell:**
```powershell
$API_URL = "https://<API_URL>.execute-api.<REGION>.amazonaws.com/prod"
$USER_POOL_ID = "<USER_POOL_ID>"
$APP_CLIENT_ID = "<APP_CLIENT_ID_DO_lab2-cli-client>"  # App Client sem secret criado no Lab 2
```

**Bash:**
```bash
API_URL="https://<API_URL>.execute-api.<REGION>.amazonaws.com/prod"
USER_POOL_ID="<USER_POOL_ID>"
APP_CLIENT_ID="<APP_CLIENT_ID_DO_lab2-cli-client>"  # App Client sem secret criado no Lab 2
```

Em seguida, execute os testes:

**PowerShell (Windows):**
```powershell
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

**PowerShell:**
```powershell
# Deletar a API
aws apigateway delete-rest-api --rest-api-id <API_URL>

# Deletar a Lambda
aws lambda delete-function --function-name lab3-backend

# Deletar o User Pool (se não for usado em outros labs)
# 1. Desativar proteção contra exclusão
aws cognito-idp update-user-pool --user-pool-id $USER_POOL_ID --deletion-protection INACTIVE

# 2. Obter e deletar o domínio
$DOMAIN = aws cognito-idp describe-user-pool --user-pool-id $USER_POOL_ID --query 'UserPool.Domain' --output text
aws cognito-idp delete-user-pool-domain --domain $DOMAIN --user-pool-id $USER_POOL_ID

# 3. Deletar o User Pool
aws cognito-idp delete-user-pool --user-pool-id $USER_POOL_ID
```

**Bash:**
```bash
# Deletar a API
aws apigateway delete-rest-api --rest-api-id <API_URL>

# Deletar a Lambda
aws lambda delete-function --function-name lab3-backend

# Deletar o User Pool (se não for usado em outros labs)
# 1. Desativar proteção contra exclusão
aws cognito-idp update-user-pool --user-pool-id $USER_POOL_ID --deletion-protection INACTIVE

# 2. Obter e deletar o domínio
DOMAIN=$(aws cognito-idp describe-user-pool --user-pool-id $USER_POOL_ID --query 'UserPool.Domain' --output text)
aws cognito-idp delete-user-pool-domain --domain $DOMAIN --user-pool-id $USER_POOL_ID

# 3. Deletar o User Pool
aws cognito-idp delete-user-pool --user-pool-id $USER_POOL_ID
```
