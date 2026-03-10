# Roteiro — Lab 5: AWS CodeArtifact e Rollback Automático

> **Compatibilidade de comandos**
> Os blocos de código abaixo indicam o terminal alvo (**Bash** ou **PowerShell**).
> Comandos sem variáveis (`aws`, `pip`, `twine`) funcionam diretamente em ambos os terminais — copie e cole sem adaptação.
> **Importante:** execute os blocos Bash ou PowerShell de uma determinada seção em uma única sessão de terminal para que as variáveis se mantenham visíveis entre os passos.
> - Linux / macOS / Git Bash → bloco `bash`
> - Windows PowerShell → bloco `powershell`

## Custos e Free Tier

| Serviço | Free Tier |
|---------|-----------|
| CodeArtifact | 2 GB storage + 100k requests/mês (primeiros 12 meses) |
| CloudWatch Alarms | 10 alarmes métricos/mês (permanente) |

> **Aviso:** Recursos na nuvem podem gerar custos mesmo dentro do Free Tier, pois ele tem limites mensais e pode ser esgotado. O CodeArtifact cobra por GB armazenado e por request após o Free Tier. Pacotes cacheados de PyPI/npm acumulam storage — execute o cleanup ao final da prática.

---
## Objetivo

**Parte A:** Criar domínio e repositório CodeArtifact, conectar ao pip, publicar um pacote interno e integrar com CodeBuild.

**Parte B:** Configurar rollback automático no CodeDeploy acionado por CloudWatch Alarm.

---
## PARTE A — AWS CodeArtifact

### A.1 — Criar Domínio e Repositórios

**Bash:**
```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
DOMAIN="minha-empresa"
REPO="python-packages"
REGION="sa-east-1"  # ajuste se necessário

aws codeartifact create-domain --domain $DOMAIN --region $REGION
aws codeartifact create-repository --domain $DOMAIN --repository $REPO --description "Repositório Python para demos DVA" --region $REGION
aws codeartifact create-repository --domain $DOMAIN --repository pypi-store --description "Cache PyPI público" --region $REGION
aws codeartifact associate-external-connection --domain $DOMAIN --repository pypi-store --external-connection public:pypi --region $REGION
aws codeartifact update-repository --domain $DOMAIN --repository $REPO --upstreams repositoryName=pypi-store --region $REGION
```

**PowerShell:**
```powershell
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$DOMAIN = "minha-empresa"
$REPO = "python-packages"
$REGION = "sa-east-1"  # ajuste se necessário

aws codeartifact create-domain --domain $DOMAIN --region $REGION
aws codeartifact create-repository --domain $DOMAIN --repository $REPO --description "Repositório Python para demos DVA" --region $REGION
aws codeartifact create-repository --domain $DOMAIN --repository pypi-store --description "Cache PyPI público" --region $REGION
aws codeartifact associate-external-connection --domain $DOMAIN --repository pypi-store --external-connection public:pypi --region $REGION
aws codeartifact update-repository --domain $DOMAIN --repository $REPO --upstreams repositoryName=pypi-store --region $REGION
```

---
### A.2 — Autenticar e Configurar pip

> Os comandos abaixo usam as variáveis definidas em A.1 — mantenha a mesma sessão de terminal.
> Os comandos `aws codeartifact login`, `pip` e `aws codeartifact list-packages` funcionam sem mudança em Bash e PowerShell.

```
aws codeartifact login --tool pip --domain $DOMAIN --domain-owner $ACCOUNT_ID --repository $REPO --region $REGION
pip config list
pip install requests
aws codeartifact list-packages --domain $DOMAIN --repository $REPO --format pypi --region $REGION
```

---
### A.3 — Publicar Pacote Interno

Os arquivos do pacote de demonstração estão na pasta `mypackage/` desta pasta. Use-os para publicar:

```
cd mypackage
pip install build twine --quiet
python -m build
```

Obtenha o endpoint e o token de autenticação:

**Bash:**
```bash
REPO_URL=$(aws codeartifact get-repository-endpoint --domain $DOMAIN --repository $REPO --format pypi --query repositoryEndpoint --output text --region $REGION)
TOKEN=$(aws codeartifact get-authorization-token --domain $DOMAIN --domain-owner $ACCOUNT_ID --query authorizationToken --output text --region $REGION)
twine upload --repository-url $REPO_URL -u aws -p $TOKEN dist/*
```

**PowerShell:**
```powershell
$REPO_URL = aws codeartifact get-repository-endpoint --domain $DOMAIN --repository $REPO --format pypi --query repositoryEndpoint --output text --region $REGION
$TOKEN = aws codeartifact get-authorization-token --domain $DOMAIN --domain-owner $ACCOUNT_ID --query authorizationToken --output text --region $REGION
twine upload --repository-url $REPO_URL -u aws -p $TOKEN dist/*
```

```
cd ..
```

