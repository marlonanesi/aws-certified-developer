# Lab 2 – Cognito User Pool: Signup, Login e Tokens JWT

> **Compatibilidade de comandos CLI**
> Este roteiro apresenta blocos para **PowerShell** (Windows) e **Bash** (Linux/macOS/Git Bash/WSL).
> No Linux/macOS substitua `python` por `python3` onde necessário.
> CMD não é suportado.

---
> **Custos e Free Tier**
> O Amazon Cognito oferece **50.000 MAUs (Monthly Active Users) gratuitos por mês** para User Pools (nível permanente, não limitado a 12 meses). Para este lab de aprendizado com poucos usuários de teste, o custo tende a ser zero.
>
> ⚠️ **Aviso importante:** recursos na AWS podem gerar custos mesmo dentro do free tier, que possui limites mensais. Ao concluir o lab, execute a etapa de limpeza para evitar cobranças inesperadas.

---
## Objetivo

Criar um Amazon Cognito User Pool, registrar usuários, realizar autenticação e inspecionar os tokens JWT gerados (ID Token, Access Token, Refresh Token).

---
## Pré-requisitos

- Conta AWS com permissões em Cognito
- AWS CLI configurado
- Python 3 instalado (para inspeção de JWT)

---
## Parte 1 – Criar o User Pool

O console do Cognito usa um assistente de 3 passos ("Configure application resources" / "Configurar recursos da aplicação"). Siga abaixo.

1. Console AWS → **Amazon Cognito → User Pools → Create user pool** ("Criar grupo de usuários")

### Passo 1 de 3 — "Tell us about your application" ("Conte-nos sobre sua inscrição")

**"Define the application" ("Definir a aplicação")**

- **"Application type"** ("Tipo de aplicação"): selecione **"Traditional web application"** ("Aplicação Web tradicional")
- **"Give your application a name"** ("Dê um nome para sua aplicação"): `lab2-app-client`

**"Configure options" ("Configurar opções")**

- **"Login identifier options"** ("Opções para identificadores de login"): marcar **"Email"**
- **"Do you want to configure social, SAML, or OIDC login?"** ("Deseja configurar o login social, SAML ou OIDC?"): deixar sem marcar
- **"Self-registration"** ("Autorregistro"): marcar **"Enable self-registration"** ("Habilitar autorregistro")
- **"Required attributes for sign-up"** ("Atributos obrigatórios para a inscrição"): deixar o dropdown como **"Selecionar atributos"** sem selecionar nada — o `email` já é exigido implicitamente por ser o identificador de login escolhido acima
- **"Add a return URL – optional"** ("Adicionar um URL de retorno – opcional"): `http://localhost:3000/callback`

Clique em **"Next"** ("Próximo").

### Passo 2 de 3 — "Create a Cognito user directory" ("Crie um diretório de usuários do Cognito")

**"User pool name"** ("Nome do grupo de usuários"): `lab2-user-pool`

**"Password policy"** ("Política de senha"): selecione **"Cognito defaults"** ("Padrões do Cognito")

**"Multi-factor authentication"** ("Autenticação multifator"):
- **"MFA enforcement"** ("Aplicação de MFA"): selecione **"Optional MFA"** ("MFA opcional") ou **"No MFA"** — para o lab, selecione **"No MFA"** ("Sem MFA")

**"User account recovery"** ("Recuperação de conta do usuário"):
- **"Self-service account recovery"** ("Recuperação de conta de autoatendimento"): deixar marcado **"Enable self-service account recovery"** ("Habilitar recuperação de conta de autoatendimento")
- **"Recovery message delivery method"** ("Método de entrega de mensagem de recuperação"): manter **"Email only"** ("Somente e-mail")

**"Email"** (entrega de mensagens):
- **"Email provider"** ("Provedor de e-mail"): manter **"Send email with Cognito"** ("Enviar e-mail com o Cognito") — gratuito, limite de 50 e-mails/dia; suficiente para o lab

Clique em **"Next"** ("Próximo").

### Passo 3 de 3 — "Deploy and update your application" ("Implante e atualize sua aplicação")

Revise o resumo. Clique em **"Create user pool"** ("Criar grupo de usuários").

### Após a criação

O Cognito exibe um "Guia de configuração rápida" com exemplos de código. Ignore essa tela — clique em **"Ir para visão geral"** (botão no canto inferior direito) para acessar os detalhes do pool.

Anote o valor abaixo — necessário nas partes seguintes:
- **User Pool ID**: visível diretamente na visão geral, campo **"ID do grupo de usuários"** (ex.: `sa-east-1_AbCdEfGhI`)

