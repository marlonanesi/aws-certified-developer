# Lab 5 – Gerenciando Segredos com Secrets Manager e Parameter Store

> **Compatibilidade de comandos CLI**
> Este roteiro apresenta blocos para **PowerShell** (Windows) e **Bash** (Linux/macOS/Git Bash/WSL).
> Strings JSON em single-quotes funcionam em ambos os terminais sem necessidade de escaping adicional.
> CMD não é suportado; use PowerShell ou Bash.

---
> **Custos e Free Tier**
> - **AWS Secrets Manager:** **$0,40 por secret por mês** + $0,05 por 10.000 chamadas de API — **não há free tier**
> - **AWS Systems Manager Parameter Store (Standard):** gratuito para parâmetros Standard (incluindo SecureString via AWS Managed Key)
> - **Lambda:** 1 milhão de invocações gratuitas/mês (permanente)
>
> O secret criado neste lab **gera custo imediatamente** ($0,40/mês). Execute a limpeza ao finalizar.
>
> ⚠️ **Aviso importante:** qualquer recurso provisionado na AWS pode gerar custos mesmo dentro do free tier, que possui limites mensais. Ao concluir o lab, execute a etapa de limpeza para evitar cobranças inesperadas.

---
## Objetivo

Criar e gerenciar segredos no AWS Secrets Manager, configurar rotação automática com Lambda, comparar com o AWS Systems Manager Parameter Store e demonstrar integração com uma função Lambda.

---
## Pré-requisitos

- Conta AWS com permissões em Secrets Manager, Lambda e SSM Parameter Store
- AWS CLI configurado

---
## Parte 1 – Criar Secret no Secrets Manager

**PowerShell:**
```powershell
$secretValue = '{"username":"admin","password":"LabPass@2024","host":"db.exemplo.com","port":5432}'
aws secretsmanager create-secret --name "prod/lab5/database" --description "Credenciais de banco de dados - Lab 5" --secret-string $secretValue --tags Key=Env,Value=lab Key=Project,Value=lab5

# Verificar metadados
aws secretsmanager describe-secret --secret-id "prod/lab5/database"

# Ler o valor atual
aws secretsmanager get-secret-value --secret-id "prod/lab5/database"
```

**Bash:**
```bash
SECRET_VALUE='{"username":"admin","password":"LabPass@2024","host":"db.exemplo.com","port":5432}'
aws secretsmanager create-secret --name "prod/lab5/database" --description "Credenciais de banco de dados - Lab 5" --secret-string "$SECRET_VALUE" --tags Key=Env,Value=lab Key=Project,Value=lab5

# Verificar metadados
aws secretsmanager describe-secret --secret-id "prod/lab5/database"

# Ler o valor atual
aws secretsmanager get-secret-value --secret-id "prod/lab5/database"
```

---
## Parte 2 – Versionamento de Secrets

**PowerShell:**
```powershell
$newSecret = '{"username":"admin","password":"NovaPass@2024!","host":"db.exemplo.com","port":5432}'
aws secretsmanager put-secret-value --secret-id "prod/lab5/database" --secret-string $newSecret

# Listar todas as versões
aws secretsmanager list-secret-version-ids --secret-id "prod/lab5/database"
# Observe os stage labels: AWSCURRENT e AWSPREVIOUS

# Acessar a versão anterior
aws secretsmanager get-secret-value --secret-id "prod/lab5/database" --version-stage AWSPREVIOUS
```

**Bash:**
```bash
NEW_SECRET='{"username":"admin","password":"NovaPass@2024!","host":"db.exemplo.com","port":5432}'
aws secretsmanager put-secret-value --secret-id "prod/lab5/database" --secret-string "$NEW_SECRET"

# Listar todas as versões
aws secretsmanager list-secret-version-ids --secret-id "prod/lab5/database"
# Observe os stage labels: AWSCURRENT e AWSPREVIOUS

# Acessar a versão anterior
aws secretsmanager get-secret-value --secret-id "prod/lab5/database" --version-stage AWSPREVIOUS
```

---
## Parte 3 – Integração com Lambda

A Lambda de aplicação precisa existir antes de testar a integração. Escolha uma das opções abaixo para criá-la.

### Opção A – Via script (automatizada)

Os scripts criam o IAM role, anexam as policies necessárias, empacotam o arquivo `app_lambda.py`, implantam a função e definem a variável de ambiente `SECRET_NAME` — tudo a partir da pasta `lab5/`.

