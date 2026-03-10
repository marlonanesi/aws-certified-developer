# Roteiro — Lab 2: Deploy de Aplicação no ECS Fargate
### Versão do Instrutor — com insights e troubleshooting

---

## Custos e Free Tier

| Serviço | Free Tier |
|---------|-----------|
| ECS (Fargate) | **Sem Free Tier** — cobrado por vCPU/hora e GB de memória/hora |
| Application Load Balancer | **Sem Free Tier** — cobrado por hora + LCUs processadas |
| ECR | 500 MB de armazenamento/mês (primeiros 12 meses) |
| CloudWatch Logs | 5 GB de ingestão/mês (primeiros 12 meses) |

> **Aviso:** ALB + duas tasks Fargate podem gerar USD 0,50+ por dia. **Execute o cleanup logo após concluir a prática.**

---

## Objetivo

Criar um cluster ECS Fargate, uma Task Definition, um Application Load Balancer e um ECS Service. Implantar a imagem construída no Lab 1 e observar o rolling deploy ao atualizar para a v2.

---

## Pré-requisitos

- Lab 1 concluído — imagem `dva-demo-app:v1.0.0` no ECR
- AWS CLI configurada
- VPC padrão disponível na conta

---

## Parte 0 — Criar IAM Role para Execução de Tasks

IAM → Roles → **Create role**:

| Campo | Valor |
|---|---|
| Trusted entity | AWS service → Elastic Container Service Task |
| Policy | `AmazonECSTaskExecutionRolePolicy` |
| Nome | `ecsTaskExecutionRole` |

> 💡 **Insight — Execution Role vs Task Role:** Esta é uma das distinções mais cobradas no DVA. A **Execution Role** é usada pelo *ECS Agent* — o processo que orquestra o container — para fazer pull da imagem no ECR e enviar logs para o CloudWatch. Ela age *antes* do container existir. Já a **Task Role** dá permissões ao *código dentro do container* para acessar DynamoDB, S3, SQS e outros serviços. São identidades completamente separadas com propósitos distintos. Nesse lab só precisamos da Execution Role porque nossa aplicação não acessa nenhum serviço AWS diretamente.

---

## Parte 1 — Criar Cluster ECS

> ⚠️ **Atenção — Primeira vez usando ECS na conta:** Se a conta nunca usou ECS antes, a Service Linked Role não existe e a criação do cluster vai falhar. Rode esse comando antes de criar o cluster:
>
> `aws iam create-service-linked-role --aws-service-name ecs.amazonaws.com`
>
> Esse comando só precisa ser executado uma vez por conta. A role fica disponível permanentemente.

> 💡 **Insight — O que é a Service Linked Role:** É uma role especial gerenciada pela própria AWS que dá ao serviço ECS permissão para gerenciar recursos de rede, registrar targets no ALB e interagir com outros serviços em seu nome. Diferente da Execution Role e da Task Role que você cria manualmente, essa é criada e gerenciada pela AWS — mas precisa existir na conta antes do primeiro uso.

ECS → Clusters → **Create Cluster**:

| Campo | Valor |
|---|---|
| Cluster name | `dva-demo-cluster` |
| Infrastructure | AWS Fargate (serverless) ✅ |

> 💡 **Insight — O que é um Cluster no ECS:** O cluster é um agrupamento lógico — um namespace onde seus serviços e tasks vivem. No Fargate ele não representa nenhuma infraestrutura de EC2 por baixo. Fica pronto em segundos exatamente por isso: não há servidor para provisionar, o Fargate cuida da infraestrutura de forma totalmente gerenciada.

---

## Parte 2 — Criar Task Definition

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

**Logging:** habilitar `awslogs`, log group `/ecs/dva-demo-task`

> 💡 **Insight — Task Definition é imutável por design:** Cada vez que você salva uma alteração, o ECS cria uma **nova revisão** — `dva-demo-task:1`, `dva-demo-task:2`, e assim por diante. A revisão anterior nunca é alterada. Isso é intencional: é exatamente essa imutabilidade que torna o rollback trivial — basta apontar o service para uma revisão anterior. No exame, quando aparecer cenário de rollback no ECS, a resposta sempre envolve revisão da task definition.

