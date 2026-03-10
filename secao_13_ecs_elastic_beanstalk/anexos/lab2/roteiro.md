# Lab 2 — Elastic Beanstalk: Deploy, Deployment Policies e .ebextensions

> **Compatibilidade de comandos CLI**
> Este roteiro apresenta blocos para **PowerShell** (Windows) e **Bash** (Linux/macOS/Git Bash/WSL).
> No PowerShell, o backtick `` ` `` é o caractere de continuação de linha; no Bash, use `\`.
> O EB CLI (`eb`) funciona da mesma forma em ambos os terminais.

---

> **Custos e Free Tier**
> O Elastic Beanstalk em si é **gratuito** — você paga pelos recursos que ele cria.
> Este lab usa instâncias **t3.micro** (750 h/mês Free Tier nos primeiros 12 meses).
> O Elastic Load Balancer custa ~$0,008/hora fora do Free Tier.
>
> ⚠️ **Aviso importante:** o ambiente Elastic Beanstalk (EC2 + ELB) gera custo enquanto ativo.
> Execute a etapa de limpeza ao concluir o lab.

---

## Objetivo

Fazer o deploy de uma aplicação Python no Elastic Beanstalk, explorar as
**deployment policies** (All at Once, Rolling, Immutable) e configurar o ambiente
usando `.ebextensions` — incluindo variáveis de ambiente e o padrão `leader_only`
para simular uma migration de banco de dados.

---

## Pré-requisitos

- Conta AWS com permissões em: `ElasticBeanstalk`, `EC2`, `IAM`, `S3`, `CloudFormation`
- AWS CLI instalada e configurada (`aws configure`)
- Python 3.x instalado (para criar e testar a app localmente)
- EB CLI instalado

### Instalar o EB CLI (se necessário)

```
pip install awsebcli
eb --version
```

> Funciona em Bash e PowerShell.

---

## Estrutura de Arquivos deste Lab

```
lab2/
├── roteiro.md              <- este arquivo
├── app.py                  <- aplicação Python (Flask)
├── requirements.txt        <- dependências Python
├── Procfile                <- instrução de inicialização para o Beanstalk
└── .ebextensions/
    ├── 01_env.config       <- configura variáveis de ambiente
    └── 02_commands.config  <- container_commands com leader_only
```

Os arquivos `app.py`, `requirements.txt`, `Procfile` e a pasta `.ebextensions`
compõem o pacote que será enviado ao Elastic Beanstalk.

---

## Parte 1 — Preparar e Testar a Aplicação Localmente

### 1.1 — Criar ambiente virtual Python e instalar dependências

**PowerShell (Windows):**
```powershell
# No diretório lab2/
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Bash (Linux/macOS/Git Bash/WSL):**
```bash
# No diretório lab2/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 1.2 — Testar localmente

```
python app.py
```

> No Linux/macOS use `python3 app.py` se necessário.

Abra o navegador em `http://localhost:5000` e verifique:
- `GET /` → mensagem de boas-vindas com variável de ambiente
- `GET /health` → `{"status": "ok"}` (usado pelo Beanstalk como health check)
- `GET /info` → informações do servidor

Pare o servidor com `Ctrl+C`.

---

## Parte 2 — Criar o Pacote de Deploy (ZIP)

O Elastic Beanstalk espera um arquivo ZIP com o código da aplicação.
O ZIP deve incluir `app.py`, `requirements.txt`, `Procfile` e a pasta `.ebextensions`.

**PowerShell (Windows):**
```powershell
# Sair do venv antes de zipar
deactivate

# Criar o ZIP do pacote (sem incluir a pasta venv/)
Compress-Archive `
  -Path app.py, requirements.txt, Procfile, .ebextensions `
  -DestinationPath deploy-v1.zip `
  -Force

Write-Host "Pacote criado: deploy-v1.zip"
Get-Item deploy-v1.zip | Select-Object Name, Length
```

**Bash (Linux/macOS/Git Bash/WSL):**
```bash
# Sair do venv antes de zipar
deactivate