> O `lab2-app-client` criado pelo assistente possui **client secret** e não pode ser usado diretamente via CLI. O App Client ID para o lab será gerado automaticamente no próximo passo.

### Criar App Client sem segredo para uso via CLI

O assistente criou o `lab2-app-client` com um **client secret** (tipo "Traditional web application"). Chamadas diretas via AWS CLI não suportam client secret sem calcular um `SECRET_HASH`. Por isso, crie um segundo App Client sem segredo exclusivo para uso no lab.

Primeiro, defina o `USER_POOL_ID` no terminal com o valor anotado na etapa anterior:

**PowerShell:**
```powershell
$USER_POOL_ID = "<USER_POOL_ID>"
```

**Bash:**
```bash
USER_POOL_ID="<USER_POOL_ID>"
```

Em seguida, crie o App Client e capture o ID na variável `APP_CLIENT_ID`:

**PowerShell:**
```powershell
$APP_CLIENT_ID = (aws cognito-idp create-user-pool-client `
    --user-pool-id $USER_POOL_ID `
    --client-name lab2-cli-client `
    --no-generate-secret `
    --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH ALLOW_USER_SRP_AUTH `
    --query 'UserPoolClient.ClientId' --output text)
Write-Output "App Client ID (CLI): $APP_CLIENT_ID"
```

**Bash:**
```bash
APP_CLIENT_ID=$(aws cognito-idp create-user-pool-client \
    --user-pool-id $USER_POOL_ID \
    --client-name lab2-cli-client \
    --no-generate-secret \
    --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH ALLOW_USER_SRP_AUTH \
    --query 'UserPoolClient.ClientId' --output text)
echo "App Client ID (CLI): $APP_CLIENT_ID"
```

A variável `$APP_CLIENT_ID` estará definida para os comandos seguintes.

---
## Parte 2 – Criar Usuário de Teste

> `$USER_POOL_ID` e `$APP_CLIENT_ID` devem estar definidos da etapa anterior. Se iniciou uma nova sessão de terminal, redefina-os:
> - **PowerShell:** `$USER_POOL_ID = "<USER_POOL_ID>"` e `$APP_CLIENT_ID = "<APP_CLIENT_ID_DO_lab2-cli-client>"`
> - **Bash:** `USER_POOL_ID="<USER_POOL_ID>"` e `APP_CLIENT_ID="<APP_CLIENT_ID_DO_lab2-cli-client>"`

**PowerShell (Windows):**
```powershell
# Criar usuário (sem envio de e-mail de convite)
aws cognito-idp admin-create-user --user-pool-id $USER_POOL_ID --username testuser@exemplo.com --user-attributes Name=email,Value=testuser@exemplo.com Name=email_verified,Value=true --temporary-password TempPass123! --message-action SUPPRESS

# Definir senha permanente
aws cognito-idp admin-set-user-password --user-pool-id $USER_POOL_ID --username testuser@exemplo.com --password LabPass@2024 --permanent
```

**Bash (Linux/macOS/Git Bash/WSL):**
```bash
# Criar usuário (sem envio de e-mail de convite)
aws cognito-idp admin-create-user --user-pool-id $USER_POOL_ID --username testuser@exemplo.com --user-attributes Name=email,Value=testuser@exemplo.com Name=email_verified,Value=true --temporary-password TempPass123! --message-action SUPPRESS

# Definir senha permanente
aws cognito-idp admin-set-user-password --user-pool-id $USER_POOL_ID --username testuser@exemplo.com --password LabPass@2024 --permanent
```

---
## Parte 3 – Autenticação e Obtenção de Tokens

**PowerShell:**
```powershell
# Autenticar e obter tokens
aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH --auth-parameters USERNAME=testuser@exemplo.com,PASSWORD=LabPass@2024 --client-id $APP_CLIENT_ID
```

**Bash:**
```bash
# Autenticar e obter tokens
aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH --auth-parameters USERNAME=testuser@exemplo.com,PASSWORD=LabPass@2024 --client-id $APP_CLIENT_ID
```

A resposta inclui `IdToken`, `AccessToken`, `RefreshToken` e `ExpiresIn`.

---
## Parte 4 – Inspecionar o JWT

Execute o script `decode_jwt.py` passando o token obtido:

```
python decode_jwt.py
```

> No Linux/macOS use `python3 decode_jwt.py` se necessário.

Abra `decode_jwt.py` e substitua o valor da variável `TOKEN = "<COLE_O_TOKEN_AQUI>"` pelo `IdToken` ou `AccessToken` obtido na Parte 3.

**Claims relevantes no IdToken:**
- `sub` – identificador único do usuário
- `email` – e-mail
- `cognito:username` – username no User Pool
- `iss` – emissor (URL do User Pool)
- `aud` – App Client ID
- `exp` – timestamp de expiração

---
## Parte 5 – Grupos e Claim `cognito:groups`

**PowerShell:**
```powershell
# Criar grupo
aws cognito-idp create-group --user-pool-id $USER_POOL_ID --group-name admins

