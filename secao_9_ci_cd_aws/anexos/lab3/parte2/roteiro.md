# Lab 3B — CodeDeploy Blue/Green: Deploy e Rollback

> **Compatibilidade de comandos**
> - Linux / macOS / Git Bash → bloco `bash`
> - Windows PowerShell → bloco `powershell`

## Pré-requisito

**Lab 3A concluído.** Você deve ter:
- ASG `asg-blue-codedeploy` com 2 instâncias `InService`
- ALB `demo-codedeploy-alb` respondendo com `V1 - Blue Environment`
- `tg-blue` com 2 instâncias healthy, `tg-green` vazio
- Zip em `s3://codedeploy-artifacts-<account-id>/releases/v2/deploy-package.zip`

---
## Objetivo

Usando a infraestrutura do Lab 3A:
1. Configurar o CodeDeploy (IAM Role, Application, Deployment Group)
2. Executar um deploy Blue/Green (v1 → v2) e observar a troca de tráfego no ALB
3. Simular uma falha no `ValidateService` e observar o rollback automático

---
## Parte 1 — IAM Role do CodeDeploy

### Passo 1 — Criar a role `AWSCodeDeployRole`

**IAM → Roles → Create role:**

| Campo | Valor |
|---|---|
| Trusted entity type | **AWS service** |
| Use case | **CodeDeploy** (role for EC2/On-premises) |

> Ao escolher "CodeDeploy" como Use case, a política `AWSCodeDeployRole` já é adicionada automaticamente.

**Next** → Nome da role: `AWSCodeDeployRole` → **Create role**.

### Passo 2 — Adicionar inline policy complementar

A managed policy `AWSCodeDeployRole` **não inclui** todas as permissões necessárias para Blue/Green com ASG. Sem a policy abaixo o deploy falha na Etapa 1 com:

> *"The IAM role does not give you permission to perform operations in the following AWS service: AmazonAutoScaling"*

**O que falta e por quê:**

| Permission | Por que é necessária | Sintoma se ausente |
|---|---|---|
| `ec2:RunInstances` | O Auto Scaling usa essa action para lançar as instâncias Green via Launch Template | Etapa 1 falha: `AccessDenied` em `CreateAutoScalingGroup` (visível no CloudTrail) |
| `iam:CreateServiceLinkedRole` | Necessária caso o `AWSServiceRoleForAutoScaling` ainda não exista na conta | Etapa 1 falha: `implicitDeny` no IAM simulate |
| `autoscaling:Create/Delete*` | Para criar e destruir o ASG Green durante o deploy | Mensagem: *"role does not give permission to AmazonAutoScaling"* |
| `elasticloadbalancing:ModifyListener` | Para redirecionar o listener do ALB de `tg-blue` para `tg-green` no AllowTraffic | Etapa 3 (`AllowTraffic`) trava indefinidamente — instâncias Green ficam healthy mas listener nunca muda |
| `elasticloadbalancing:ModifyRule` | Para ajustar regras do listener durante o traffic shifting | Mesmo sintoma: AllowTraffic em andamento para sempre |

```powershell
aws iam put-role-policy `
  --role-name AWSCodeDeployRole `
  --policy-name CodeDeployAutoScalingBlueGreen `
  --policy-document file://C:\cursos\aws_developer_associate\secao_9_ci_cd_aws\anexos\lab3\codedeploy-autoscaling-policy.json
```

### Passo 3 — Adicionar inline policy para o ALB

A managed policy `AWSCodeDeployRole` também **não inclui** `elasticloadbalancing:ModifyListener` nem `ModifyRule`. Sem essas permissões o deploy chega na Etapa 3 (`AllowTraffic`), registra as instâncias Green no target group, mas **nunca consegue alterar o listener** — fica travado indefinidamente sem erro visível no console.

> **Como diagnosticar:** se o `AllowTraffic` passar de ~5 minutos, rode o simulate abaixo. Você verá `implicitDeny` para `ModifyListener`.

```powershell
aws iam put-role-policy `
  --role-name AWSCodeDeployRole `
  --policy-name CodeDeployALBListenerAccess `
  --policy-document file://C:\cursos\aws_developer_associate\secao_9_ci_cd_aws\anexos\lab3\codedeploy-alb-listener-policy.json
```

**Verificar se todas as permissões estão corretas:**

```powershell
aws iam simulate-principal-policy `
  --policy-source-arn arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/AWSCodeDeployRole `
  --action-names "autoscaling:CreateAutoScalingGroup" "ec2:RunInstances" "iam:CreateServiceLinkedRole" "elasticloadbalancing:ModifyListener" "elasticloadbalancing:ModifyRule" `
  --query "EvaluationResults[].{Action:EvalActionName,Decision:EvalDecision}" `
  --output table
```

Todas devem retornar `allowed`.

> **DVA-C02 — Mínimo privilégio:** dois arquivos de policy separados por responsabilidade — `codedeploy-autoscaling-policy.json` (ASG + EC2) e `codedeploy-alb-listener-policy.json` (ALB). A `AWSCodeDeployRole` managed policy cobre o restante.