# Criar o ZIP do pacote (sem incluir a pasta venv/)
zip deploy-v1.zip app.py requirements.txt Procfile -r .ebextensions

echo "Pacote criado: deploy-v1.zip"
ls -lh deploy-v1.zip
```

---

## Parte 3 — Criar a Aplicação e o Ambiente no Elastic Beanstalk

### Opção A — Via EB CLI (recomendada)

**PowerShell:**
```powershell
# Inicializar o projeto EB CLI no diretório lab2/
eb init lab-beanstalk-python `
  --platform "Python 3.11 running on 64bit Amazon Linux 2023" `
  --region us-east-1

# Criar o ambiente (pode levar 5-10 minutos)
eb create lab-env-producao `
  --instance-type t3.micro `
  --single `
  --timeout 20

# Acompanhar eventos em tempo real
eb events -f
```

**Bash:**
```bash
# Inicializar o projeto EB CLI no diretório lab2/
eb init lab-beanstalk-python \
  --platform "Python 3.11 running on 64bit Amazon Linux 2023" \
  --region us-east-1

# Criar o ambiente (pode levar 5-10 minutos)
eb create lab-env-producao \
  --instance-type t3.micro \
  --single \
  --timeout 20

# Acompanhar eventos em tempo real
eb events -f
```

> `--single` cria um ambiente sem Load Balancer (instância única).
> Remova `--single` para criar com Load Balancer e Auto Scaling, necessário para
> testar as deployment policies Rolling e Immutable.

### Opção B — Via AWS CLI

**PowerShell:**
```powershell
# Definir variáveis
$APP_NAME    = "lab-beanstalk-python"
$ENV_NAME    = "lab-env-producao"
$REGION      = "us-east-1"
$ACCOUNT_ID  = (aws sts get-caller-identity --query Account --output text)

# 1. Criar a aplicação
aws elasticbeanstalk create-application `
  --application-name $APP_NAME `
  --description "Lab Elastic Beanstalk - DVA-C02"

# 2. Criar bucket S3 para artefatos (se não existir)
$BUCKET = "eb-artifacts-$ACCOUNT_ID-$REGION"
aws s3 mb "s3://$BUCKET" --region $REGION

# 3. Fazer upload do ZIP
$VERSION_LABEL = "v1-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
aws s3 cp deploy-v1.zip "s3://$BUCKET/lab-beanstalk/$VERSION_LABEL.zip"

# 4. Registrar a Application Version
aws elasticbeanstalk create-application-version `
  --application-name $APP_NAME `
  --version-label $VERSION_LABEL `
  --source-bundle "S3Bucket=$BUCKET,S3Key=lab-beanstalk/$VERSION_LABEL.zip" `
  --auto-create-application

# 5. Criar o ambiente
aws elasticbeanstalk create-environment `
  --application-name $APP_NAME `
  --environment-name $ENV_NAME `
  --solution-stack-name "64bit Amazon Linux 2023 v4.0.0 running Python 3.11" `
  --version-label $VERSION_LABEL `
  --option-settings `
    Namespace=aws:autoscaling:launchconfiguration,OptionName=InstanceType,Value=t3.micro

Write-Host "Criando ambiente... Aguarde 5-10 minutos."

# 6. Aguardar o ambiente estar pronto
aws elasticbeanstalk wait environment-updated `
  --application-name $APP_NAME `
  --environment-names $ENV_NAME
```