> 💡 **Insight — 0.25 vCPU e 0.5 GB:** No Fargate você define CPU e memória em valores fixos — não é como EC2 onde você escolhe um tipo de instância. Esses são os menores valores disponíveis, suficientes para esse lab. Em produção, subdimensionar memória é a causa mais comum de tasks sendo encerradas com `OOMKilled` — erro de Out of Memory. Monitore sempre pelo CloudWatch.

> 💡 **Insight — awslogs:** Habilitar o driver `awslogs` faz com que tudo que sua aplicação escreve no stdout/stderr apareça automaticamente no CloudWatch Logs. Sem isso você fica cego — não há como depurar uma task Fargate que falha sem acesso aos logs. Em produção isso não é opcional.

---

## Parte 3 — Criar Security Groups

VPC → Security Groups → **Create security group**:

**SG para o Load Balancer (`dva-alb-sg`):**
- Descrição: `Permite tráfego HTTP na porta 80 para o Application Load Balancer`
- Inbound: HTTP 80 from `0.0.0.0/0`
- Outbound: Todo o tráfego para `0.0.0.0/0` (padrão)

**SG para as Tasks ECS (`dva-ecs-sg`):**
- Descrição: `Permite tráfego na porta 8080 originado apenas do Security Group do ALB`
- Inbound: TCP 8080, Source: `dva-alb-sg`
- Outbound: Todo o tráfego para `0.0.0.0/0` (**obrigatório — não remova**)

> ⚠️ **Atenção crítica — Outbound do dva-ecs-sg:** O outbound liberado para `0.0.0.0/0` no `dva-ecs-sg` **não é opcional**. A task precisa de saída na porta 443 para se autenticar no ECR, fazer pull da imagem e enviar logs para o CloudWatch. Se o outbound estiver bloqueado, a task falha com erro `ResourceInitializationError` antes mesmo de inicializar. Ao criar o SG, verifique se a regra de saída padrão está presente. Se estiver ausente ou com erro no console, exclua a regra problemática e recrie manualmente: Tipo = Todo o tráfego, Destino = `0.0.0.0/0`.

> 💡 **Insight — Por que dois Security Groups:** Essa arquitetura de dois SGs é um padrão de segurança importante que cai no exame. As tasks **não devem aceitar tráfego direto da internet** — somente do Load Balancer. Ao colocar `dva-alb-sg` como source do `dva-ecs-sg`, você garante que mesmo que alguém descubra o IP privado de uma task, não consegue acessá-la diretamente. O único caminho de entrada é pelo ALB.

> 💡 **Insight — Security Group é stateful:** A regra de inbound que você configurou (porta 8080 do ALB) não tem relação com o tráfego de saída que a task precisa fazer para o ECR. São fluxos independentes. A task precisa de outbound 443 para autenticar no ECR, enviar logs para o CloudWatch e realizar qualquer chamada de API AWS.

> 💡 **Insight — awsvpc networking:** Cada task Fargate recebe seu próprio ENI — Elastic Network Interface — com um IP privado exclusivo. O Security Group é aplicado diretamente na task, não em um host compartilhado. Isso é mais seguro e mais granular, mas significa que o número de ENIs disponíveis na subnet limita quantas tasks você pode subir.

---

## Parte 4 — Criar Application Load Balancer

EC2 → Load Balancers → **Create** → **Application Load Balancer**:

| Campo | Valor |
|---|---|
| Name | `dva-demo-alb` |
| Scheme | Internet-facing |
| VPC | VPC padrão |
| Subnets | Ao menos 2 AZs |
| Security group | `dva-alb-sg` |

**Listener:** HTTP:80 — protocolo **HTTP1**

**Target Group** — clique em "criar um grupo de destino" no campo de ação padrão do listener (abre em nova aba):

| Campo | Valor |
|---|---|
| Target type | IP addresses |
| Name | `dva-demo-tg` |
| Protocol/Port | HTTP / 8080 |
| Protocol version | HTTP1 |
| Health check path | `/` |

