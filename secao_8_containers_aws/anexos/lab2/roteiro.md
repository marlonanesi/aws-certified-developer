# Lab 2 — Infraestrutura de Rede e Balanceamento de Carga

## Custos e Free Tier

| Serviço | Free Tier |
|---------|-----------|
| Application Load Balancer | Sem Free Tier — cobrado por hora + LCUs processadas |
| ECR | 500 MB de armazenamento/mês (primeiros 12 meses) |
| CloudWatch Logs | 5 GB de ingestão/mês (primeiros 12 meses) |

> **Aviso:** O ALB custa aproximadamente USD 0,008 por hora. Execute o cleanup no Lab 4 assim que concluir a prática.

---

## Objetivo

Criar os recursos de infraestrutura que o ECS Service vai utilizar nos próximos labs: a IAM Role de execução de tasks, os Security Groups e o Application Load Balancer com seu Target Group.

---

## Pré-requisitos

- Lab 1 concluído — imagem `dva-demo-app:v1.0.0` no ECR
- AWS CLI configurada
- VPC padrão disponível na conta

---

## Parte 1 — Criar IAM Role para Execução de Tasks

IAM → Roles → **Create role** ("Criar função"):

| Campo | Valor |
|---|---|
| Trusted entity | AWS service → Elastic Container Service Task |
| Policy | `AmazonECSTaskExecutionRolePolicy` |
| Nome | `ecsTaskExecutionRole` |

Esta role é utilizada pelo ECS Agent — o processo que orquestra o container — para fazer pull da imagem no ECR e enviar logs ao CloudWatch. Ela age antes do container existir.

> A **Execution Role** é diferente da **Task Role**. A Task Role daria permissões ao código dentro do container para acessar outros serviços AWS (DynamoDB, S3, SQS etc.). Neste lab a aplicação não acessa nenhum serviço AWS diretamente, portanto apenas a Execution Role é necessária.

---

## Parte 2 — Criar Security Groups

VPC → Security Groups → **Create security group**:

**SG para o Load Balancer (`dva-alb-sg`):**

| Campo | Valor |
|---|---|
| Nome | `dva-alb-sg` |
| Inbound | HTTP 80 — Source `0.0.0.0/0` |
| Outbound | Todo o tráfego → `0.0.0.0/0` (padrão) |

**SG para as Tasks ECS (`dva-ecs-sg`):**

| Campo | Valor |
|---|---|
| Nome | `dva-ecs-sg` |
| Inbound | TCP 8080 — Source `dva-alb-sg` |
| Outbound | Todo o tráfego → `0.0.0.0/0` **(obrigatório — não remova)** |

> **Outbound do `dva-ecs-sg` é obrigatório.** A task precisa de saída na porta 443 para se autenticar no ECR, fazer pull da imagem e enviar logs ao CloudWatch. Se o outbound estiver bloqueado ou ausente, a task falha com `ResourceInitializationError` antes mesmo de inicializar. Ao criar o SG, confirme que a regra de saída padrão está presente.

As tasks não aceitam tráfego direto da internet — somente do Load Balancer. Ao usar `dva-alb-sg` como source do `dva-ecs-sg`, você garante que o único caminho de entrada é pelo ALB.

---

## Parte 3 — Criar Application Load Balancer e Target Group

EC2 → Load Balancers → **Create** → **Application Load Balancer**:

| Campo | Valor |
|---|---|
| Name | `dva-demo-alb` |
| Scheme | Internet-facing |
| VPC | VPC padrão |
| Subnets | Ao menos 2 AZs |
| Security group | `dva-alb-sg` |

**Listener:** HTTP:80 — protocolo HTTP1

**Target Group** — clique em "criar um grupo de destino" no campo de ação padrão do listener (abre em nova aba):

| Campo | Valor |
|---|---|
| Target type | IP addresses |
| Name | `dva-demo-tg` |
| Protocol/Port | HTTP / 8080 |
| Protocol version | HTTP1 |
| Health check path | `/` |

Na etapa "Registrar destinos", não registre nada — o ECS Service registrará os IPs das tasks automaticamente.

Após criar o target group, volte na aba do ALB, atualize o dropdown do listener e selecione `dva-demo-tg`.

> **Target type: IP addresses** é obrigatório no Fargate porque as tasks não estão associadas a instâncias EC2 — elas possuem IPs privados próprios via awsvpc networking. O ECS Service registra e desregistra esses IPs automaticamente conforme as tasks sobem e descem.

---

## Pontos de Atenção

- **Execution Role vs Task Role:** são identidades separadas — Execution Role é para o ECS Agent fazer pull da imagem e enviar logs; Task Role é para o código da aplicação acessar serviços AWS
- **Outbound obrigatório no `dva-ecs-sg`:** sem a regra de saída a task não consegue autenticar no ECR e falha antes de inicializar
- **Target type IP addresses:** obrigatório no Fargate — tasks não têm instância EC2 associada
- **Não registrar targets manualmente no Target Group:** o ECS Service faz isso automaticamente ao subir as tasks

> Os recursos criados neste lab serão utilizados nos Labs 3 e 4. A limpeza completa é feita ao final do Lab 4.
