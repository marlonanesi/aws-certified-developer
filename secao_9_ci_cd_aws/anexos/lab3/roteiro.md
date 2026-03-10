# Roteiro — Lab 3: AWS CodeDeploy — Deploy Blue/Green

> **Compatibilidade de comandos**
> Os blocos de código abaixo indicam o terminal alvo (**Bash** ou **PowerShell**).
> Comandos sem variáveis (`aws`, `git`, `curl`) funcionam diretamente em ambos os terminais — copie e cole sem adaptação.
> - Linux / macOS / Git Bash → bloco `bash`
> - Windows PowerShell → bloco `powershell`

## Custos e Free Tier

| Serviço | Free Tier |
|---------|-----------|
| CodeDeploy (EC2/On-premises) | Gratuito |
| EC2 | 750 horas/mês `t2.micro` ou `t3.micro` (primeiros 12 meses) |
| Application Load Balancer | **Sem Free Tier** — ~USD 0,008/hora + LCUs |
| S3 | 5 GB + 20k GET + 2k PUT (primeiros 12 meses) |

> **Aviso:** Recursos na nuvem podem gerar custos mesmo dentro do Free Tier, pois ele tem limites mensais e pode ser esgotado. Este lab cria um **ALB** que **não tem Free Tier** e um conjunto de instâncias EC2. Execute o cleanup imediatamente ao concluir a prática para evitar cobranças.

---
## Pré-requisito

Labs 1 e 2 concluídos. Repositório `demo-dva-pipeline` com `app.py` e `buildspec.yml`.

---
## Objetivo

Configurar o CodeDeploy com estratégia Blue/Green em instâncias EC2, usando ALB para transferência de tráfego. Ao final, simular falha e observar o rollback automático.

---
## Arquitetura

```
git push → CodeCommit
                ↓
           CodeDeploy Blue/Green
           /                   Target Group Blue (v1)   Target Group Green (v2)
           \                   /
        Application Load Balancer
                ↓
            Usuários
```

---
## Parte 1 — Preparar Infraestrutura EC2

### Passo 0 — Criar o IAM Instance Profile para as instâncias EC2

O CodeDeploy Agent rodando nas instâncias precisa de permissão para se comunicar com o serviço CodeDeploy e baixar artefatos do S3. Isso é feito via **IAM Instance Profile** (uma role EC2 com as políticas necessárias).

**IAM → Roles → Create role:**

| Campo | Valor |
|---|---|
| Trusted entity type | **AWS service** |
| Use case | **EC2** |

Clique em **Next** e adicione as políticas:

| Política | Para que serve |
|---|---|
| `AmazonEC2RoleforAWSCodeDeploy` | permite ao agente baixar revisões do S3 e comunicar status ao CodeDeploy |
| `AmazonSSMManagedInstanceCore` | permite acesso via Session Manager (opcional, mas recomendado para debug sem SSH) |

**Next** → Nome da role: `EC2InstanceProfile-CodeDeploy` → **Create role**.

> O **Instance Profile** é criado automaticamente pelo console com o mesmo nome da role — não é necessário criar separadamente. Ao lançar a instância EC2, selecione essa role no campo **IAM instance profile**.

---
### Passo 1 — Criar os Security Groups

Você precisa de **dois Security Groups** criados nesta ordem (o SG das instâncias referencia o SG do ALB):

**SG 1 — ALB (`alb-sg`):**

EC2 → Security Groups → **Create security group**:

| Campo | Valor |
|---|---|
| Name | `alb-sg` |
| Description | `Allow HTTP from internet` |
| VPC | mesma VPC das instâncias EC2 |
| Inbound rule | Type: HTTP, Port: 80, Source: `0.0.0.0/0` |
| Outbound rule | All traffic (padrão) |

> Este SG permite que qualquer usuário da internet acesse o ALB na porta 80.

**SG 2 — Instâncias EC2 (`ec2-sg`):**

Crie um segundo Security Group:

| Campo | Valor |
|---|---|
| Name | `ec2-sg` |
| Description | `Allow traffic from ALB only` |
| VPC | mesma VPC |
| Inbound rule | Type: Custom TCP, Port: **8080**, Source: **`alb-sg`** (selecione o SG, não um CIDR) |
| Outbound rule | All traffic (padrão) |

> Source = `alb-sg` significa "aceite tráfego apenas de recursos que pertencem a esse SG" — ou seja, somente o ALB pode acessar a porta 8080 das instâncias. Nunca use `0.0.0.0/0` aqui.

---
### Passo 2 — Criar o Launch Template (modelo de instância)

O Launch Template define a configuração que o Auto Scaling Group usará para criar as instâncias — tanto Blue quanto Green usarão o mesmo template.

EC2 → **Launch Templates** → **Create launch template**:

| Campo | Valor |
|---|---|
| Launch template name | `lt-codedeploy-blue-green` |
| Auto Scaling guidance | ✅ marque "Provide guidance..." |
| AMI | Amazon Linux 2023 (busque em Quick Start) |
| Instance type | `t2.micro` |
| Key pair | selecione um existente ou "Proceed without" |
| Security groups | `ec2-sg` (criado no Passo 1) |
| IAM instance profile | `EC2InstanceProfile-CodeDeploy` |
| User data | conteúdo do arquivo `user_data.sh` desta pasta |

Clique em **Create launch template**.

> O Launch Template **não cria instâncias** — é apenas o blueprint. O ASG criado no Passo 5 é quem lança as instâncias usando este template.

---
### Passo 3 — Criar os Target Groups

> **Por que 2 target groups?** Blue/Green exige dois ambientes paralelos. O ALB usa o **tg-blue** inicialmente (produção atual). No deploy, o CodeDeploy registra as instâncias Green no **tg-green** e depois muda o listener do ALB para apontar para tg-green. Os TGs precisam existir antes do ASG para que o grupo possa ser anexado ao `tg-blue` durante a criação.

EC2 → **Target Groups** → **Create target group**:

**Target Group Blue (produção atual):**

| Campo | Valor |
|---|---|
| Target type | Instances |
| Name | `tg-blue` |
| Protocol / Port | HTTP / 8080 |
| Health check path | `/` |
| VPC | mesma VPC das instâncias EC2 |

> As instâncias Blue serão registradas automaticamente no `tg-blue` pelo Auto Scaling Group — não é necessário registrá-las manualmente.

**Target Group Green (inicialmente vazio):**

Repita o processo com as mesmas configurações, mas nome `tg-green`. **Não registre instâncias** — o CodeDeploy faz isso automaticamente durante o deploy.

---
### Passo 4 — Criar o Application Load Balancer

EC2 → Load Balancers → **Create load balancer** → **Application Load Balancer**:

| Campo | Valor |
|---|---|
| Name | `demo-codedeploy-alb` |
| Scheme | Internet-facing |
| Subnets | selecione pelo menos 2 AZs |
| Security group | **`alb-sg`** (criado no Passo 1) |
| Listener | HTTP : 80 → **Default action**: encaminhar para `tg-blue` |

Após criar o ALB, anote o **DNS name** — será usado para testar na Parte 4.

---
### Passo 5 — Criar o Auto Scaling Group (ambiente Blue)

O ASG é o mecanismo que o CodeDeploy usa no Blue/Green para clonar o ambiente automaticamente. O ASG Blue representa a produção atual; o CodeDeploy criará um ASG Green na hora do deploy.

EC2 → **Auto Scaling Groups** → **Create Auto Scaling group**:

**Step 1 — Choose launch template:**

| Campo | Valor |
|---|---|
| Auto Scaling group name | `asg-blue-codedeploy` |
| Launch template | `lt-codedeploy-blue-green` |

**Step 2 — Choose instance launch options:**

| Campo | Valor |
|---|---|
| VPC | mesma VPC dos SGs |
| Availability Zones | selecione pelo menos 2 AZs |

**Step 3 — Configure advanced options:**