---
## Parte 2 — Configurar CodeDeploy

### Passo 1 — Criar a Application

CodeDeploy → **Applications** → **Create application**:

| Campo | Valor |
|---|---|
| Application name | `demo-webapp` |
| Compute platform | `EC2/On-premises` |

### Passo 2 — Criar o Deployment Group

> **Como funciona o Blue/Green com ASG?** O CodeDeploy: (1) clona o `asg-blue-codedeploy` criando um ASG Green; (2) instala a v2 nas instâncias Green; (3) atualiza o listener do ALB para `tg-green`; (4) encerra o ASG Blue após 5 minutos.

CodeDeploy → Application `demo-webapp` → **Create deployment group**:

| Campo (PT-BR) | Valor | Por que |
|---|---|---|
| **Nome do grupo de implantação** | `demo-prod-bluegreen` | — |
| **Função de serviço** | `AWSCodeDeployRole` | gerencia EC2, ALB e ASG |
| **Tipo de implantação** | **Azul/verde** | dois ambientes paralelos |
| **Configuração do ambiente** | **Copiar automaticamente o grupo de Auto Scaling do Amazon EC2** | clona o ASG Blue para criar o Green |
| ↳ Auto Scaling group | `asg-blue-codedeploy` | — |
| **Redirecionamento do tráfego** | **Redirecionar o tráfego imediatamente** | — |
| **Instâncias originais** | ✅ Encerrar | dias: `0`, horas: `0`, minutos: `5` ⚠️ Atenção: coloque **minutos**, não horas — erro aqui causa Etapa 4 travada por 1h+ |
| **Configuração de implantação** | `CodeDeployDefault.AllAtOnce` | — |
| **Habilitar balanceamento de carga** | ✅ (fixo, não desmarcável em Blue/Green) | — |
| ↳ Tipo | **Application Load Balancer ou Network Load Balancer** | não usar Classic |
| ↳ Load balancer | `demo-codedeploy-alb` | — |
| ↳ Grupos de destino | ✅ `tg-blue` e ✅ `tg-green` | marque os dois — o CodeDeploy identifica produção e substituição pelo estado de cada TG. O console grava essa configuração como `targetGroupInfoList`, que é o formato correto para EC2/On-premises. O listener do ALB já deve ter ambos os TGs registrados (feito no Lab 3A, Passo 4) — sem isso a Etapa 3 trava indefinidamente. |
| **Reversões** | ✅ Habilitar → **Reverter quando uma implantação falhar** | — |

---
## Parte 3 — Executar o Deploy (v1 → v2)

### Passo 1 — Verificar pré-requisitos

```powershell
# Instâncias Blue com tag correto
aws ec2 describe-instances `
  --filters "Name=tag:Environment,Values=blue" "Name=instance-state-name,Values=running" `
  --query "Reservations[].Instances[].{ID:InstanceId,State:State.Name}" `
  --output table

# CodeDeploy Agent em cada instância (via Session Manager)
sudo systemctl status codedeploy-agent
# Esperado: active (running)
```

### Passo 2 — Criar o deployment

CodeDeploy → `demo-webapp` → **Create deployment**:

| Campo (PT-BR) | Valor |
|---|---|
| **Grupo de implantação** | `demo-prod-bluegreen` |
| **Tipo de revisão** | Meu aplicativo está armazenado no Amazon S3 |
| **Local de revisão** | `s3://codedeploy-artifacts-<account-id>/releases/v2/deploy-package.zip` |
| **Opções de conteúdo** | **Substituir o conteúdo** |

> **"Configuração do ambiente"** não precisa ser preenchida com ASG — o CodeDeploy já sabe qual é o Blue pelo ASG do Deployment Group.

Acompanhe as 4 etapas no console:
1. **Provisionar instâncias de substituição** — cria o ASG Green (2 instâncias)
2. **Instalação do aplicativo** — executa os lifecycle hooks nas instâncias Green
3. **Redirecionamento do tráfego** — ALB muda o listener de `tg-blue` para `tg-green`
4. **Encerramento de instâncias originais** — aguarda `terminationWaitTimeInMinutes` e encerra o ASG Blue

> **Etapa 3 travada em 0%?** Verifique se o listener do ALB tem `tg-green` registrado com peso 0 (Lab 3A, Passo 4). Esse é o motivo mais comum de travamento nessa etapa — o CodeDeploy não consegue executar o `ModifyListener` se o target group de destino não estiver previamente associado ao listener.

