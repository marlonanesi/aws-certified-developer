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

1. Console → **Lambda → Create function** ("Criar função") → name: `lab5-app` → Runtime: Python 3.12
2. Cole o código do arquivo `app_lambda.py`
3. Adicionar variável de ambiente: `SECRET_NAME` = `prod/lab5/database`
4. **Configuration** ("Configuração") **→ Permissions** ("Permissões") **→ Execution role** ("Função de execução") → adicionar policy:

```json
{
  "Effect": "Allow",
  "Action": "secretsmanager:GetSecretValue",
  "Resource": "arn:aws:secretsmanager:*:*:secret:prod/lab5/*"
}
```

5. Testar a função com evento `{}`

---
## Parte 4 – Rotação Automática (Lambda Customizado)

```
# Dar permissão ao Secrets Manager para invocar a Lambda
aws lambda add-permission --function-name lab5-rotation --statement-id allow-secrets-manager --action lambda:InvokeFunction --principal secretsmanager.amazonaws.com

# Configurar rotação automática no secret
aws secretsmanager rotate-secret --secret-id "prod/lab5/database" --rotation-lambda-arn arn:aws:lambda:<REGION>:<ACCOUNT_ID>:function:lab5-rotation --rotation-rules AutomaticallyAfterDays=30

# Forçar rotação imediata para testar
aws secretsmanager rotate-secret --secret-id "prod/lab5/database"

# Verificar versões após rotação
aws secretsmanager list-secret-version-ids --secret-id "prod/lab5/database"
```

> Todos os comandos acima funcionam em Bash e PowerShell.

---
## Parte 5 – Parameter Store para Comparação

```
# Parâmetro simples (String)
aws ssm put-parameter --name "/lab5/app/feature-flag-dark-mode" --type "String" --value "false"

# Parâmetro numérico
aws ssm put-parameter --name "/lab5/app/max-connections" --type "String" --value "100"

# Parâmetro seguro (SecureString — usa AWS Managed Key por padrão, gratuito)
aws ssm put-parameter --name "/lab5/app/api-key" --type "SecureString" --value "sk-1234567890abcdef"

# Ler parâmetro seguro (com decriptação)
aws ssm get-parameter --name "/lab5/app/api-key" --with-decryption

# Ler todos os parâmetros do prefixo /lab5/app/
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
| Caso de uso típico | Credenciais de BD, tokens OAuth | Feature flags, configurações de app |

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
aws ssm delete-parameters --names "/lab5/app/feature-flag-dark-mode" "/lab5/app/max-connections" "/lab5/app/api-key"

# Deletar funções Lambda
aws lambda delete-function --function-name lab5-app
aws lambda delete-function --function-name lab5-rotation
```

> Todos os comandos acima funcionam em Bash e PowerShell.