**Bash:**
```bash
# Definir variáveis
APP_NAME="lab-beanstalk-python"
ENV_NAME="lab-env-producao"
REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# 1. Criar a aplicação
aws elasticbeanstalk create-application \
  --application-name $APP_NAME \
  --description "Lab Elastic Beanstalk - DVA-C02"

# 2. Criar bucket S3 para artefatos (se não existir)
BUCKET="eb-artifacts-$ACCOUNT_ID-$REGION"
aws s3 mb "s3://$BUCKET" --region $REGION

# 3. Fazer upload do ZIP
VERSION_LABEL="v1-$(date +%Y%m%d-%H%M%S)"
aws s3 cp deploy-v1.zip "s3://$BUCKET/lab-beanstalk/$VERSION_LABEL.zip"

# 4. Registrar a Application Version
aws elasticbeanstalk create-application-version \
  --application-name $APP_NAME \
  --version-label $VERSION_LABEL \
  --source-bundle "S3Bucket=$BUCKET,S3Key=lab-beanstalk/$VERSION_LABEL.zip" \
  --auto-create-application

# 5. Criar o ambiente
aws elasticbeanstalk create-environment \
  --application-name $APP_NAME \
  --environment-name $ENV_NAME \
  --solution-stack-name "64bit Amazon Linux 2023 v4.0.0 running Python 3.11" \
  --version-label $VERSION_LABEL \
  --option-settings \
    Namespace=aws:autoscaling:launchconfiguration,OptionName=InstanceType,Value=t3.micro

echo "Criando ambiente... Aguarde 5-10 minutos."

# 6. Aguardar o ambiente estar pronto
aws elasticbeanstalk wait environment-updated \
  --application-name $APP_NAME \
  --environment-names $ENV_NAME
```

### Verificar o status e obter a URL

**PowerShell:**
```powershell
aws elasticbeanstalk describe-environments `
  --application-name $APP_NAME `
  --environment-names $ENV_NAME `
  --query "Environments[0].{Nome:EnvironmentName,Status:Status,Saude:Health,URL:CNAME}" `
  --output table
```

**Bash:**
```bash
aws elasticbeanstalk describe-environments \
  --application-name $APP_NAME \
  --environment-names $ENV_NAME \
  --query "Environments[0].{Nome:EnvironmentName,Status:Status,Saude:Health,URL:CNAME}" \
  --output table
```

Acesse a URL exibida no campo `URL` no navegador.

---

## Parte 4 — Explorar as Deployment Policies

Para esta parte, você precisa de um ambiente **com Load Balancer** (sem `--single`).
Se criou com `--single`, recrie o ambiente sem essa flag.

### 4.1 — Criar versão 2 da aplicação

Edite o arquivo `app.py` e altere a variável `APP_VERSION` de `"1.0"` para `"2.0"`.

**PowerShell:**
```powershell
# Re-criar o ZIP com a versão atualizada
Compress-Archive `
  -Path app.py, requirements.txt, Procfile, .ebextensions `
  -DestinationPath deploy-v2.zip `
  -Force
```

**Bash:**
```bash
# Re-criar o ZIP com a versão atualizada
zip deploy-v2.zip app.py requirements.txt Procfile -r .ebextensions
```

### 4.2 — Deploy com All at Once

All at Once atualiza todas as instâncias simultaneamente — **gera downtime**.
Use apenas em desenvolvimento.

```
# Via EB CLI
eb deploy lab-env-producao --label v2-all-at-once
```

Via AWS CLI — alterar a política antes do deploy:

**PowerShell:**
```powershell
aws elasticbeanstalk update-environment `
  --application-name $APP_NAME `
  --environment-name $ENV_NAME `
  --option-settings `
    "Namespace=aws:elasticbeanstalk:command,OptionName=DeploymentPolicy,Value=AllAtOnce"
```

**Bash:**
```bash
aws elasticbeanstalk update-environment \
  --application-name $APP_NAME \
  --environment-name $ENV_NAME \
  --option-settings \
    "Namespace=aws:elasticbeanstalk:command,OptionName=DeploymentPolicy,Value=AllAtOnce"