**PowerShell:**
```powershell
.\create_app_lambda.ps1
```

**Bash:**
```bash
bash create_app_lambda.sh
```

### Opção B – Via console (manual)

1. Console → **Lambda → Funções → Criar função**
2. **"Nome da função"**: `lab5-app` → Runtime: Python 3.12 → clique em **"Criar função"**
3. Na aba **"Código"**, substitua o conteúdo pelo do arquivo `app_lambda.py` desta pasta; clique em **Deploy**
4. Aba **"Configuração"** → **"Variáveis de ambiente"** → **"Editar"** → adicionar:
   - **Chave**: `SECRET_NAME` / **Valor**: `prod/lab5/database`
   - Clique em **"Salvar"**
5. Aba **"Configuração"** → **"Permissões"** → na seção **"Papel de execução"**, clique no nome do role (link azul abaixo de **"Nome da função"**) para abrir no IAM
6. No IAM, clique em **"Adicionar permissões"** → **"Criar política inline"**
7. Selecione a aba **"JSON"**, substitua o conteúdo pelo JSON abaixo e clique em **"Próximo"**:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "secretsmanager:GetSecretValue",
    "Resource": "arn:aws:secretsmanager:*:*:secret:prod/lab5/*"
  }]
}
```
8. Dê um nome à política (ex.: `SecretsManagerRead`) e clique em **"Criar política"**

Na aba **"Teste"**, crie um evento com nome `teste-lab5` e corpo `{}`, depois clique em **"Testar"**. A resposta deve exibir o `username` e `host` lidos diretamente do secret.

---
## Parte 4 – Rotação Automática (Lambda Customizado)

A Lambda de rotação precisa existir antes de configurar a rotação no secret. Escolha uma das opções abaixo para criá-la.

### Opção A – Via script (automatizada)

Os scripts criam o IAM role, anexam as policies necessárias, empacotam o arquivo `rotation_lambda.py` e implantam a função — tudo a partir da pasta `lab5/`. A região padrão configurada é `sa-east-1` (São Paulo).

**PowerShell:**
```powershell
.\create_rotation_lambda.ps1
```

**Bash:**
```bash
bash create_rotation_lambda.sh
```

Ao final, o script exibe o **Function ARN** — anote-o para o próximo passo.

### Opção B – Via console (manual)

1. Console → **Lambda → Create function** ("Criar função") → name: `lab5-rotation` → Runtime: Python 3.12
2. No editor de código inline (Code source → Edit code inline), substitua o conteúdo pelo do arquivo `rotation_lambda.py` desta pasta; clique em **Deploy**
3. Aba **"Configuração"** → **"Permissões"** → na seção **"Papel de execução"**, clique no nome do role (link azul abaixo de **"Nome da função"**) para abrir no IAM → **"Adicionar permissões"** → **"Criar política inline"** → aba **"JSON"**, cole o JSON abaixo, clique em **"Próximo"**, dê o nome `SecretsManagerRotation` e clique em **"Criar política"**:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "secretsmanager:GetSecretValue",
      "secretsmanager:PutSecretValue",
      "secretsmanager:UpdateSecretVersionStage",
      "secretsmanager:DescribeSecret"
    ],
    "Resource": "*"
  }]
}
```

4. Volte à página da função Lambda e anote o **Function ARN** (exibido no cabeçalho)
5. Autorizar o Secrets Manager a invocar a Lambda (substituir `<REGION>` antes de executar):

```
aws lambda add-permission --function-name lab5-rotation --statement-id allow-secrets-manager --action lambda:InvokeFunction --principal secretsmanager.amazonaws.com --region <REGION>
```

---

### Configurar a rotação no secret

Substituir `<FUNCTION_ARN>` pelo ARN anotado na opção escolhida acima:

```
# Configurar rotação automática e disparar a primeira rotação imediatamente
aws secretsmanager rotate-secret --secret-id "prod/lab5/database" --rotation-lambda-arn <FUNCTION_ARN> --rotation-rules AutomaticallyAfterDays=30
```

O comando acima já dispara a primeira rotação automaticamente. Aguarde alguns segundos e verifique o status antes de prosseguir:

```
aws secretsmanager describe-secret --secret-id "prod/lab5/database" --query 'RotationEnabled'
aws secretsmanager list-secret-version-ids --secret-id "prod/lab5/database"
```

