# Lab 3 — Cluster ECS, Task Definition e Service

## Custos e Free Tier

| Serviço | Free Tier |
|---------|-----------|
| ECS (Fargate) | Sem Free Tier — cobrado por vCPU/hora e GB de memória/hora |
| CloudWatch Logs | 5 GB de ingestão/mês (primeiros 12 meses) |

> **Aviso:** Duas tasks Fargate com 0,25 vCPU e 0,5 GB geram aproximadamente USD 0,01 por hora. Execute o cleanup no Lab 4 assim que concluir a prática.

---

## Objetivo

Criar o cluster ECS Fargate, a Task Definition com a imagem construída no Lab 1 e o ECS Service conectado ao Application Load Balancer criado no Lab 2. Verificar que as tasks estão rodando e saudáveis.

---

## Pré-requisitos

- Labs 1 e 2 concluídos
- IAM Role `ecsTaskExecutionRole` criada
- Security Groups `dva-alb-sg` e `dva-ecs-sg` criados
- ALB `dva-demo-alb` e Target Group `dva-demo-tg` criados e ativos

---

## Parte 1 — Verificar Service Linked Role

Se a conta nunca usou ECS antes, a Service Linked Role não existe e a criação do cluster vai falhar com erro `CREATE_FAILED — Unable to assume the service linked role`.

Execute o comando a seguir **uma única vez por conta**:

```
aws iam create-service-linked-role --aws-service-name ecs.amazonaws.com
```

Se o retorno for `InvalidInput — Service role name AWSServiceRoleForECS has been taken in this account`, a role já existe — siga normalmente.

> A Service Linked Role é gerenciada pela própria AWS e concede ao serviço ECS permissão para gerenciar recursos de rede, registrar targets no ALB e interagir com outros serviços em seu nome. Diferente da Execution Role e da Task Role, ela é criada e gerenciada pela AWS mas precisa existir na conta antes do primeiro uso.

---

## Parte 2 — Criar Cluster ECS

ECS → Clusters → **Create Cluster** ("Criar cluster"):

| Campo | Valor |
|---|---|
| Cluster name | `dva-demo-cluster` |
| Infrastructure | AWS Fargate (serverless) |

Clusters Fargate ficam prontos em segundos — não há EC2 para provisionar.

> O cluster é um agrupamento lógico — um namespace onde seus serviços e tasks vivem. No Fargate ele não representa infraestrutura de EC2 por baixo. Fica pronto imediatamente exatamente por isso: não há servidor para provisionar.

---

## Parte 3 — Criar Task Definition

ECS → Task definitions → **Create new task definition**:

**Task definition configuration:**

| Campo | Valor |
|---|---|
| Family | `dva-demo-task` |
| Launch type | AWS Fargate |
| OS/Architecture | Linux/X86_64 |
| CPU | 0.25 vCPU |
| Memory | 0.5 GB |
| Task execution role | `ecsTaskExecutionRole` |

**Container:**

| Campo | Valor |
|---|---|
| Name | `dva-demo-container` |
| Image URI | `<account-id>.dkr.ecr.<region>.amazonaws.com/dva-demo-app:v1.0.0` |
| Container port | 8080 / TCP |

**Logging:** habilitar `awslogs`, log group `/ecs/dva-demo-task`.

Para obter o Account ID e a região configurada, execute:

```
aws sts get-caller-identity --query Account --output text
aws configure get region
```

> Cada atualização salva na Task Definition cria uma **nova revisão imutável** — `dva-demo-task:1`, `dva-demo-task:2`, e assim por diante. A revisão anterior nunca é alterada. Essa imutabilidade é a base do rollback: basta apontar o service para uma revisão anterior.

> Habilitar o driver `awslogs` faz com que tudo que a aplicação escreve no stdout/stderr apareça automaticamente no CloudWatch Logs. Sem isso não há como depurar uma task Fargate que falha — os logs são a única janela para o que acontece dentro do container.

---

## Parte 4 — Criar ECS Service

