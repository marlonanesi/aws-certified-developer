# Lab 3A — Infraestrutura para CodeDeploy Blue/Green

> **Compatibilidade de comandos**
> - Linux / macOS / Git Bash → bloco `bash`
> - Windows PowerShell → bloco `powershell`
> - Comandos sem variáveis funcionam diretamente em ambos.

## Custos e Free Tier

| Serviço | Free Tier |
|---|---|
| EC2 | 750 horas/mês `t2.micro` (primeiros 12 meses) |
| Application Load Balancer | **Sem Free Tier** — ~USD 0,008/hora + LCUs |
| S3 | 5 GB + 20k GET + 2k PUT (primeiros 12 meses) |

> **Aviso:** O ALB não tem Free Tier. Execute o cleanup ao concluir para evitar cobranças.

---
## Pré-requisito

Labs 1 e 2 concluídos. Repositório `demo-dva-pipeline` com `app.py` e `buildspec.yml`.

---
## Objetivo

Montar toda a infraestrutura necessária para o deploy Blue/Green do Lab 3B:
- IAM roles (EC2 + CodeDeploy)
- Security Groups, Launch Template e Auto Scaling Group (ambiente Blue)
- ALB e Target Groups (`tg-blue` e `tg-green`)
- Artefato de deploy empacotado no S3

Ao final deste lab o app v1 estará respondendo pelo DNS do ALB, pronto para receber o deploy Blue/Green.

---
## Arquivos de apoio (pasta raiz do lab3)

| Arquivo | Usado em |
|---|---|
| `user_data.sh` | Launch Template — inicializa o CodeDeploy Agent nas instâncias |
| `app.py` | Aplicação Python v2 (Green) |
| `appspec.yml` | Manifesto do CodeDeploy (lifecycle hooks) |
| `scripts/` | Scripts dos hooks (`install_deps.sh`, `start_app.sh`, `validate.sh`) |
| `codedeploy-autoscaling-policy.json` | Inline policy para a role do CodeDeploy (usado no Lab 3B) |

---
## Parte 1 — IAM

### Passo 1 — Criar o IAM Instance Profile para as instâncias EC2

O CodeDeploy Agent rodando nas instâncias precisa de permissão para se comunicar com o serviço CodeDeploy e baixar artefatos do S3.

**IAM → Roles → Create role:**

| Campo | Valor |
|---|---|
| Trusted entity type | **AWS service** |
| Use case | **EC2** |

Clique em **Next** e adicione as políticas:

| Política | Para que serve |
|---|---|
| `AmazonEC2RoleforAWSCodeDeploy` | permite ao agente baixar revisões do S3 e comunicar status ao CodeDeploy |
| `AmazonSSMManagedInstanceCore` | permite acesso via Session Manager (recomendado para debug sem SSH) |

**Next** → Nome da role: `EC2InstanceProfile-CodeDeploy` → **Create role**.

> O Instance Profile é criado automaticamente com o mesmo nome da role — não é necessário criar separadamente.

---
## Parte 2 — Rede e Segurança

### Passo 1 — Criar os Security Groups

Crie nesta ordem — o SG das instâncias referencia o SG do ALB.

**SG 1 — ALB (`alb-sg`):**

EC2 → Security Groups → **Create security group**:

| Campo | Valor |
|---|---|
| Name | `alb-sg` |
| VPC | VPC padrão |
| Inbound rule | HTTP, Port 80, Source: `0.0.0.0/0` |

**SG 2 — Instâncias EC2 (`ec2-sg`):**

| Campo | Valor |
|---|---|
| Name | `ec2-sg` |
| VPC | mesma VPC |
| Inbound rule | Custom TCP, Port **8080**, Source: **`alb-sg`** (selecione o SG, não um CIDR) |

> Nunca use `0.0.0.0/0` no `ec2-sg` — somente o ALB deve acessar a porta 8080 das instâncias.

---
## Parte 3 — Launch Template e Auto Scaling Group

### Passo 1 — Criar o Launch Template