Na etapa "Registrar destinos" — **não registre nada**. Deixa vazio e finaliza. O ECS Service registrará os IPs automaticamente.

Após criar o target group, volte na aba do ALB, atualize o dropdown do listener e selecione `dva-demo-tg`.

> 💡 **Insight — Target type: IP addresses:** No Fargate obrigatoriamente usamos **IP** porque as tasks não estão associadas a instâncias EC2 — elas têm IPs privados próprios via awsvpc. O ECS Service registra e desregistra esses IPs automaticamente conforme as tasks sobem e descem.

> 💡 **Insight — Health check path `/`:** O ALB bate nesse endpoint periodicamente em cada task. Se a resposta não for 2xx ou 3xx, a task é considerada *unhealthy* e o ECS a encerra e sobe uma nova no lugar. Em aplicações reais, é recomendado ter um endpoint dedicado `/health` que verifica as dependências internas antes de responder OK.

> 💡 **Insight — Protocolo HTTP1:** A interface oferece HTTP1, HTTP2 e gRPC. Use HTTP1 para aplicações HTTP simples. HTTP2 exige que a aplicação suporte multiplexação de streams. gRPC é para comunicação entre microsserviços usando Protocol Buffers. Para esse lab, HTTP1 é o correto.

---

## Parte 5 — Criar ECS Service

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
- IP público: **ON** (necessário para subnets públicas sem NAT Gateway)

**Load balancing:**
- Selecione **Usar um listener existente** → HTTP:80
- Selecione **Usar um grupo de destino existente** → `dva-demo-tg`

Aguarde 2–3 minutos para as 2 tasks atingirem status `RUNNING`.

> ⚠️ **Atenção — IP público ON:** Em subnets públicas sem NAT Gateway, as tasks precisam de IP público para se comunicar com o ECR e o CloudWatch. Deixar OFF nesse cenário causa erro `ResourceInitializationError: unable to pull registry auth`. Em produção com subnets privadas, o correto é manter OFF e usar **VPC Endpoint para o ECR** ou um **NAT Gateway** — ambos têm custo adicional e fogem do escopo desse lab.

> 💡 **Insight — Estratégia do provedor de capacidade vs Tipo de inicialização:** O modo de estratégia é o atual e recomendado — permite misturar FARGATE e FARGATE_SPOT numa mesma estratégia para otimizar custo. FARGATE_SPOT pode reduzir custo em até 70% mas as tasks podem ser interrompidas — indicado para workloads tolerantes a falhas. Tipo de inicialização é o modo legado sem essa flexibilidade.

> 💡 **Insight — O que é o Service:** O Service é o controlador que garante que o número desejado de tasks esteja sempre rodando. Se uma task morrer, ele sobe outra automaticamente. Pensa nele como um supervisor permanente — o estado desejado declarado por você é o que ele vai tentar manter indefinidamente.

> 💡 **Insight — Desired tasks: 2 em AZs diferentes:** Duas tasks em zonas de disponibilidade diferentes garante que se uma AZ inteira tiver problema, o serviço continua respondendo pela outra. Com apenas 1 task você tem Single Point of Failure. Isso é Alta Disponibilidade básica no ECS — conceito direto no DVA.

---

## Parte 6 — Testar

1. ECS → Services → `dva-demo-service` → Tasks → aguarde `RUNNING`
2. EC2 → Load Balancers → `dva-demo-alb` → copie o **DNS name**
3. Acesse no browser: `http://<dns-do-alb>`

Resposta esperada: `Hello from ECR! Container rodando na AWS!`

**Verificar logs:**
- ECS → Services → Tasks → clique na task → aba Logs
- Ou CloudWatch → Log groups → `/ecs/dva-demo-task`

> 💡 **Insight — Dois caminhos para ver logs:** Direto na task pelo console ECS é mais rápido para debug pontual. Pelo CloudWatch é onde você faz análise histórica, cria métricas e configura alarmes. Em produção você nunca monitora olhando task por task — usa o CloudWatch como fonte central.