> Somente force uma nova rotação após a anterior estar concluída. Se executar o comando de rotação enquanto uma rotação ainda está em andamento, o erro `InvalidRequestException: A previous rotation isn't complete` será retornado — isso é esperado, não é uma falha. Aguarde e tente novamente.

```
# Forçar rotação imediata adicional (somente após a anterior concluir)
aws secretsmanager rotate-secret --secret-id "prod/lab5/database"
```

> Todos os comandos acima funcionam em Bash e PowerShell.

---
## Parte 5 – Parameter Store para Comparação

O Parameter Store é um serviço de **configuração**, não de gerenciamento de segredos. Ele suporta o tipo `SecureString` (valor cifrado com KMS), o que o torna aceitável para valores sensíveis estáticos e de baixo risco — como flags de configuração cifradas ou identificadores internos. Para credenciais reais (senhas de banco de dados, tokens OAuth, chaves de API de terceiros), o Secrets Manager é o serviço recomendado pela AWS, pois oferece rotação automática, versionamento e auditoria por secret.

```
# Parâmetro simples (String) — feature flag
aws ssm put-parameter --name "/lab5/app/feature-flag-dark-mode" --type "String" --value "false"

# Parâmetro numérico — configuração de pool de conexões
aws ssm put-parameter --name "/lab5/app/max-connections" --type "String" --value "100"

# Parâmetro cifrado (SecureString) — valor sensível estático de baixo risco
# Nota: para segredos reais com rotação, use o Secrets Manager (Partes 1-4)
aws ssm put-parameter --name "/lab5/app/internal-token" --type "SecureString" --value "tk-1234567890abcdef"
```

Os três parâmetros estão criados. Agora leia-os de volta:

```
# Ler parâmetro cifrado (com decriptação)
aws ssm get-parameter --name "/lab5/app/internal-token" --with-decryption

# Ler todos os parâmetros do prefixo /lab5/app/ de uma vez
aws ssm get-parameters-by-path --path "/lab5/app" --recursive --with-decryption
```

> Todos os comandos acima funcionam em Bash e PowerShell.

---
## Comparação: Secrets Manager × Parameter Store

| | Secrets Manager | Parameter Store Standard |
|---|---|---|
| Custo de armazenamento | $0,40/secret/mês | Gratuito |
| Custo de API | $0,05/10k chamadas | Gratuito |
| Rotação automática | ✅ Nativa | ❌ Manual |
| Versionamento | ✅ Automático (AWSCURRENT/AWSPREVIOUS) | ✅ Manual (histórico limitado) |
| Cross-account | ✅ | ❌ |
| Caso de uso típico | Credenciais de BD, tokens OAuth, segredos com rotação | Feature flags, configurações de app, valores sensíveis estáticos de baixo risco |

---
## Pontos de Verificação

- O campo `VersionStages` mostra `AWSCURRENT` e `AWSPREVIOUS` após a atualização
- A Lambda com cache (`_secret_cache`) não chama o Secrets Manager a cada invocação — importante para reduzir custo e latência
- Durante a rotação, a Lambda executa 4 steps em ordem: `createSecret` → `setSecret` → `testSecret` → `finishSecret`
- Um secret deletado entra em período de recuperação de 7 a 30 dias por padrão

---
## Limpeza

```
# Deletar o secret (--force-delete-without-recovery pula o período de recuperação)
aws secretsmanager delete-secret --secret-id "prod/lab5/database" --force-delete-without-recovery

# Deletar parâmetros do Parameter Store
aws ssm delete-parameters --names "/lab5/app/feature-flag-dark-mode" "/lab5/app/max-connections" "/lab5/app/internal-token"

# Deletar funções Lambda
aws lambda delete-function --function-name lab5-app
aws lambda delete-function --function-name lab5-rotation

# Remover policy inline e deletar o IAM role criado pelo script da app (se usou Opção A na Parte 3)
aws iam delete-role-policy --role-name lab5-app-role --policy-name SecretsManagerRead
aws iam detach-role-policy --role-name lab5-app-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam delete-role --role-name lab5-app-role

# Remover policy inline e deletar o IAM role criado pelo script (se usou Opção A na Parte 4)
aws iam delete-role-policy --role-name lab5-rotation-role --policy-name SecretsManagerRotation
aws iam detach-role-policy --role-name lab5-rotation-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam delete-role --role-name lab5-rotation-role
```

> Todos os comandos acima funcionam em Bash e PowerShell.
