# Roteiro — Lab 1: Push de Imagem para o Amazon ECR

> **Compatibilidade de comandos**
> Os blocos de código abaixo indicam o terminal alvo (**Bash** ou **PowerShell**).
> Comandos sem variáveis de ambiente (ex: `docker build`, `aws ecr delete-repository`) funcionam diretamente em ambos os terminais — copie e cole sem adaptação.
> Para os blocos com variáveis, use a versão correta conforme seu sistema:
> - Linux / macOS / Git Bash → bloco `bash`
> - Windows PowerShell → bloco `powershell`

## Custos e Free Tier

| Serviço | Free Tier |
|---------|-----------|
| ECR | 500 MB de armazenamento/mês (primeiros 12 meses) |
| ECR (transferência) | 1 GB de saída para internet/mês grátis |

> **Aviso:** Recursos na nuvem podem gerar custos mesmo dentro do Free Tier, pois ele tem limites mensais e pode ser esgotado. Imagens grandes ou muitas revisões acumuladas aumentam o armazenamento cobrado. Ao finalizar a prática, **desprovisione todos os recursos** para evitar cobranças inesperadas.

---
## Objetivo

Criar um repositório privado no Amazon ECR, autenticar o Docker CLI, construir uma imagem simples, e fazer push com duas tags. Ao final, configurar uma lifecycle policy para controle de retenção.

---
## Pré-requisitos

- AWS CLI v2 instalada e configurada (`aws configure`)
- Docker Desktop instalado e rodando
- Permissão IAM: `AmazonEC2ContainerRegistryFullAccess`

---
## Parte 1 — Criar o Repositório no ECR

Console AWS → **ECR** → **Create repository** ("Criar repositório"):

| Campo | Valor |
|---|---|
| Visibility | Private |
| Repository name | `dva-demo-app` |
| Tag immutability | Disable |
| Scan on push | Enable |

Anote o **URI** do repositório no formato:
```
<account-id>.dkr.ecr.<region>.amazonaws.com/dva-demo-app
```

---
## Parte 2 — Criar a Aplicação e o Dockerfile

Os arquivos `app.py` e `Dockerfile` desta pasta contêm a aplicação de exemplo. Copie-os para um diretório de trabalho:

```
mkdir dva-demo-app && cd dva-demo-app
# copie app.py e Dockerfile para este diretório
```

`app.py` é um servidor HTTP mínimo que responde na porta 8080. `Dockerfile` usa `python:3.11-alpine` como base — imagem de ~5 MB.

---
## Parte 3 — Build e Teste Local

**Bash:**
```bash
mkdir dva-demo-app && cd dva-demo-app
```
**PowerShell:**
```powershell
New-Item -ItemType Directory -Name dva-demo-app; Set-Location dva-demo-app
```

> Copie os arquivos `app.py` e `Dockerfile` para dentro deste diretório.

Os comandos Docker abaixo funcionam em **Bash e PowerShell** sem adaptação:
```
docker build -t dva-demo-app .
docker run -p 8080:8080 dva-demo-app
```

Em outro terminal (Bash e PowerShell):
```
curl http://localhost:8080
```
Saída esperada: `Hello from ECR! Container rodando na AWS!`

Para parar o container: `Ctrl+C`

---
## Parte 4 — Autenticar Docker com ECR

**Bash:**
```bash
REGION=$(aws configure get region)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
```

**PowerShell:**
```powershell
$REGION = aws configure get region
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
```

Saída esperada: `Login Succeeded`

> O token de autenticação expira em **12 horas**. Em pipelines CI/CD, este comando é executado antes de cada push.

---
## Parte 5 — Tag e Push

**Bash:**
```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)
URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/dva-demo-app"

docker tag dva-demo-app:latest ${URI}:v1.0.0
docker tag dva-demo-app:latest ${URI}:latest
docker push ${URI}:v1.0.0
docker push ${URI}:latest
```

**PowerShell:**
```powershell
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$REGION = aws configure get region
$URI = "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/dva-demo-app"

docker tag dva-demo-app:latest "${URI}:v1.0.0"
docker tag dva-demo-app:latest "${URI}:latest"
docker push "${URI}:v1.0.0"
docker push "${URI}:latest"
```

O push envia cada layer individualmente. Em re-pushes com pequenas mudanças, apenas as layers alteradas são transferidas.

---
## Parte 6 — Verificar no Console

ECR → repositório `dva-demo-app`:
- Confirme as duas tags: `v1.0.0` e `latest`
- Verifique o tamanho da imagem (menor que 20 MB graças ao alpine)
- Observe a aba **Scan results** — mostra vulnerabilidades detectadas automaticamente

---
## Parte 7 — Lifecycle Policy

ECR → repositório `dva-demo-app` → **Lifecycle policies** → **Create rule** ("Criar regra"):

**Regra 1 — imagens sem tag:**
| Campo | Valor |
|---|---|
| Priority | 1 |
| Image status | Untagged |
| Match criteria | Since image pushed → 7 days |

**Regra 2 — imagens tagged (limite de 10):**
| Campo | Valor |
|---|---|
| Priority | 2 |
| Image status | Tagged |
| Tag prefixes | `v` |
| Match criteria | Image count more than → 10 |

Lifecycle policies evitam o acúmulo de dezenas de imagens e o custo de armazenamento associado.

---
## Referência de Comandos

| Ação | Comando |
|------|---------|
| Autenticar | `aws ecr get-login-password \| docker login --username AWS --password-stdin <uri>` |
| Build | `docker build -t nome .` |
| Tag | `docker tag nome:tag <uri>:tag` |
| Push | `docker push <uri>:tag` |
| Listar imagens | `aws ecr list-images --repository-name dva-demo-app` |

---
## Erros Comuns

| Erro | Causa | Solução |
|------|-------|---------|
| `no basic auth credentials` | Autenticação expirada | Rodar `get-login-password` novamente |
| `denied: User is not authorized` | Permissão IAM insuficiente | Adicionar `AmazonEC2ContainerRegistryFullAccess` |
| `name unknown: The repository does not exist` | Repositório não criado | Criar repositório antes do push |

---
## Limpeza

Os comandos abaixo funcionam em **Bash e PowerShell** sem adaptação:

```
aws ecr batch-delete-image --repository-name dva-demo-app --image-ids imageTag=v1.0.0 imageTag=latest
aws ecr delete-repository --repository-name dva-demo-app --force
```