| Campo | Valor |
|---|---|
| Load balancing | **Attach to an existing load balancer** |
| ↳ Choose from your load balancer target groups | `tg-blue` |
| Health check type | EC2 |

**Step 4 — Configure group size and scaling:**

| Campo | Valor |
|---|---|
| Desired capacity | `2` |
| Minimum capacity | `2` |
| Maximum capacity | `2` |
| Automatic scaling | **No scaling policies** |

**Step 5 — Add tags:**

| Chave | Valor | Propagar para instâncias |
|---|---|---|
| `Name` | `codedeploy-webapp` | ✅ Sim |
| `Environment` | `blue` | ✅ Sim |

Clique em **Create Auto Scaling group**.

> **Por que não usar `blue-instance` como nome?** O CodeDeploy clona o ASG Blue para criar o ASG Green, herdando todas as tags inclusive o `Name`. Isso resultaria em instâncias Green chamadas `blue-instance`, o que é confuso. Usando um nome neutro como `codedeploy-webapp` ambos os ambientes ficam com nome coerente. O que diferencia Blue de Green é a tag `Environment` e o ASG ao qual pertencem.

> Aguarde as 2 instâncias ficarem `InService` no ASG antes de prosseguir — verifique em EC2 → Auto Scaling Groups → `asg-blue-codedeploy` → aba **Instance management**.

> O `tg-green` criado no Passo 3 deve permanecer **vazio** — o CodeDeploy registrará as instâncias Green nele automaticamente durante o deploy.

---
## Parte 2 — Preparar o Artefato de Deploy

Neste lab o CodeDeploy opera de forma **independente do CodePipeline** — ele precisa de um arquivo `.zip` (chamado de *revisão*) hospedado no S3 como fonte do deploy. O fluxo desta parte é:

1. **Push no CodeCommit** → mantém o histórico de versão dos arquivos
2. **Upload no S3** → cria a *revisão* que o CodeDeploy vai baixar e executar nas instâncias

> O `appspec.yml` **obrigatoriamente** precisa estar na raiz do `.zip` — o CodeDeploy o usa como manifesto para executar os lifecycle hooks.

**Passo 1 — Atualizar o repositório:**

Copie os arquivos `app.py`, `appspec.yml` e a pasta `scripts/` desta pasta para o repositório `demo-dva-pipeline`:

```
cd demo-dva-pipeline
# copie os arquivos desta pasta (app.py, appspec.yml, scripts/)
git add .
git commit -m "feat: v2 - add appspec.yml and deployment scripts"
git push
```

**Passo 2 — Criar o bucket S3 e fazer upload da revisão:**

Crie um bucket dedicado para os artefatos do CodeDeploy e faça upload do `.zip` que será usado na Parte 5:

**Bash:**
```bash
BUCKET="codedeploy-artifacts-$(aws sts get-caller-identity --query Account --output text)"
aws s3 mb s3://$BUCKET

zip -r deploy-package.zip app.py appspec.yml scripts/
aws s3 cp deploy-package.zip s3://$BUCKET/releases/v2/deploy-package.zip
```

**PowerShell:**
```powershell
$BUCKET = "codedeploy-artifacts-$(aws sts get-caller-identity --query Account --output text)"
aws s3 mb s3://$BUCKET

Compress-Archive -Path app.py, appspec.yml, scripts -DestinationPath deploy-package.zip -Force
aws s3 cp deploy-package.zip s3://$BUCKET/releases/v2/deploy-package.zip
```

---
## Parte 3 — Configurar CodeDeploy

### Criar Application

CodeDeploy → **Applications** → **Create application** ("Criar aplicação"):
- Name: `demo-webapp`
- Compute platform: `EC2/On-premises`

### Passo 0 — Criar a IAM Role do CodeDeploy (`AWSCodeDeployRole`)

O CodeDeploy precisa de uma role para gerenciar EC2, ALB e Auto Scaling em seu nome.

**IAM → Roles → Create role:**

