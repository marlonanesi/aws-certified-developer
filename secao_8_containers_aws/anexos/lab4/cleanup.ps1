# cleanup.ps1 — Remove todos os recursos criados nos Labs 2, 3 e 4 (ECS Fargate + ALB)
# Execute este script ao finalizar a prática para evitar cobranças.
#
# Como executar:
#   cd path\to\lab4
#   .\cleanup.ps1
#
# Caso PowerShell bloqueie a execução, rode antes:
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

$ErrorActionPreference = "Stop"

$CLUSTER    = "dva-demo-cluster"
$SERVICE    = "dva-demo-service"
$REPO       = "dva-demo-app"
$TASK_FAMILY = "dva-demo-task"

Write-Host "=== Iniciando limpeza dos Labs 2, 3 e 4 (ECS Fargate) ==="

# 1. Zerar desired count do service (necessário antes de deletar)
Write-Host "[1/4] Zerando desired count do service..."
try {
    aws ecs update-service --cluster $CLUSTER --service $SERVICE --desired-count 0 | Out-Null
    Write-Host "  Aguardando tasks encerrarem (30s)..."
    Start-Sleep -Seconds 30
} catch {
    Write-Host "  (ignorado — service pode nao existir)"
}

# 2. Deletar service
Write-Host "[2/4] Deletando ECS service..."
try {
    aws ecs delete-service --cluster $CLUSTER --service $SERVICE | Out-Null
} catch {
    Write-Host "  (ignorado)"
}

# 3. Deletar cluster
Write-Host "[3/4] Deletando cluster ECS..."
try {
    aws ecs delete-cluster --cluster $CLUSTER | Out-Null
} catch {
    Write-Host "  (ignorado)"
}

# 4. Deregistrar e deletar task definitions
Write-Host "[4/5] Deregistrando e deletando task definitions da familia $TASK_FAMILY..."
try {
    $ARNS = aws ecs list-task-definitions --family-prefix $TASK_FAMILY --query "taskDefinitionArns[]" --output json | ConvertFrom-Json
    if ($ARNS.Count -gt 0) {
        foreach ($ARN in $ARNS) {
            aws ecs deregister-task-definition --task-definition $ARN | Out-Null
            Write-Host "  Deregistered: $ARN"
        }
        aws ecs delete-task-definitions --task-definitions $ARNS | Out-Null
        Write-Host "  Task definitions deletadas."
    } else {
        Write-Host "  (nenhuma task definition encontrada)"
    }
} catch {
    Write-Host "  (ignorado)"
}

# 5. Deletar imagens ECR
Write-Host "[5/5] Deletando imagens do ECR..."
try {
    aws ecr batch-delete-image --repository-name $REPO --image-ids imageTag=v1.0.0 imageTag=v2.0.0 imageTag=latest | Out-Null
} catch {
    Write-Host "  (ignorado)"
}
try {
    aws ecr delete-repository --repository-name $REPO --force | Out-Null
} catch {
    Write-Host "  (ignorado)"
}

Write-Host ""
Write-Host "=== Limpeza de CLI concluida ==="
Write-Host ""
Write-Host "Remova manualmente pelo Console (EC2):"
Write-Host "  - Load Balancer : dva-demo-alb"
Write-Host "  - Target Group  : dva-demo-tg"
Write-Host "  - Security Groups: dva-alb-sg, dva-ecs-sg"
Write-Host ""
Write-Host "Remova pelo Console (IAM):"
Write-Host "  - Role: ecsTaskExecutionRole (se criada exclusivamente para este lab)"
Write-Host ""
Write-Host "Remova pelo Console (CloudWatch):"
Write-Host "  - Log group: /ecs/dva-demo-task"