# Adicionar usuário ao grupo
aws cognito-idp admin-add-user-to-group --user-pool-id $USER_POOL_ID --username testuser@exemplo.com --group-name admins

# Autenticar novamente para obter token com o claim cognito:groups atualizado
$TOKEN = aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH --auth-parameters USERNAME=testuser@exemplo.com,PASSWORD=LabPass@2024 --client-id $APP_CLIENT_ID --query 'AuthenticationResult.IdToken' --output text

# Cole o valor de $TOKEN na variável TOKEN de decode_jwt.py e execute:
# python decode_jwt.py
# O claim "cognito:groups" deve aparecer com ["admins"]
```

**Bash:**
```bash
# Criar grupo
aws cognito-idp create-group --user-pool-id $USER_POOL_ID --group-name admins

# Adicionar usuário ao grupo
aws cognito-idp admin-add-user-to-group --user-pool-id $USER_POOL_ID --username testuser@exemplo.com --group-name admins

# Autenticar novamente para obter token com o claim cognito:groups atualizado
TOKEN=$(aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH --auth-parameters USERNAME=testuser@exemplo.com,PASSWORD=LabPass@2024 --client-id $APP_CLIENT_ID --query 'AuthenticationResult.IdToken' --output text)

# Cole o valor de $TOKEN na variável TOKEN de decode_jwt.py e execute:
# python decode_jwt.py
# O claim "cognito:groups" deve aparecer com ["admins"]
```

---
## Parte 6 – Renovar Tokens com Refresh Token

**PowerShell:**
```powershell
$REFRESH_TOKEN = "<REFRESH_TOKEN_OBTIDO_NA_PARTE_3>"

aws cognito-idp initiate-auth --auth-flow REFRESH_TOKEN_AUTH --auth-parameters REFRESH_TOKEN=$REFRESH_TOKEN --client-id $APP_CLIENT_ID
```

**Bash:**
```bash
REFRESH_TOKEN="<REFRESH_TOKEN_OBTIDO_NA_PARTE_3>"

aws cognito-idp initiate-auth --auth-flow REFRESH_TOKEN_AUTH --auth-parameters REFRESH_TOKEN=$REFRESH_TOKEN --client-id $APP_CLIENT_ID
```

A resposta retorna novos `IdToken` e `AccessToken` sem solicitar senha novamente.

---
## Pontos de Verificação

- O campo `exp` no JWT é um Unix timestamp: `python -c "import datetime; print(datetime.datetime.fromtimestamp(<EXP>))"`
- Um token de outro User Pool (com `iss` diferente) seria rejeitado por qualquer authorizer
- O `RefreshToken` não é um JWT padrão — é opaco para o cliente

---
## Limpeza

O User Pool é criado com proteção contra exclusão ativa e com um domínio de hosted UI configurado. Ambos precisam ser tratados antes de deletar o pool.

**PowerShell:**
```powershell
# 1. Desativar proteção contra exclusão
aws cognito-idp update-user-pool --user-pool-id $USER_POOL_ID --deletion-protection INACTIVE

# 2. Obter o nome do domínio configurado no pool
$DOMAIN = aws cognito-idp describe-user-pool --user-pool-id $USER_POOL_ID --query 'UserPool.Domain' --output text
Write-Output "Domain: $DOMAIN"

# 3. Deletar o domínio
aws cognito-idp delete-user-pool-domain --domain $DOMAIN --user-pool-id $USER_POOL_ID

# 4. Deletar o User Pool
aws cognito-idp delete-user-pool --user-pool-id $USER_POOL_ID
```

**Bash:**
```bash
# 1. Desativar proteção contra exclusão
aws cognito-idp update-user-pool --user-pool-id $USER_POOL_ID --deletion-protection INACTIVE

# 2. Obter o nome do domínio configurado no pool
DOMAIN=$(aws cognito-idp describe-user-pool --user-pool-id $USER_POOL_ID --query 'UserPool.Domain' --output text)
echo "Domain: $DOMAIN"

# 3. Deletar o domínio
aws cognito-idp delete-user-pool-domain --domain $DOMAIN --user-pool-id $USER_POOL_ID

# 4. Deletar o User Pool
aws cognito-idp delete-user-pool --user-pool-id $USER_POOL_ID
```
