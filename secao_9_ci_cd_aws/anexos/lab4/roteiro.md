# Roteiro — Lab 4: AWS CodePipeline — Pipeline CI/CD Completo

> **Compatibilidade de comandos**
> Os blocos de código abaixo indicam o terminal alvo (**Bash** ou **PowerShell**).
> Comandos sem variáveis (`aws`, `git`) funcionam diretamente em ambos os terminais — copie e cole sem adaptação.
> - Linux / macOS / Git Bash → bloco `bash`
> - Windows PowerShell → bloco `powershell`

## Custos e Free Tier

| Serviço | Free Tier |
|---------|-----------|
| CodePipeline | 1 pipeline ativo/mês gratuito (primeiros 12 meses) |
| CodeBuild | 100 minutos/mês `build.general1.small` (primeiros 12 meses) |
| SNS | 1 milhão de publicações/mês (permanente) |
| S3 | 5 GB storage + 20k GET + 2k PUT (primeiros 12 meses) |

> **Aviso:** Recursos na nuvem podem gerar custos mesmo dentro do Free Tier, pois ele tem limites mensais e pode ser esgotado. Um pipeline que permanece ativo com webhook no CodeCommit dispara builds a cada push, consumindo minutos do CodeBuild. Ao finalizar, **delete o pipeline** e desabilite webhooks para evitar cobranças contínuas.

---
## Pré-requisito

Labs 1, 2 e 3 concluídos. Repositório `demo-dva-pipeline`, projeto `demo-dva-build` e Application CodeDeploy `demo-webapp` existentes.

---
## Objetivo

Criar um CodePipeline que integra Source → Build → Aprovação Manual → Deploy. Observar o fluxo end-to-end, configurar notificações de falha e executar rollback manual.

---
## Arquitetura

```
CodeCommit      CodeBuild         Aprovação Manual      CodeDeploy
(git push)  →  (build + test)  →  (SNS → Revisor)   →  (Blue/Green)
  Source            Build             Approval              Deploy
```

---
## Parte 1 — Criar Tópico SNS para Notificações

O comando de criação do tópico funciona em **Bash e PowerShell** sem adaptação:
```
aws sns create-topic --name codepipeline-notifications
```

Para a inscrição do e-mail (substitua `seu@email.com`):

**Bash:**
```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)
aws sns subscribe --topic-arn "arn:aws:sns:$REGION:$ACCOUNT_ID:codepipeline-notifications" --protocol email --notification-endpoint "seu@email.com"
```

**PowerShell:**
```powershell
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$REGION = aws configure get region
aws sns subscribe --topic-arn "arn:aws:sns:$REGION:$ACCOUNT_ID:codepipeline-notifications" --protocol email --notification-endpoint "seu@email.com"
```

---
## Parte 2 — Criar o Pipeline

Console AWS → **CodePipeline** → **Create pipeline** ("Criar pipeline"):

**Pipeline settings:**

| Campo | Valor |
|---|---|
| Pipeline name | `demo-dva-pipeline-completo` |
| Execution mode | Superseded (padrão) |
| Service role | New service role |
| Artifact store | Default location (S3 automático) |

**Source Stage:**

| Campo | Valor |
|---|---|
| Source provider | AWS CodeCommit |
| Repository | `demo-dva-pipeline` |
| Branch | `main` |
| Detection | Amazon CloudWatch Events (automático) |

**Build Stage:**

| Campo | Valor |
|---|---|
| Build provider | AWS CodeBuild |
| Project name | `demo-dva-build` |

**Deploy Stage:**

| Campo | Valor |
|---|---|
| Deploy provider | AWS CodeDeploy |
| Application name | `demo-webapp` |
| Deployment group | `demo-prod-bluegreen` |

Clique em **Create pipeline** ("Criar pipeline"). O pipeline inicia automaticamente com o commit atual.

---
## Parte 3 — Adicionar Estágio de Aprovação Manual

