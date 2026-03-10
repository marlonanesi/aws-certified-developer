# Lab 4 — Rolling Deploy e Limpeza

## Objetivo

Construir a v2 da aplicação, publicar no ECR, criar uma nova revisão da Task Definition e atualizar o ECS Service para observar o rolling deploy sem downtime. Ao final, remover todos os recursos criados nos Labs 2, 3 e 4.

---

## Pré-requisitos

- Labs 1, 2 e 3 concluídos
- ECS Service `dva-demo-service` rodando com 2 tasks em status `RUNNING`
- Docker instalado e em execução localmente

---

## Parte 1 — Build e Push da v2

No diretório de build do Lab 1, substitua o conteúdo de `app.py` pelo conteúdo do arquivo `app_v2.py` desta pasta.

Autentique no ECR e construa a nova imagem:

```
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$REGION = aws configure get region
$URI = "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/dva-demo-app"

aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

docker build -t dva-demo-app .
docker tag dva-demo-app:latest "${URI}:v2.0.0"
docker push "${URI}:v2.0.0"
```

Verifique que a imagem está no ECR:

```
aws ecr list-images --repository-name dva-demo-app --query "imageIds[].imageTag" --output table
```

---

## Parte 2 — Nova Revisão da Task Definition

ECS → Task definitions → `dva-demo-task` → **Create new revision**:

- Localize o campo **Image URI** do container `dva-demo-container`
- Altere de `...:v1.0.0` para `...:v2.0.0`
- Clique em **Create**

Uma nova revisão é criada — `dva-demo-task:2`. A revisão anterior continua existindo e pode ser usada para rollback a qualquer momento.

---

## Parte 3 — Atualizar o Service

ECS → Clusters → `dva-demo-cluster` → Services → `dva-demo-service` → **Update service**:

- **Task definition:** selecione `dva-demo-task:2`
- Clique em **Update**

O ECS inicia o rolling deploy imediatamente.

---

## Parte 4 — Observar o Rolling Deploy

O ECS sobe tasks novas com a v2 antes de encerrar as tasks antigas com a v1. Durante esse processo as duas versões estão rodando simultaneamente e o ALB distribui o tráfego entre elas.

Acompanhe o deploy:

1. ECS → Services → `dva-demo-service` → aba **Deployments** — observe as tasks sendo substituídas
2. Recarregue o browser (`http://<dns-do-alb>`) várias vezes — as respostas v1 e v2 se alternam até o deploy completar
3. Quando todas as tasks estiverem na v2, apenas a resposta `Hello from ECR! Versao 2.0 - Rolling Deploy funcionando!` será retornada

Acompanhe o status via CLI:

```
aws ecs describe-services --cluster dva-demo-cluster --services dva-demo-service --query "services[0].deployments[].{status:status,runningCount:runningCount,desiredCount:desiredCount,taskDefinition:taskDefinition}" --output table
```

> O rolling deploy garante que o serviço nunca para durante a atualização. Para rollback imediato, basta acessar Update service e selecionar `dva-demo-task:1` — o ECS executa o processo inverso. Essa é a diferença central entre Rolling Deploy e Blue/Green: no Blue/Green via CodeDeploy, um ambiente completamente novo sobe em paralelo antes de qualquer tráfego ser migrado — mais seguro para rollback instantâneo, mas dobra os recursos temporariamente.

---

## Erros Comuns e Soluções

| Erro | Causa | Solução |
|------|-------|---------|
| `docker push` falha com `no basic auth credentials` | Login no ECR expirado | Execute novamente o `aws ecr get-login-password ... \| docker login ...` |
| Tasks novas ficam em `PENDING` | Imagem `v2.0.0` não existe no ECR ou URI incorreto na task definition | Verificar com `aws ecr list-images --repository-name dva-demo-app` |
| Deployment parado — tasks novas falham no health check | Aplicação v2 não responde na porta ou path configurado | Verificar logs da task na aba Logs e confirmar que a porta 8080 está correta |

---

## Pontos de Atenção

- **Rolling deploy vs Blue/Green:** rolling deploy sobe tasks novas antes de encerrar as antigas — zero downtime mas sem isolamento de ambiente; Blue/Green sobe ambiente completamente novo antes de migrar tráfego — rollback instantâneo mas custo dobrado temporariamente
- **Revisões imutáveis:** rollback = selecionar revisão anterior da task definition no Update service
- **Desired count vs running count:** durante o deploy o running count pode ultrapassar o desired count temporariamente enquanto as tasks antigas são substituídas pelas novas

---

## Limpeza

Execute o script de limpeza para remover os recursos provisionados via CLI (é possível fazer tudo via console mas caso queira automatizar parte fique a vontade!):

```
.\cleanup.ps1
```

O script zera o desired count do service, aguarda as tasks encerrarem, deleta o service, o cluster e as imagens ECR.

Remova manualmente pelo console (EC2):
- Load Balancer: `dva-demo-alb`
- Target Group: `dva-demo-tg`
- Security Groups: `dva-alb-sg` e `dva-ecs-sg`

Remova pelo console (IAM):
- Role: `ecsTaskExecutionRole` (se criada exclusivamente para este lab)

Remova pelo console (CloudWatch):
- Log group: `/ecs/dva-demo-task`
