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

1. Console AWS → **Amazon Cognito → User Pools → Create user pool** ("Criar grupo de usuários")
2. **Step 1 – Sign-in experience:**
   - Authentication providers: Cognito user pool
   - Sign-in options: ✅ Email
3. **Step 2 – Security requirements:**
   - Password policy: Cognito defaults
   - MFA: **No MFA** (para simplificar o lab; pode explorar Optional TOTP depois)
   - Account recovery: Email only
4. **Step 3 – Sign-up experience:**
   - Self-registration: ✅ Enable
   - Required attributes: `email`
5. **Step 4 – Message delivery:**
   - Email: **Send email with Cognito** (gratuito, limite 50 emails/dia)
6. **Step 5 – App integration:**
   - User pool name: `lab2-user-pool`
   - ✅ Use the Cognito Hosted UI
   - Domain: `lab2-<identificador-unico>` (deve ser único globalmente)
   - App client name: `lab2-app-client`
   - App type: **Public client**
   - Callback URL: `http://localhost:3000/callback`
   - Allowed OAuth flows: ✅ Authorization code grant
   - Allowed OAuth scopes: ✅ openid ✅ email ✅ profile
7. **Anote:** User Pool ID e App Client ID

---
## Parte 2 – Criar Usuário de Teste

**PowerShell (Windows):**
```powershell
# Substituir pelos IDs anotados no Passo 1
$USER_POOL_ID = "<USER_POOL_ID>"
$APP_CLIENT_ID = "<APP_CLIENT_ID>"

# Criar usuário (sem envio de e-mail de convite)
aws cognito-idp admin-create-user --user-pool-id $USER_POOL_ID --username testuser@exemplo.com --user-attributes Name=email,Value=testuser@exemplo.com Name=email_verified,Value=true --temporary-password TempPass123! --message-action SUPPRESS

# Definir senha permanente
aws cognito-idp admin-set-user-password --user-pool-id $USER_POOL_ID --username testuser@exemplo.com --password LabPass@2024 --permanent
```

**Bash (Linux/macOS/Git Bash/WSL):**
```bash
# Substituir pelos IDs anotados no Passo 1
USER_POOL_ID="<USER_POOL_ID>"
APP_CLIENT_ID="<APP_CLIENT_ID>"

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

Edite o script para colar o `IdToken` ou `AccessToken` antes de executar.

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

# Autenticar novamente e inspecionar o IdToken
# O claim "cognito:groups" deve aparecer com ["admins"]
```

**Bash:**
```bash
# Criar grupo
aws cognito-idp create-group --user-pool-id $USER_POOL_ID --group-name admins

# Adicionar usuário ao grupo
aws cognito-idp admin-add-user-to-group --user-pool-id $USER_POOL_ID --username testuser@exemplo.com --group-name admins

# Autenticar novamente e inspecionar o IdToken
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

```
# Deletar o User Pool (deleta automaticamente usuários e grupos)
aws cognito-idp delete-user-pool --user-pool-id <USER_POOL_ID>
```

> Funciona em Bash e PowerShell. Substitua `<USER_POOL_ID>` pelo valor real ou use a variável `$USER_POOL_ID` (PS) / `$USER_POOL_ID` (Bash).