| Campo | Valor |
|---|---|
| Trusted entity type | **AWS service** |
| Use case | **CodeDeploy** (role for EC2/On-premises) |

> Ao escolher "CodeDeploy" como Use case, a política `AWSCodeDeployRole` já é adicionada automaticamente.

**Next** → Nome da role: `AWSCodeDeployRole` → **Create role**.

---

#### ⚠️ Por que a managed policy `AWSCodeDeployRole` não é suficiente para Blue/Green com ASG

A managed policy AWS cobre operações básicas de deploy em EC2, mas **não cobre tudo** que o CodeDeploy precisa para o modo Blue/Green com Auto Scaling Group. Ao tentar executar o deploy, você receberá o erro:

> *"The IAM role does not give you permission to perform operations in the following AWS service: AmazonAutoScaling"*

**O que acontece internamente (o que descobrimos via CloudTrail):**

Quando o deploy inicia, o CodeDeploy assume a `AWSCodeDeployRole` e tenta:
1. Chamar `autoscaling:CreateAutoScalingGroup` para criar o ASG Green (clone do Blue)
2. Passar um **Launch Template** para esse novo ASG
3. Aguardar o Auto Scaling lançar as instâncias EC2 usando o Launch Template

O passo 3 exige `ec2:RunInstances` — sem ela, o Auto Scaling aceita o pedido de criar o ASG mas não consegue lançar as instâncias, retornando `AccessDenied: An unknown error occurred`. Além disso, o CodeDeploy também precisa de `iam:CreateServiceLinkedRole` para o caso de o service-linked role do Auto Scaling ainda não existir na conta.

**A solução é adicionar uma inline policy complementar à role:**

```powershell
aws iam put-role-policy `
  --role-name AWSCodeDeployRole `
  --policy-name CodeDeployAutoScalingBlueGreen `
  --policy-document file://C:\cursos\aws_developer_associate\secao_9_ci_cd_aws\anexos\lab3\codedeploy-autoscaling-policy.json
```

O arquivo `codedeploy-autoscaling-policy.json` (já na pasta do lab) contém:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "autoscaling:CreateAutoScalingGroup",
        "autoscaling:UpdateAutoScalingGroup",
        "autoscaling:DeleteAutoScalingGroup",
        "autoscaling:DescribeAutoScalingGroups",
        "autoscaling:DescribeScalingActivities",
        "autoscaling:CreateOrUpdateTags",
        "autoscaling:SuspendProcesses",
        "autoscaling:ResumeProcesses",
        "autoscaling:AttachLoadBalancerTargetGroups",
        "autoscaling:DetachLoadBalancerTargetGroups",
        "autoscaling:TerminateInstanceInAutoScalingGroup",
        "autoscaling:PutLifecycleHook",
        "autoscaling:DeleteLifecycleHook",
        "autoscaling:CompleteLifecycleAction",
        "autoscaling:RecordLifecycleActionHeartbeat",
        "ec2:DescribeLaunchTemplates",
        "ec2:DescribeLaunchTemplateVersions",
        "ec2:RunInstances",
        "ec2:CreateTags",
        "iam:PassRole",
        "iam:CreateServiceLinkedRole",
        "iam:GetInstanceProfile"
      ],
      "Resource": "*"
    }
  ]
}
```

> **Boas práticas (DVA-C02):** nunca use `autoscaling:*` ou wildcards desnecessários em roles de serviço. O princípio do mínimo privilégio é cobrado no exame — conceda exatamente as actions necessárias. Esta policy lista apenas as actions que o CodeDeploy efetivamente chama durante um deploy Blue/Green com ASG.

**Para verificar se as permissões estão corretas antes de executar o deploy:**

```powershell
aws iam simulate-principal-policy `
  --policy-source-arn arn:aws:iam::SEU_ACCOUNT_ID:role/AWSCodeDeployRole `
  --action-names "autoscaling:CreateAutoScalingGroup" "ec2:RunInstances" "iam:CreateServiceLinkedRole" `
  --query "EvaluationResults[].{Action:EvalActionName,Decision:EvalDecision}" `
  --output table
```