---

## Parte 7 — Rolling Deploy (v2)

No diretório de build, substitua `app.py` pelo conteúdo de `app_v2.py`.

**Build e push da v2:**

Bash:

`ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)`

`REGION=$(aws configure get region)`

`URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/dva-demo-app"`

`docker build -t dva-demo-app .`

`docker tag dva-demo-app:latest $URI:v2.0.0`

`docker push $URI:v2.0.0`

PowerShell:

`$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text`

`$REGION = aws configure get region`

`$URI = "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/dva-demo-app"`

`docker build -t dva-demo-app .`

`docker tag dva-demo-app:latest "${URI}:v2.0.0"`

`docker push "${URI}:v2.0.0"`

**Nova revisão da Task Definition:**

ECS → Task definitions → `dva-demo-task` → **Create new revision** → altere o Image URI para `...:v2.0.0` → Create.

**Atualizar o Service:**

ECS → Services → `dva-demo-service` → **Update service** → selecione a nova revisão → Update.

Observe o rolling deploy: recarregue o browser várias vezes — as duas versões alternam até o deploy completar.

> 💡 **Insight — O que é Rolling Deploy:** O ECS não derruba todas as tasks de uma vez. Ele sobe tasks novas com a v2 *antes* de encerrar as antigas com a v1. Durante esse processo as duas versões estão rodando simultaneamente — o ALB distribui o tráfego entre elas. Isso é zero downtime deployment — o serviço nunca para.

> 💡 **Insight — Rolling vs Blue/Green:** O rolling deploy é o padrão do ECS. Existe também o **Blue/Green deploy via CodeDeploy** — que sobe um ambiente completamente novo em paralelo, testa, e só então migra o tráfego de uma vez. O Blue/Green é mais seguro para rollback instantâneo mas mais caro pois dobra os recursos temporariamente. O DVA cobra a diferença entre os dois.

---

## Erros Comuns e Soluções

| Erro | Causa | Solução |
|------|-------|---------|
| `CREATE_FAILED — Unable to assume the service linked role` | Service Linked Role do ECS não existe na conta | `aws iam create-service-linked-role --aws-service-name ecs.amazonaws.com` |
| `ResourceInitializationError: unable to pull registry auth` com i/o timeout | Outbound bloqueado no SG das tasks ou IP público OFF em subnet pública | Verificar outbound do `dva-ecs-sg` (liberar Todo tráfego → 0.0.0.0/0) e/ou habilitar IP público |
| Tasks ficam em PENDING indefinidamente | Security Group incorreto ou subnet sem rota para internet | Verificar SG, subnet e configuração de IP público |
| Health check falhando | Aplicação não responde na porta/path configurado | Verificar porta do container na task definition e health check path no target group |

---

## Pontos de Atenção para a Prova

- **Execution Role ≠ Task Role** — Execution Role: ECS Agent acessa ECR e CloudWatch. Task Role: código dentro do container acessa outros serviços AWS.
- **awsvpc networking** — cada task Fargate recebe seu próprio ENI com IP privado exclusivo
- **Desired count vs running count** — o Service reconcilia constantemente; se running < desired, ele sobe tasks novas automaticamente
- **Health check** — tasks que falham no health check do ALB são encerradas e substituídas automaticamente
- **Revisões imutáveis** — rollback = selecionar revisão anterior da task definition no Update service
- **Subnet pública sem NAT** — tasks precisam de IP público para acessar ECR e CloudWatch; em produção com subnet privada use VPC Endpoint ou NAT Gateway

---

## Limpeza

Bash: `bash cleanup.sh`

PowerShell: `.\cleanup.ps1`

O script zera o service, deleta cluster e imagens ECR. Os recursos abaixo devem ser removidos manualmente pelo console:

- Application Load Balancer (`dva-demo-alb`)
- Target Group (`dva-demo-tg`)
- Security Groups (`dva-alb-sg` e `dva-ecs-sg`)
- Log Group (`/ecs/dva-demo-task`)