EC2 → **Launch Templates** → **Create launch template**:

| Campo | Valor |
|---|---|
| Launch template name | `lt-codedeploy-blue-green` |
| Auto Scaling guidance | ✅ marque "Provide guidance..." |
| AMI | Amazon Linux 2023 (Quick Start) |
| Instance type | `t2.micro` |
| Key pair | selecione um existente ou "Proceed without" |
| Security groups | `ec2-sg` |
| IAM instance profile | `EC2InstanceProfile-CodeDeploy` |
| User data | conteúdo do arquivo `user_data.sh` da pasta raiz do lab3 |

> O Launch Template é apenas o blueprint — o ASG abaixo é quem lança as instâncias.

### Passo 2 — Criar o Auto Scaling Group (ambiente Blue)

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
| ↳ Target group | `tg-blue` |
| Health check type | EC2 |

> Ainda não criamos o `tg-blue` — **pule este passo por enquanto** e volte para editar o ASG após criar os Target Groups na Parte 4.

**Step 4 — Configure group size:**

| Campo | Valor |
|---|---|
| Desired capacity | `2` |
| Minimum capacity | `2` |
| Maximum capacity | `2` |
| Automatic scaling | No scaling policies |

**Step 5 — Add tags:**

| Chave | Valor | Propagar para instâncias |
|---|---|---|
| `Name` | `codedeploy-webapp` | ✅ Sim |
| `Environment` | `blue` | ✅ Sim |

> **Por que `codedeploy-webapp` e não `blue-instance`?** O CodeDeploy clona o ASG Blue herdando todas as tags. Com um nome fixo como `blue-instance` as instâncias Green ficariam com nome errado. Um nome neutro evita confusão.

Clique em **Create Auto Scaling group** e aguarde as 2 instâncias ficarem `InService`.

---
## Parte 4 — ALB e Target Groups

> **Por que 2 target groups?** O ALB usa `tg-blue` como produção atual. No deploy, o CodeDeploy registra as instâncias Green no `tg-green` e altera o listener para apontar para ele.

### Passo 1 — Criar os Target Groups

EC2 → **Target Groups** → **Create target group**:

**`tg-blue` (produção atual):**

| Campo | Valor |
|---|---|
| Target type | Instances |
| Name | `tg-blue` |
| Protocol / Port | HTTP / 8080 |
| Health check path | `/` |
| VPC | mesma VPC |

Após criar → **Register targets** → selecione as 2 instâncias Blue → porta 8080 → **Register pending targets**.

**`tg-green` (inicialmente vazio):**

Repita com as mesmas configurações, nome `tg-green`. **Não registre instâncias** — o CodeDeploy faz isso no deploy.

### Passo 2 — Vincular `tg-blue` ao ASG

Volte ao ASG `asg-blue-codedeploy` → **Edit** → **Load balancing** → selecione `tg-blue` → **Save**.

### Passo 3 — Criar o Application Load Balancer

EC2 → Load Balancers → **Create load balancer** → **Application Load Balancer**:

| Campo | Valor |
|---|---|
| Name | `demo-codedeploy-alb` |
| Scheme | Internet-facing |
| Subnets | pelo menos 2 AZs |
| Security group | `alb-sg` |
| Listener | HTTP : 80 → Default action: encaminhar para `tg-blue` |

> Anote o **DNS name** do ALB — será usado para verificar no Lab 3B.

### Passo 4 — Adicionar tg-green ao listener do ALB

> ⚠️ **Este passo é obrigatório.** Sem ele, o deploy trava na Etapa 3 indefinidamente sem mensagem de erro visível.

O CodeDeploy não cria entradas no listener — ele apenas modifica pesos já existentes. O `tg-green` precisa estar registrado no listener com peso 0 antes do deploy. Sem isso, o CodeDeploy registra as instâncias Green no target group mas nunca consegue redirecionar o tráfego.

**EC2 → Load Balancers → `demo-codedeploy-alb` → aba Listeners and rules → clique no link HTTP:80 → localize a regra Default → clique nos três pontinhos ⋮ → Edit rule:**