Todas as actions devem retornar `allowed`. Se alguma retornar `implicitDeny`, a inline policy não foi aplicada ainda.

> **Lição:** a AWS divide as permissões do CodeDeploy em múltiplas camadas — a managed policy cobre o protocolo de deploy (lifecycle hooks, health checks), mas a criação de infraestrutura nova (ASGs, instâncias EC2 via Launch Template) exige permissões adicionais que só fazem sentido no modo Blue/Green com ASG. Em produção, o ideal é revisar essas permissões com o princípio do mínimo privilégio necessário.

---
### Criar Deployment Group (Blue/Green com ASG)

> **Como o CodeDeploy sabe alternar com ASG?** Você aponta o Deployment Group para o ASG Blue (`asg-blue-codedeploy`). No deploy, o CodeDeploy: (1) clona o ASG Blue criando um ASG Green com o mesmo Launch Template; (2) instala a nova versão nas instâncias Green; (3) atualiza o listener do ALB para apontar para `tg-green`; (4) encerra o ASG Blue. O rollback reverte o listener para `tg-blue`.

CodeDeploy → Application `demo-webapp` → **Create deployment group** ("Criar grupo de implantação"):

| Seção / Campo (PT-BR) | Valor | Por que |
|---|---|---|
| **Nome do grupo de implantação** | `demo-prod-bluegreen` | — |
| **Função de serviço** | `AWSCodeDeployRole` | permissão para gerenciar EC2, ALB e ASG |
| **Tipo de implantação** | **Azul/verde** | dois ambientes paralelos com troca de tráfego |
| **Configuração do ambiente** | **Copiar automaticamente o grupo de Auto Scaling do Amazon EC2** | o CodeDeploy clona o ASG Blue para criar o Green automaticamente |
| ↳ Auto Scaling group | `asg-blue-codedeploy` | o ASG Blue criado na Parte 1 |
| **Redirecionamento do tráfego** | **Redirecionar o tráfego imediatamente** | muda o listener assim que os hooks passam |
| **Instâncias originais** | ✅ **Encerrar as instâncias originais** | dias: `0`, horas: `0`, minutos: `5` — encerra o ASG Blue após o Green estar ativo |
| **Configuração de implantação** | `CodeDeployDefault.AllAtOnce` | implanta em todas as instâncias de uma vez |
| **Habilitar balanceamento de carga** | ✅ marcado (fixo — não é possível desmarcar em Blue/Green com ASG) | o ALB é obrigatório para o CodeDeploy alternar o tráfego entre Blue e Green |
| ↳ **Tipo de balanceador de carga** | **Application Load Balancer ou Network Load Balancer** | selecione esta opção (não "Classic Load Balancer") |
| ↳ Load balancer | `demo-codedeploy-alb` | ALB criado na Parte 3 |
| ↳ Grupos de destino (checklist) | ✅ `tg-blue` e ✅ `tg-green` | marque **os dois** — o CodeDeploy identifica automaticamente qual é produção (aquele com instâncias registradas = `tg-blue`) e qual é substituição (vazio = `tg-green`) |
| **Reversões** | ✅ **Habilitar reversões de implantação para esse grupo de implantação** | o padrão é "Desativar reversões" — clique aqui para trocar |
| ↳ opção | ✅ **Reverter quando uma implantação falhar** | se algum hook falhar, o listener volta para `tg-blue` |

---
## Parte 4 — Executar o Deploy

### Passo 0 — Verificar pré-requisitos antes de criar o deployment

Antes de criar a implantação, confirme que as instâncias estão com o tag correto e com o agente rodando. Erros aqui causam o erro `no instances were found`.

**Verificar tags nas instâncias (deve retornar as 2 instâncias Blue):**

```powershell
aws ec2 describe-instances `
  --filters "Name=tag:Environment,Values=blue" "Name=instance-state-name,Values=running" `
  --query "Reservations[].Instances[].{ID:InstanceId,State:State.Name,Tags:Tags}" `
  --output table
