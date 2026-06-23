# Scripts de Autenticação MFA AWS

Esses scripts automatizam o fluxo de autenticação MFA na AWS via CLI, eliminando a necessidade de rodar manualmente o `aws sts get-session-token` e copiar as credenciais nos arquivos de configuração.

## O problema que resolvem

Sem o script, o fluxo manual seria:
1. Rodar `aws sts get-session-token --serial-number <arn-mfa> --token-code <codigo>`
2. Copiar `AccessKeyId`, `SecretAccessKey` e `SessionToken` da resposta JSON
3. Editar manualmente o arquivo `~/.aws/credentials` (ou rodar 3x `aws configure set`)

Com o script: basta executar e digitar o código MFA.

---

## `auth-mfa.bat` — Windows

### Pré-requisitos
- AWS CLI instalada
- PowerShell disponível (já incluso no Windows)

### Configuração (editar antes de usar)

Abra o arquivo e ajuste as variáveis no topo:

```bat
set "MFA_ARN=arn:aws:iam::<id da sua conta>:mfa/cli-user-mfa"
set "SOURCE_PROFILE=base"
set "TARGET_PROFILE=default"
```

| Variável | O que é |
|---|---|
| `MFA_ARN` | ARN do dispositivo MFA vinculado ao seu usuário IAM. Encontre em IAM → Users → Security credentials → MFA device |
| `SOURCE_PROFILE` | Perfil com as credenciais base (sem MFA) configuradas no `~/.aws/credentials` |
| `TARGET_PROFILE` | Perfil onde as credenciais temporárias serão gravadas (normalmente `default`) |

### Como usar

Dê duplo clique no arquivo `auth-mfa.bat` ou rode no terminal:

```cmd
auth-mfa.bat
```

O script vai pedir o código de 6 dígitos do seu app autenticador (Google Authenticator, Authy, etc.), chamar o STS e gravar as credenciais temporárias no perfil `TARGET_PROFILE` automaticamente.

---

## `auth-mfa.sh` — Linux / macOS

### Pré-requisitos
- AWS CLI instalada
- `jq` instalado (usado para parsear o JSON da resposta do STS)

```bash
# Ubuntu/Debian
sudo apt install jq

# macOS
brew install jq
```

### Configuração (editar antes de usar)

Abra o arquivo e ajuste as variáveis no topo:

```bash
MFA_ARN="arn:aws:iam::123456789012:mfa/cli-user"
PROFILE_NAME="default"
```

| Variável | O que é |
|---|---|
| `MFA_ARN` | ARN do dispositivo MFA do seu usuário IAM |
| `PROFILE_NAME` | Perfil onde as credenciais temporárias serão gravadas |

> Diferente do `.bat`, o script `.sh` usa apenas um perfil (não separa `SOURCE_PROFILE` de `TARGET_PROFILE`). As credenciais base precisam estar no perfil `default` ou você pode chamar com `--profile` ajustado manualmente no script.

### Como usar

Dê permissão de execução (apenas na primeira vez):

```bash
chmod +x auth-mfa.sh
```

Execute:

```bash
./auth-mfa.sh
```

Digite o código MFA quando solicitado. As credenciais temporárias serão gravadas no perfil configurado em `PROFILE_NAME`.

---

## Observações

- As credenciais temporárias geradas pelo STS expiram em **12 horas** por padrão. Após esse prazo, execute o script novamente.
- O script `.bat` cria um arquivo `.ps1` temporário em `%TEMP%` durante a execução e o mantém para debug. Remova o comentário da linha `del "%TEMP_PS1%"` para apagar automaticamente.
