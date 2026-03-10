#!/bin/bash
# cleanup.sh — Remove todos os recursos criados no Lab 2 (ECS Fargate + ALB)
# Execute este script ao finalizar a prática para evitar cobranças.

set -e

CLUSTER="dva-demo-cluster"
SERVICE="dva-demo-service"
REPO="dva-demo-app"

echo "=== Iniciando limpeza do Lab 2 (ECS Fargate) ==="

# 1. Zerar desired count do service (necessário antes de deletar)
echo "[1/4] Zerando desired count do service..."
aws ecs update-service \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --desired-count 0 2>/dev/null || echo "  (ignorado — service pode não existir)"

# Aguarda as tasks pararem
echo "  Aguardando tasks encerrarem (30s)..."
sleep 30

# 2. Deletar service
echo "[2/4] Deletando ECS service..."
aws ecs delete-service \
  --cluster "$CLUSTER" \
  --service "$SERVICE" 2>/dev/null || echo "  (ignorado)"

# 3. Deletar cluster
echo "[3/4] Deletando cluster ECS..."
aws ecs delete-cluster \
  --cluster "$CLUSTER" 2>/dev/null || echo "  (ignorado)"

# 4. Deletar imagens ECR (repositório criado no Lab 1)
echo "[4/4] Deletando imagens do ECR..."
aws ecr batch-delete-image \
  --repository-name "$REPO" \
  --image-ids imageTag=v1.0.0 imageTag=v2.0.0 imageTag=latest 2>/dev/null || echo "  (ignorado)"

aws ecr delete-repository \
  --repository-name "$REPO" \
  --force 2>/dev/null || echo "  (ignorado)"

echo ""
echo "=== Limpeza de CLI concluída ==="
echo ""
echo "Remova manualmente pelo Console (EC2):"
echo "  - Load Balancer : dva-demo-alb"
echo "  - Target Group  : dva-demo-tg"
echo "  - Security Groups: dva-alb-sg, dva-ecs-sg"
echo ""
echo "Remova pelo Console (IAM):"
echo "  - Role: ecsTaskExecutionRole (se criada exclusivamente para este lab)"
echo ""
echo "Remova pelo Console (CloudWatch):"
echo "  - Log group: /ecs/dva-demo-task"