```

> Se retornar vazio: vá ao console EC2 → selecione cada instância → aba **Tags** → confirme que existe `Environment` = `blue` (com esse exato capitalização). Se não existir, clique em **Manage tags** e adicione.

**Verificar se o CodeDeploy Agent está rodando (via Session Manager ou SSH em cada instância):**

```bash
sudo systemctl status codedeploy-agent
```

> Deve mostrar `active (running)`. Se estiver parado:
> ```bash
> sudo systemctl start codedeploy-agent
> sudo systemctl enable codedeploy-agent
> ```
> Se o serviço não existir, o User Data não executou — verifique os logs: `cat /var/log/cloud-init-output.log`

---
### Passo 1 — Criar o deployment

CodeDeploy → Applications → `demo-webapp` → **Create deployment** ("Criar implantação"):

| Campo (PT-BR) | Valor | Observação |
|---|---|---|
| **Aplicativo** | `demo-webapp` | preenchido automaticamente |
| **Grupo de implantação** | `demo-prod-bluegreen` | selecione na lista |
| **Tipo de revisão** | **Meu aplicativo está armazenado no Amazon S3** | — |
| **Local de revisão** | `s3://codedeploy-artifacts-<account-id>/releases/v2/deploy-package.zip` | substitua `<account-id>` pelo seu |
| **Tipo de arquivo de revisão** | `.zip` | selecionado automaticamente ao digitar a URL |
| **Descrição da implantação** | *(deixar em branco)* | opcional |
| **Opções de conteúdo** | **Substituir o conteúdo** | evita falha caso o arquivo já exista na instância de uma implantação anterior |

> **Configuração do ambiente:** com ASG essa seção não precisa ser preenchida — o CodeDeploy identifica o ambiente Blue pelo próprio ASG configurado no Deployment Group e clona-o automaticamente para o Green.

> **Label não traduzido no console:** você pode ver `createDeploymentGroup.formSection.managedHookRole.label` — é um bug de internacionalização do console; ignore.

Clique em **Create deployment** e acompanhe as fases:
1. **Provisioning** — provisionando instâncias Green
2. **Deploying** — executando lifecycle hooks (`ApplicationStop`, `AfterInstall`, `ValidateService`)
3. **Rerouting** — ALB transfere tráfego do Blue para o Green
4. **Terminating** — instâncias Blue encerradas após 5 minutos

---
### Passo 2 — Verificar o resultado do deploy

Quando o deployment mostrar **"Com êxito"**, faça as verificações abaixo para confirmar que as instâncias Green estão servindo a v2.

**1. Testar pelo ALB (verificação principal — simula o usuário real):**

```powershell
$ALB_DNS = aws elbv2 describe-load-balancers --names demo-codedeploy-alb --query 'LoadBalancers[0].DNSName' --output text
curl "http://$ALB_DNS"
# Esperado: "V2 - Green Environment" (ou o conteúdo definido no app.py v2)
```

**2. Confirmar quais instâncias estão no `tg-green` (deve ter 2) e `tg-blue` (deve estar vazio):**

```powershell
# Instâncias no tg-green (Green — produção após deploy)
aws elbv2 describe-target-health --target-group-arn $(
  aws elbv2 describe-target-groups --names tg-green --query 'TargetGroups[0].TargetGroupArn' --output text
) --query "TargetHealthDescriptions[].{ID:Target.Id,Port:Target.Port,State:TargetHealth.State}" --output table

# Instâncias no tg-blue (deve estar vazio após Etapa 4 concluída)
aws elbv2 describe-target-health --target-group-arn $(
  aws elbv2 describe-target-groups --names tg-blue --query 'TargetGroups[0].TargetGroupArn' --output text
) --query "TargetHealthDescriptions[].{ID:Target.Id,Port:Target.Port,State:TargetHealth.State}" --output table
```

**3. Confirmar a versão do app diretamente em uma instância Green (via Session Manager):**