Verifique no console CodeArtifact → repositório `python-packages` → aba **Packages**.

---
### A.4 — Integrar CodeBuild com CodeArtifact

O arquivo `buildspec_codeartifact.yml` desta pasta é o template do buildspec atualizado. Para usar no repositório:

1. Copie o conteúdo para o `buildspec.yml` do repositório `demo-dva-pipeline`
2. Ajuste `CODEARTIFACT_DOMAIN`, `CODEARTIFACT_REPO` e `AWS_ACCOUNT_ID`
3. Adicione as permissões abaixo à **service role do CodeBuild** (IAM):

```json
{
  "Effect": "Allow",
  "Action": [
    "codeartifact:GetAuthorizationToken",
    "codeartifact:GetRepositoryEndpoint",
    "codeartifact:ReadFromRepository"
  ],
  "Resource": "*"
}
```

4. Faça commit e push — o build deve autenticar no CodeArtifact e instalar o pacote `mypackage-demo`

---
## PARTE B — Rollback Automático com CloudWatch Alarm

### B.1 — Criar Alarme CloudWatch

**Bash:**
```bash
ALARM_NAME="demo-app-errors-alta"
aws cloudwatch put-metric-alarm --alarm-name "$ALARM_NAME" --alarm-description "Alarme de erros elevados - triggera rollback" --metric-name "ErrorRate" --namespace "Demo/Application" --statistic Average --period 60 --threshold 5 --comparison-operator GreaterThanThreshold --evaluation-periods 1 --region $REGION
```

**PowerShell:**
```powershell
$ALARM_NAME = "demo-app-errors-alta"
aws cloudwatch put-metric-alarm --alarm-name "$ALARM_NAME" --alarm-description "Alarme de erros elevados - triggera rollback" --metric-name "ErrorRate" --namespace "Demo/Application" --statistic Average --period 60 --threshold 5 --comparison-operator GreaterThanThreshold --evaluation-periods 1 --region $REGION
```

---
### B.2 — Configurar Rollback no Deployment Group

CodeDeploy → Application `demo-webapp` → Deployment group `demo-prod-bluegreen` → **Edit** ("Editar"):

Em **Advanced - Optional → Rollback configuration**:
- ✅ Roll back when a deployment fails
- ✅ Roll back when alarm thresholds are met
- **Alarms:** adicione `demo-app-errors-alta`

---
### B.3 — Simular Alarme e Observar Rollback

```
# Força alarme em estado ALARM (simula pico de erros pós-deploy)
aws cloudwatch set-alarm-state --alarm-name "$ALARM_NAME" --state-value ALARM --state-reason "Simulando erros elevados pós-deploy" --region $REGION
```

Com um deployment em andamento no CodeDeploy:
1. O alarme em estado ALARM é detectado
2. O CodeDeploy interrompe o deployment
3. Rollback automático é iniciado
4. Versão anterior é restaurada

Restaurar o alarme:
```
aws cloudwatch set-alarm-state --alarm-name "$ALARM_NAME" --state-value OK --state-reason "Erros normalizados" --region $REGION
```

### B.4 — Rollback Automático no CodePipeline (opcional)

Console CodePipeline → pipeline → **Edit** ("Editar") → estágio Deploy → editar ação → **Advanced** ("Avançado") → **Rollback trigger** ("Gatilho de rollback"): adicione o alarme `demo-app-errors-alta`.

O pipeline realizará rollback automático se o alarme disparar durante o deploy em produção.

---
## Pontos de Atenção

- `aws codeartifact login` é um wrapper que configura pip/npm automaticamente — mais prático que fazer manualmente
- Rollback por **alarme** monitora a saúde da aplicação *após* o deploy; rollback por **falha de deployment** monitora os lifecycle hooks *durante* o deploy — são mecanismos diferentes
- CodeArtifact cobra por GB armazenado — pacotes cacheados do PyPI acumulam rapidamente
- Cross-account: um domínio CodeArtifact central pode ser compartilhado entre múltiplas contas AWS via IAM role

---
## Limpeza

> Re-declare as variáveis caso esteja em uma nova sessão de terminal:
> - **Bash:** `DOMAIN="minha-empresa"`, `REPO="python-packages"`, `REGION="sa-east-1"`, `ALARM_NAME="demo-app-errors-alta"`
> - **PowerShell:** `$DOMAIN="minha-empresa"`, `$REPO="python-packages"`, `$REGION="sa-east-1"`, `$ALARM_NAME="demo-app-errors-alta"`

Os comandos abaixo funcionam em **Bash e PowerShell** (após as variáveis estarem definidas):

```
aws codeartifact delete-repository --domain $DOMAIN --repository $REPO --region $REGION
aws codeartifact delete-repository --domain $DOMAIN --repository pypi-store --region $REGION
aws codeartifact delete-domain --domain $DOMAIN --region $REGION
aws cloudwatch delete-alarms --alarm-names "$ALARM_NAME"
```