Na tela do pipeline → **Edit** → entre Build e Deploy → **Add stage** → nome: `Approval`.

Dentro do novo estágio → **Add action group**:

| Campo | Valor |
|---|---|
| Action name | `ManualApproval` |
| Action provider | Manual approval |
| SNS topic ARN | ARN do tópico criado na Parte 1 |
| Comments | "Verifique o ambiente de staging antes de aprovar." |

Salve o pipeline. O CodePipeline pausará neste estágio aguardando aprovação (timeout: 7 dias).

---
## Parte 4 — Disparar e Acompanhar o Pipeline

```
cd demo-dva-pipeline
```

Adicione linhas ao `app.py`:

**Bash:**
```bash
cat >> app.py << 'EOF'

# Feature adicionada no Lab 4
def versao():
    return "v3 - CI/CD Pipeline completo!"
EOF
```

**PowerShell:**
```powershell
@"

# Feature adicionada no Lab 4
def versao():
    return "v3 - CI/CD Pipeline completo!"
"@ | Add-Content app.py
```

Em seguida, em ambos os terminais:
```
git add app.py
git commit -m "feat: v3 - adiciona funcao versao"
git push
```

Acompanhe no console:
1. **Source** → link direto para o commit no CodeCommit
2. **Build** → "Details" para logs do CodeBuild em tempo real
3. **Approval** → pipeline pausa; email SNS enviado; clique em **Review → Approve**
4. **Deploy** → CodeDeploy executa o Blue/Green

---
## Parte 5 — Aprovação via CLI

```
# O token é enviado na notificação SNS — único por execução
aws codepipeline put-approval-result --pipeline-name demo-dva-pipeline-completo --stage-name Approval --action-name ManualApproval --result actionStatus=Approved,summary="LGTM - testado" --token "<TOKEN_DA_NOTIFICACAO>"
```

---
## Parte 6 — Notificações de Falha via EventBridge

Console CodePipeline → pipeline → **Settings** → **Notifications** → **Create notification rule**:

| Campo | Valor |
|---|---|
| Name | `pipeline-falha-alerta` |
| Events | Pipeline execution: Failed; Stage execution: Failed |
| Target | SNS topic `codepipeline-notifications` |

**Simular falha:** copie o conteúdo do arquivo `buildspec_broken.yml` desta pasta como `buildspec.yml` no repositório, faça push, verifique o email de falha, restaure o buildspec correto em seguida.

---
## Parte 7 — Rollback Manual

Via **Console CodePipeline:**
- Histórico de execuções → encontre a última execução bem-sucedida → **Release change**

Via **CodeDeploy:**
- Application → Deployment group → Deployments → versão anterior → **Redeploy**

---
## Pontos de Atenção

- Artefatos do pipeline são armazenados em S3 automático, criptografados com KMS
- O token de aprovação SNS é **único por execução** — não pode ser reutilizado
- Ações no mesmo estágio executam **em paralelo**; estágios diferentes executam em **série**
- Pipeline v2: suporta variáveis entre estágios (feature avançada)
- Timeout da aprovação manual: **7 dias** — após isso, a execução é cancelada

---
## Limpeza

```
# Deletar pipeline
aws codepipeline delete-pipeline --name demo-dva-pipeline-completo
```

Deletar tópico SNS:

**Bash:**
```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)
aws sns delete-topic --topic-arn "arn:aws:sns:$REGION:$ACCOUNT_ID:codepipeline-notifications"
```

**PowerShell:**
```powershell
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$REGION = aws configure get region
aws sns delete-topic --topic-arn "arn:aws:sns:$REGION:$ACCOUNT_ID:codepipeline-notifications"
```

```
# Deletar repositório, projeto build e application CodeDeploy
aws codecommit delete-repository --repository-name demo-dva-pipeline
aws codebuild delete-project --name demo-dva-build
aws codedeploy delete-application --application-name demo-webapp
```