```bash
# No terminal Session Manager de uma das instâncias Green:
curl http://localhost:8080
# Esperado: "V2 - Green Environment"

# Confirmar o arquivo no disco:
cat /var/www/app/index.html
```

> **Por que as instâncias Green se chamam `codedeploy-webapp` e não `green-instance`?** O CodeDeploy clona o ASG Blue herdando as tags — por isso usamos um nome neutro. O que identifica o ambiente é o ASG ao qual a instância pertence (visível em EC2 → Instances → aba **Tags** → `aws:autoscaling:groupName`).

---
## Parte 5 — Simular Falha e Rollback Automático

O objetivo é forçar uma falha no hook `ValidateService` para observar o rollback automático. São dois passos: (1) criar e subir um `.zip` com o script quebrado; (2) criar um novo deployment apontando para ele.

**Passo 1 — Criar o pacote com falha e subir ao S3:**

**Bash:**
```bash
cat > scripts/validate.sh << 'EOF'
#!/bin/bash
echo "Validation failed!"
exit 1
EOF

zip -r deploy-broken.zip app.py appspec.yml scripts/
aws s3 cp deploy-broken.zip s3://$BUCKET/releases/broken/deploy-broken.zip
```

**PowerShell:**
```powershell
@"
#!/bin/bash
echo "Validation failed!"
exit 1
"@ | Set-Content scripts/validate.sh

Compress-Archive -Path app.py, appspec.yml, scripts -DestinationPath deploy-broken.zip -Force
aws s3 cp deploy-broken.zip s3://$BUCKET/releases/broken/deploy-broken.zip
```

**Passo 2 — Criar o novo deployment no CodeDeploy:**

CodeDeploy → Application `demo-webapp` → **Create deployment**:

| Campo | Valor |
|---|---|
| Deployment group | `demo-prod-bluegreen` |
| Revision location | S3 |
| S3 URL | `s3://codedeploy-artifacts-<account-id>/releases/broken/deploy-broken.zip` |

Acompanhe o que acontece:
1. **Deploying** — hook `ValidateService` executa o `validate.sh` que retorna `exit 1`
2. **CodeDeploy marca o deployment como falho** — o listener do ALB **não é alterado** (rerouting não ocorre pois a falha é antes dessa fase)
3. **Rollback automático disparado** — se o rerouting já tivesse ocorrido, o listener voltaria para `tg-blue`; como falhou antes, o Green simplesmente é descartado
4. **Instâncias Blue permanecem em produção** — verifique com `curl` no DNS do ALB que a versão anterior continua respondendo

> **Detalhe importante:** neste cenário a falha ocorre em `ValidateService`, que roda **após** o deploy nas instâncias Green mas **antes** do rerouting de tráfego. Por isso o rollback aqui é apenas descartar o Green — as Blue nunca saíram de produção.

---
## Pontos de Atenção

- Em Blue/Green, o rollback é **redirecionamento de tráfego** (não reversão de código)
- CodeDeploy Agent nos logs da instância: `sudo systemctl status codedeploy-agent` e `tail -f /var/log/aws/codedeploy-agent/codedeploy-agent.log`
- `appspec.yml` deve estar na **raiz** do pacote zip
- IAM Instance Profile na EC2 é **obrigatório** — sem ele o agente não consegue conectar ao CodeDeploy
- Lifecycle hooks: `ApplicationStop` roda na versão *antiga*, os demais na versão nova

---
## Limpeza

> **Mantenha a Application CodeDeploy `demo-webapp`** — referenciada no Lab 4 (CodePipeline).

```
# Remover instâncias pelo console EC2

# Remover ALB e target groups pelo console EC2 → Load Balancers

# Remover bucket S3 (re-declare a variável se necessário)
# Bash:  BUCKET="codedeploy-artifacts-$(aws sts get-caller-identity --query Account --output text)"
# PS:  $BUCKET = "codedeploy-artifacts-$(aws sts get-caller-identity --query Account --output text)"
aws s3 rb s3://$BUCKET --force
```