ECS → Clusters → `dva-demo-cluster` → Services → **Create**:

**Compute configuration:**
- Estratégia do provedor de capacidade: **FARGATE**, Base 0, Peso 1
- Versão da plataforma: **LATEST**

**Service configuration:**

| Campo | Valor |
|---|---|
| Task definition | `dva-demo-task` (última revisão) |
| Service name | `dva-demo-service` |
| Desired tasks | 2 |

**Networking:**
- VPC: VPC padrão
- Subnets: ao menos 2 subnets em AZs diferentes
- Security group: remova o default e adicione `dva-ecs-sg`
- IP público: **ON**

> **IP público deve estar ON.** Em subnets públicas sem NAT Gateway, as tasks precisam de IP público para se comunicar com o ECR e o CloudWatch. Deixar OFF causa erro `ResourceInitializationError: unable to pull registry auth` e as tasks ficam presas em `PENDING`. Em produção com subnets privadas, o correto é manter OFF e usar VPC Endpoint para o ECR ou NAT Gateway.

**Load balancing:**
- Selecione **Usar um listener existente** → HTTP:80
- Selecione **Usar um grupo de destino existente** → `dva-demo-tg`

Aguarde 2–3 minutos para as 2 tasks atingirem status `RUNNING`.

> O Service é o controlador que garante que o número desejado de tasks esteja sempre rodando. Se uma task morrer, ele sobe outra automaticamente. Duas tasks em zonas de disponibilidade diferentes garantem que, se uma AZ inteira tiver problema, o serviço continua respondendo pela outra — Alta Disponibilidade básica no ECS.

---

## Parte 5 — Testar

1. ECS → Services → `dva-demo-service` → aba **Tasks** → aguarde status `RUNNING` nas 2 tasks
2. EC2 → Load Balancers → `dva-demo-alb` → copie o **DNS name**
3. Acesse no browser: `http://<dns-do-alb>`

Resposta esperada: `Hello from ECR! Container rodando na AWS!`

**Verificar logs:**
- ECS → Services → Tasks → clique na task → aba **Logs**
- Ou CloudWatch → Log groups → `/ecs/dva-demo-task`

Para checar o status das tasks via CLI:

```
aws ecs describe-services --cluster dva-demo-cluster --services dva-demo-service --query "services[0].{runningCount:runningCount,desiredCount:desiredCount,status:status}" --output table
```

---

## Erros Comuns e Soluções

| Erro | Causa | Solução |
|------|-------|---------|
| `CREATE_FAILED — Unable to assume the service linked role` | Service Linked Role do ECS não existe na conta | `aws iam create-service-linked-role --aws-service-name ecs.amazonaws.com` |
| `ResourceInitializationError: unable to pull registry auth` | Outbound bloqueado no SG das tasks ou IP público OFF | Verificar outbound do `dva-ecs-sg` (liberar Todo o tráfego → `0.0.0.0/0`) e/ou habilitar IP público no service |
| Tasks ficam em `PENDING` indefinidamente | Security Group incorreto ou subnet sem rota para internet | Verificar SG, subnet e configuração de IP público |
| Health check falhando no ALB | Aplicação não responde na porta ou path configurado | Confirmar porta 8080 no container e path `/` no target group |

---

## Pontos de Atenção

- **awsvpc networking:** cada task Fargate recebe seu próprio ENI com IP privado exclusivo — o número de ENIs disponíveis na subnet limita quantas tasks podem subir simultaneamente
- **Desired count vs running count:** o Service reconcilia constantemente; se running < desired, ele sobe tasks novas automaticamente
- **Health check:** tasks que falham no health check do ALB são encerradas e substituídas automaticamente
- **Subnet pública sem NAT:** tasks precisam de IP público para acessar ECR e CloudWatch; em produção com subnet privada use VPC Endpoint ou NAT Gateway

> Os recursos criados neste lab serão utilizados no Lab 4. A limpeza completa é feita ao final do Lab 4.