> **Por que tenho 4 instâncias rodando ao mesmo tempo?** É esperado. Após a Etapa 3 (tráfego já no Green), o CodeDeploy abre uma **janela de segurança** configurada no Deployment Group ("Instâncias originais → Encerrar → minutos"). Durante esse período as instâncias Blue permanecem ativas caso você precise reverter manualmente. Ao fim do prazo, o ASG Blue é encerrado automaticamente.
>
> **Quer reduzir a espera?** Execute o comando abaixo para sinalizar ao CodeDeploy que pode encerrar o Blue imediatamente, sem aguardar o prazo configurado:
>
> ```powershell
> aws deploy continue-deployment --deployment-id <DEPLOYMENT_ID> --deployment-wait-type TERMINATION_WAIT
> ```
>
> Substitua `<DEPLOYMENT_ID>` pelo ID visível no console (ex.: `d-XXXXXXX`). Só funciona **após** a Etapa 3 estar concluída (tráfego já no Green).

### Passo 3 — Verificar o resultado

```powershell
# Verificação principal — tráfego real pelo ALB
$ALB_DNS = aws elbv2 describe-load-balancers --names demo-codedeploy-alb --query 'LoadBalancers[0].DNSName' --output text
curl "http://$ALB_DNS"
# Esperado: "V2 - Green Environment - New Version!"

# Confirmar saúde dos TGs
aws elbv2 describe-target-health `
  --target-group-arn $(aws elbv2 describe-target-groups --names tg-green --query 'TargetGroups[0].TargetGroupArn' --output text) `
  --query "TargetHealthDescriptions[].{ID:Target.Id,State:TargetHealth.State}" --output table
# Esperado: 2 instâncias healthy

aws elbv2 describe-target-health `
  --target-group-arn $(aws elbv2 describe-target-groups --names tg-blue --query 'TargetGroups[0].TargetGroupArn' --output text) `
  --query "TargetHealthDescriptions[].{ID:Target.Id,State:TargetHealth.State}" --output table
# Esperado: vazio (após Etapa 4 concluída)
```

```bash
# Verificar diretamente na instância Green (Session Manager)
curl http://localhost:8080
# Esperado: "V2 - Green Environment"
```

---
## Parte 4 — Simular Falha e Rollback Automático

O objetivo é forçar uma falha no hook `ValidateService` e observar o rollback.

### Passo 1 — Criar pacote com falha e subir ao S3

```bash
cat > scripts/validate.sh << 'EOF'
#!/bin/bash
echo "Validation failed!"
exit 1
EOF
zip -r deploy-broken.zip app.py appspec.yml scripts/
aws s3 cp deploy-broken.zip s3://$BUCKET/releases/broken/deploy-broken.zip
```

```powershell
@"
#!/bin/bash
echo "Validation failed!"
exit 1
"@ | Set-Content scripts/validate.sh

Compress-Archive -Path app.py, appspec.yml, scripts -DestinationPath deploy-broken.zip -Force
$BUCKET = "codedeploy-artifacts-$(aws sts get-caller-identity --query Account --output text)"
aws s3 cp deploy-broken.zip s3://$BUCKET/releases/broken/deploy-broken.zip
```

### Passo 2 — Criar o deployment com falha

CodeDeploy → `demo-webapp` → **Create deployment**:

| Campo | Valor |
|---|---|
| Deployment group | `demo-prod-bluegreen` |
| S3 URL | `s3://codedeploy-artifacts-<account-id>/releases/broken/deploy-broken.zip` |

**O que observar:**
1. Etapa 2 falha — `ValidateService` retorna `exit 1`
2. Rollback disparado — listener do ALB **não é alterado** (falha ocorreu antes do rerouting)
3. ASG Green descartado — Blue permanece em produção

```powershell
# Confirmar que o Blue ainda está servindo
curl "http://$ALB_DNS"
# Esperado: ainda "V2 - Green Environment" (produção atual após o deploy anterior)
```

> **Por que não volta para V1?** O rollback reverte o *roteamento de tráfego*, não o código. Como o deploy anterior colocou a v2 como produção (Green se tornou o novo Blue após Etapa 4), o rollback mantém essa versão.

---
## Pontos de Atenção

- Rollback em Blue/Green = **redirecionamento de tráfego**, não reversão de código
- `appspec.yml` deve estar na **raiz** do zip
- `ApplicationStop` roda na versão *antiga*; demais hooks rodam na versão nova
- Logs do agente nas instâncias: `tail -f /var/log/aws/codedeploy-agent/codedeploy-agent.log`

---
## Limpeza

> **Mantenha a Application CodeDeploy `demo-webapp`** — usada no Lab 4 (CodePipeline).

```powershell
# Bucket S3
$BUCKET = "codedeploy-artifacts-$(aws sts get-caller-identity --query Account --output text)"
aws s3 rb s3://$BUCKET --force
```

```
# Via console:
# EC2 → Auto Scaling Groups → excluir asg-blue-codedeploy (e o ASG Green gerado pelo CodeDeploy)
# EC2 → Load Balancers → excluir demo-codedeploy-alb
# EC2 → Target Groups → excluir tg-blue e tg-green
# EC2 → Launch Templates → excluir lt-codedeploy-blue-green
# IAM → Roles → excluir EC2InstanceProfile-CodeDeploy e AWSCodeDeployRole
```