| Campo | Valor |
|---|---|
| Grupo de destino 1 | `tg-blue` — Peso: 1 |
| Grupo de destino 2 | `tg-green` — Peso: 0 |

Clique em **+ Adicionar grupo de destino**, selecione `tg-green`, defina peso `0` → **Save changes**.

> Peso `0` significa que nenhum tráfego vai para o `tg-green` agora — mas o listener já o conhece e o CodeDeploy consegue alterar esse peso para `100` no momento do traffic shift (Etapa 3).

---
## Parte 5 — Artefato de Deploy (S3)

O CodeDeploy precisa de um `.zip` no S3 como fonte do deploy. O `appspec.yml` **deve estar na raiz** do zip.

**Passo 1 — Copiar os arquivos para o repositório e fazer push:** 

```
cd demo-dva-pipeline
# copie app.py, appspec.yml e scripts/ da pasta raiz do lab3
git add .
git commit -m "feat: v2 - add appspec.yml and deployment scripts"
git push
```

**Passo 2 — Empacotar e subir ao S3:**

```bash
BUCKET="codedeploy-artifacts-$(aws sts get-caller-identity --query Account --output text)"
aws s3 mb s3://$BUCKET
zip -r deploy-package.zip app.py appspec.yml scripts/
aws s3 cp deploy-package.zip s3://$BUCKET/releases/v2/deploy-package.zip
```

```powershell
$BUCKET = "codedeploy-artifacts-$(aws sts get-caller-identity --query Account --output text)"
aws s3 mb s3://$BUCKET
Compress-Archive -Path app.py, appspec.yml, scripts -DestinationPath deploy-package.zip -Force
aws s3 cp deploy-package.zip s3://$BUCKET/releases/v2/deploy-package.zip
```

---
## Verificação Final

Antes de ir para o Lab 3B, confirme:

```powershell
# 1. Instâncias Blue rodando com as tags corretas
aws ec2 describe-instances `
  --filters "Name=tag:Environment,Values=blue" "Name=instance-state-name,Values=running" `
  --query "Reservations[].Instances[].{ID:InstanceId,State:State.Name}" `
  --output table

# 2. tg-blue com 2 instâncias healthy
aws elbv2 describe-target-health `
  --target-group-arn $(aws elbv2 describe-target-groups --names tg-blue --query 'TargetGroups[0].TargetGroupArn' --output text) `
  --query "TargetHealthDescriptions[].{ID:Target.Id,State:TargetHealth.State}" `
  --output table

# 3. App respondendo pelo ALB
$ALB_DNS = aws elbv2 describe-load-balancers --names demo-codedeploy-alb --query 'LoadBalancers[0].DNSName' --output text
curl "http://$ALB_DNS"
# Esperado: "V1 - Blue Environment"

# 4. Listener com ambos os TGs registrados
aws elbv2 describe-listeners `
  --load-balancer-arn $(aws elbv2 describe-load-balancers --names demo-codedeploy-alb --query 'LoadBalancers[0].LoadBalancerArn' --output text) `
  --query "Listeners[0].DefaultActions[0].ForwardConfig.TargetGroups" `
  --output table
# Esperado: tg-blue com Weight 1 e tg-green com Weight 0
```

---
## Recursos criados neste lab

| Recurso | Nome |
|---|---|
| IAM Role (EC2) | `EC2InstanceProfile-CodeDeploy` |
| Security Group ALB | `alb-sg` |
| Security Group EC2 | `ec2-sg` |
| Launch Template | `lt-codedeploy-blue-green` |
| Auto Scaling Group | `asg-blue-codedeploy` |
| Target Group Blue | `tg-blue` |
| Target Group Green | `tg-green` (vazio) |
| Load Balancer | `demo-codedeploy-alb` |
| S3 Bucket | `codedeploy-artifacts-<account-id>` |

> **Não faça cleanup agora** — todos esses recursos são usados no Lab 3B.