```

### 4.3 — Deploy com Rolling

Rolling atualiza um batch por vez, mantendo o restante em serviço.
Capacidade reduzida durante o deploy, mas **sem downtime**.

**PowerShell:**
```powershell
aws elasticbeanstalk update-environment `
  --application-name $APP_NAME `
  --environment-name $ENV_NAME `
  --option-settings `
    "Namespace=aws:elasticbeanstalk:command,OptionName=DeploymentPolicy,Value=Rolling" `
    "Namespace=aws:elasticbeanstalk:command,OptionName=BatchSizeType,Value=Percentage" `
    "Namespace=aws:elasticbeanstalk:command,OptionName=BatchSize,Value=50"
```

**Bash:**
```bash
aws elasticbeanstalk update-environment \
  --application-name $APP_NAME \
  --environment-name $ENV_NAME \
  --option-settings \
    "Namespace=aws:elasticbeanstalk:command,OptionName=DeploymentPolicy,Value=Rolling" \
    "Namespace=aws:elasticbeanstalk:command,OptionName=BatchSizeType,Value=Percentage" \
    "Namespace=aws:elasticbeanstalk:command,OptionName=BatchSize,Value=50"
```

> `BatchSize=50` atualiza 50% das instâncias por vez.

### 4.4 — Deploy com Immutable

Immutable cria um novo Auto Scaling Group com instâncias na nova versão.
Após validação, migra o tráfego e termina as instâncias antigas.
**Rollback instantâneo** — sem downtime — custo mais alto (dobra instâncias temporariamente).

**PowerShell:**
```powershell
aws elasticbeanstalk update-environment `
  --application-name $APP_NAME `
  --environment-name $ENV_NAME `
  --option-settings `
    "Namespace=aws:elasticbeanstalk:command,OptionName=DeploymentPolicy,Value=Immutable"
```

**Bash:**
```bash
aws elasticbeanstalk update-environment \
  --application-name $APP_NAME \
  --environment-name $ENV_NAME \
  --option-settings \
    "Namespace=aws:elasticbeanstalk:command,OptionName=DeploymentPolicy,Value=Immutable"
```

### Comparativo visual (consulte durante o deploy)

| Política           | Downtime | Capacidade | Rollback | Custo extra |
|--------------------|----------|------------|----------|-------------|
| All at Once        | Sim      | Zero       | Re-deploy| Nenhum      |
| Rolling            | Não      | Reduzida   | Re-deploy| Nenhum      |
| Rolling + Batch    | Não      | Total      | Re-deploy| Baixo       |
| Immutable          | Não      | Total      | Instantâneo | Alto     |

---

## Parte 5 — Inspecionar o .ebextensions em Ação

### 5.1 — Verificar variáveis de ambiente configuradas

Acesse via console:
**Elastic Beanstalk → Environments → lab-env-producao → Configuration → Software → Environment properties**

Ou via endpoint da aplicação:

**PowerShell:**
```powershell
$URL = (aws elasticbeanstalk describe-environments `
  --application-name $APP_NAME `
  --environment-names $ENV_NAME `
  --query "Environments[0].CNAME" `
  --output text)

Invoke-WebRequest -Uri "http://$URL/info" | Select-Object -ExpandProperty Content
```

**Bash:**
```bash
URL=$(aws elasticbeanstalk describe-environments \
  --application-name $APP_NAME \
  --environment-names $ENV_NAME \
  --query "Environments[0].CNAME" \
  --output text)

curl "http://$URL/info"
```

### 5.2 — Verificar os logs do container_command com leader_only

Acesse os logs via EB CLI:
```
eb logs lab-env-producao
```

Ou via console: **Elastic Beanstalk → Environments → lab-env-producao → Logs → Request Logs → Last 100 Lines**

Procure a linha:
```
[MIGRATION] Este comando roda apenas na instância líder - simulando migration de banco
```

> Este log confirma que `container_commands` com `leader_only: true` rodou
> em apenas **uma** instância do cluster, garantindo que a migration não
> seja executada múltiplas vezes.

---

## Parte 6 — Blue/Green Deploy (Swap de URLs)

O Blue/Green no Beanstalk **não é uma deployment policy nativa** — é feito via Swap de URLs.

### 6.1 — Criar ambiente Green

**PowerShell:**
```powershell
# Via EB CLI — criar um segundo ambiente
eb create lab-env-green `
  --instance-type t3.micro `
  --timeout 20

