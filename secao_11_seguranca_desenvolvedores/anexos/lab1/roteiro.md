# Lab 1 – Cross-Account Access com AWS STS

> **Compatibilidade de comandos CLI**
> Este roteiro apresenta blocos para **PowerShell** (Windows) e **Bash** (Linux/macOS/Git Bash/WSL).
> CMD não é suportado.

---
> **Custos e Free Tier**
> O AWS STS não tem custo adicional por chamadas de API. Os outros serviços usados neste lab (IAM, S3 Read) também não geram custo direto. Se um bucket S3 for criado para validação, lembre-se que armazenamento e requisições S3 podem gerar custos fora do free tier.
>
> ⚠️ **Aviso importante:** qualquer recurso provisionado na AWS pode gerar custos, mesmo dentro do free tier (que tem limites mensais). Ao concluir o lab, execute a etapa de limpeza para evitar cobranças inesperadas.

---
## Objetivo

Configurar acesso cross-account utilizando AWS STS AssumeRole. Ao final, será possível obter credenciais temporárias de uma conta "destino" a partir de uma conta "origem", e usá-las para operar na conta destino.

---
## Pré-requisitos

- Duas contas AWS (ou dois usuários IAM com políticas distintas simulando contas separadas)
- AWS CLI configurado com permissões IAM na conta origem
- Python 3 com `boto3` instalado

---
## Parte 1 – Criar o Role na Conta Destino

1. No console da **conta destino**, acesse **IAM → Roles → Create role** ("Criar função")
2. Trusted entity type: **AWS account**
3. Informe o **Account ID da conta origem**
4. Adicione a policy gerenciada: `AmazonS3ReadOnlyAccess`
5. Role name: `CrossAccountS3Role`
6. Anote o **ARN do role** criado: `arn:aws:iam::<DESTINO_ID>:role/CrossAccountS3Role`

**Trust Policy gerada (verificar após criar):**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::<ORIGEM_ID>:root"},
    "Action": "sts:AssumeRole"
  }]
}
```

---
## Parte 2 – Conceder Permissão de AssumeRole na Conta Origem

Na **conta origem**, crie e atache a seguinte policy ao usuário ou role que realizará o assume:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "sts:AssumeRole",
    "Resource": "arn:aws:iam::<DESTINO_ID>:role/CrossAccountS3Role"
  }]
}
```

---
## Parte 3 – AssumeRole via AWS CLI

**PowerShell (Windows):**
```powershell
# Assumir o role na conta destino
aws sts assume-role --role-arn "arn:aws:iam::<DESTINO_ID>:role/CrossAccountS3Role" --role-session-name "lab1-session"

# A resposta retorna: AccessKeyId, SecretAccessKey, SessionToken, Expiration

# Exportar as credenciais temporárias
$env:AWS_ACCESS_KEY_ID = "<AccessKeyId>"
$env:AWS_SECRET_ACCESS_KEY = "<SecretAccessKey>"
$env:AWS_SESSION_TOKEN = "<SessionToken>"

# Verificar identidade atual (deve mostrar o ARN do role assumido)
aws sts get-caller-identity

# Testar acesso ao S3 da conta destino
aws s3 ls
```

**Bash (Linux/macOS/Git Bash/WSL):**
```bash
# Assumir o role na conta destino
aws sts assume-role --role-arn "arn:aws:iam::<DESTINO_ID>:role/CrossAccountS3Role" --role-session-name "lab1-session"

# A resposta retorna: AccessKeyId, SecretAccessKey, SessionToken, Expiration

# Exportar as credenciais temporárias
export AWS_ACCESS_KEY_ID="<AccessKeyId>"
export AWS_SECRET_ACCESS_KEY="<SecretAccessKey>"
export AWS_SESSION_TOKEN="<SessionToken>"

# Verificar identidade atual (deve mostrar o ARN do role assumido)
aws sts get-caller-identity

# Testar acesso ao S3 da conta destino
aws s3 ls
```

---
## Parte 4 – AssumeRole via SDK Python

Execute o script `assume_role.py` incluído nesta pasta:

```
python assume_role.py
```

> No Linux/macOS use `python3 assume_role.py` se `python` não estiver mapeado.

O script realiza o assume, exibe as credenciais temporárias e lista os buckets S3 da conta destino.

Substitua `<DESTINO_ID>` no script antes de executar.

---
## Parte 5 – Verificar Identidade e Restaurar Credenciais

**PowerShell:**
```powershell
# Ainda com as variáveis exportadas — deve mostrar conta DESTINO
aws sts get-caller-identity

# Restaurar credenciais originais da conta origem
Remove-Item Env:AWS_ACCESS_KEY_ID
Remove-Item Env:AWS_SECRET_ACCESS_KEY
Remove-Item Env:AWS_SESSION_TOKEN

# Confirmar retorno à identidade original
aws sts get-caller-identity
```

**Bash:**
```bash
# Ainda com as variáveis exportadas — deve mostrar conta DESTINO
aws sts get-caller-identity

# Restaurar credenciais originais da conta origem
unset AWS_ACCESS_KEY_ID
unset AWS_SECRET_ACCESS_KEY
unset AWS_SESSION_TOKEN

# Confirmar retorno à identidade original
aws sts get-caller-identity
```

---
## Pontos de Verificação

- O `Account` retornado por `get-caller-identity` muda para o ID da conta destino durante o assume
- Sem a policy `sts:AssumeRole` na conta origem, a chamada retorna `AccessDenied`
- Sem o Account ID correto no trust policy, a chamada também falha com `AccessDenied`
- O campo `Expiration` indica quando as credenciais expiram (padrão: 1 hora)
- Após expirar, qualquer chamada retorna `ExpiredTokenException`

---
## Limpeza

```
# Na conta destino: deletar o role
aws iam delete-role --role-name CrossAccountS3Role
# (se houver policy inline, removê-la antes com delete-role-policy)

# Na conta origem: remover a policy de assume role do usuário/role
```

> Funciona em Bash e PowerShell sem adaptação.