# Fazer o deploy da v2 no Green
eb deploy lab-env-green
```

**Bash:**
```bash
# Via EB CLI — criar um segundo ambiente
eb create lab-env-green \
  --instance-type t3.micro \
  --timeout 20

# Fazer o deploy da v2 no Green
eb deploy lab-env-green
```

### 6.2 — Testar o ambiente Green

**PowerShell:**
```powershell
$GREEN_URL = (aws elasticbeanstalk describe-environments `
  --application-name $APP_NAME `
  --environment-names "lab-env-green" `
  --query "Environments[0].CNAME" `
  --output text)

Invoke-WebRequest -Uri "http://$GREEN_URL" | Select-Object -ExpandProperty Content
```

**Bash:**
```bash
GREEN_URL=$(aws elasticbeanstalk describe-environments \
  --application-name $APP_NAME \
  --environment-names "lab-env-green" \
  --query "Environments[0].CNAME" \
  --output text)

curl "http://$GREEN_URL"
```

### 6.3 — Trocar as URLs (Swap)

**PowerShell:**
```powershell
# Swap de URLs entre produção (Blue) e Green
aws elasticbeanstalk swap-environment-cnames `
  --source-environment-name $ENV_NAME `
  --destination-environment-name "lab-env-green"

Write-Host "Swap realizado! O tráfego agora aponta para o ambiente Green."
Write-Host "Para reverter, execute o swap novamente."
```

**Bash:**
```bash
# Swap de URLs entre produção (Blue) e Green
aws elasticbeanstalk swap-environment-cnames \
  --source-environment-name $ENV_NAME \
  --destination-environment-name "lab-env-green"

echo "Swap realizado! O tráfego agora aponta para o ambiente Green."
echo "Para reverter, execute o swap novamente."
```

> O swap é **instantâneo** no DNS. Ambos os ambientes continuam rodando,
> permitindo validação antes e rollback imediato se necessário.

---

## Pontos de Verificação

- O arquivo `Procfile` diz ao Beanstalk como iniciar a aplicação (`web: gunicorn app:app`)
- O `.ebextensions` é processado em **ordem alfabética** — use prefixos `01_`, `02_`
- `container_commands` roda **depois** do deploy mas **antes** do start da aplicação
- `leader_only: true` executa o comando em **uma única instância** do cluster (líder)
- `option_settings` no `.ebextensions` substitui configurações do console
- Blue/Green no Beanstalk usa `swap-environment-cnames` — não é deployment policy nativa
- O Beanstalk é **gratuito** — você paga pelos recursos (EC2, ELB, S3)

---

## Limpeza

```
# Via EB CLI (funciona em Bash e PowerShell)
eb terminate lab-env-producao --force
eb terminate lab-env-green --force   # se criou o Green
```

Aguardar encerramento:

**PowerShell:**
```powershell
Write-Host "Aguardando encerramento dos ambientes (pode levar 5-10 minutos)..."
Start-Sleep -Seconds 30
```

**Bash:**
```bash
echo "Aguardando encerramento dos ambientes (pode levar 5-10 minutos)..."
sleep 30
```

Deletar a aplicação via AWS CLI:

**PowerShell:**
```powershell
aws elasticbeanstalk delete-application `
  --application-name $APP_NAME `
  --terminate-env-by-force
```

**Bash:**
```bash
aws elasticbeanstalk delete-application \
  --application-name $APP_NAME \
  --terminate-env-by-force
```

Limpar o bucket S3 de artefatos (opcional):

```
aws s3 rm "s3://$BUCKET/lab-beanstalk/" --recursive
```

> `aws s3 rm` funciona em Bash e PowerShell. Use `$BUCKET` (PS) ou `$BUCKET` (Bash) dependendo do terminal.
