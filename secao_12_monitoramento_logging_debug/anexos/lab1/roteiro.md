# Lab — CloudWatch Métricas, Dashboards e Alarmes

> **Compatibilidade de comandos CLI**
> Todos os comandos AWS CLI deste roteiro funcionam diretamente em **PowerShell** e **Bash** sem adaptação.
> A única exceção é a variável JSON para o dashboard (documentada com blocos separados).
> No Linux/macOS substitua `python` por `python3` onde necessário. CMD não é suportado.

> **Aviso de custos:** CloudWatch oferece Free Tier de 10 métricas customizadas, 10 alarmes e 1 milhão de requisições de API por mês (permanente). Este lab publica poucas métricas e fica dentro do Free Tier. Dashboards customizados têm custo de USD 3,00/mês cada após os primeiros 3 gratuitos. **Desprovisione ao finalizar.**

---
## Objetivo

Explorar métricas nativas do CloudWatch, criar um dashboard customizado, publicar métricas customizadas via CLI e Python, configurar um alarme com ação SNS e observar a diferença entre Standard e High-Resolution.

---
## Pré-requisitos

- AWS CLI configurada com credenciais válidas
- Python 3.x com `boto3`:

  ```shell
  pip install boto3
  ```

- Permissões IAM: `cloudwatch:PutMetricData`, `cloudwatch:GetMetricData`, `cloudwatch:PutDashboard`, `cloudwatch:PutMetricAlarm`, `sns:CreateTopic`, `sns:Subscribe`

---
## Parte 1 — Explorar Métricas Nativas no Console

1. Acesse **CloudWatch → Metrics → All metrics**.
2. Abra o namespace `AWS/Lambda` → dimensão `FunctionName` → selecione qualquer função existente.
3. Adicione ao gráfico as métricas: `Invocations`, `Errors`, `Duration`.
4. Altere o período para **1 minuto** e a estatística de `Duration` para **p99**.
5. Observe: **namespace** agrupa métricas de um serviço; **dimensão** filtra dentro do namespace; **estatística** define como os pontos são agregados.

---
## Parte 2 — Publicar Métrica Customizada via CLI

Publicar um único ponto:

```
aws cloudwatch put-metric-data --namespace "MeuCurso/Lab" --metric-name "PedidosSimulados" --value 42 --unit Count --dimensions "Ambiente=Dev"
```

Verificar se a métrica apareceu:

```
aws cloudwatch list-metrics --namespace "MeuCurso/Lab"
```

> A métrica pode levar até 1 minuto para aparecer no console após a primeira publicação.

Publicar mais pontos individualmente para gerar histórico (adapte para o seu terminal se quiser usar um loop):

```
aws cloudwatch put-metric-data --namespace "MeuCurso/Lab" --metric-name "PedidosSimulados" --value 10 --unit Count --dimensions "Ambiente=Dev"
aws cloudwatch put-metric-data --namespace "MeuCurso/Lab" --metric-name "PedidosSimulados" --value 25 --unit Count --dimensions "Ambiente=Dev"
aws cloudwatch put-metric-data --namespace "MeuCurso/Lab" --metric-name "PedidosSimulados" --value 50 --unit Count --dimensions "Ambiente=Dev"
aws cloudwatch put-metric-data --namespace "MeuCurso/Lab" --metric-name "PedidosSimulados" --value 15 --unit Count --dimensions "Ambiente=Dev"
aws cloudwatch put-metric-data --namespace "MeuCurso/Lab" --metric-name "PedidosSimulados" --value 38 --unit Count --dimensions "Ambiente=Dev"
```

---
## Parte 3 — Publicar Métrica via Python

O arquivo `put_metric_data.py` publica uma série de 10 pontos em Standard Resolution e depois 3 pontos em High-Resolution, demonstrando a diferença de granularidade.

```
python put_metric_data.py
```

> No Linux/macOS use `python3 put_metric_data.py` se necessário.

Após a execução, acesse **CloudWatch → Metrics → Custom namespaces → MeuCurso/Lab** e observe:
- Standard Resolution: granularidade mínima de 1 minuto no gráfico
- High-Resolution: granularidade de até 1 segundo (custo 5x maior)

---
## Parte 4 — Criar Dashboard no Console

1. Acesse **CloudWatch → Dashboards → Create dashboard** → nome: `Lab-CloudWatch-Dashboard`.
2. Adicione os widgets:
   - **Line** → `MeuCurso/Lab / PedidosSimulados` (dimensão `Ambiente=Dev`)
   - **Number** → `AWS/Lambda / Errors` (função existente qualquer)
3. Salve o dashboard.

Via CLI:

**PowerShell:**
```powershell
$dashBody = '{"widgets":[]}'
aws cloudwatch put-dashboard --dashboard-name "Lab-CloudWatch-Dashboard" --dashboard-body $dashBody
```

**Bash:**
```bash
DASH_BODY='{"widgets":[]}'
aws cloudwatch put-dashboard --dashboard-name "Lab-CloudWatch-Dashboard" --dashboard-body "$DASH_BODY"
```

> O comando acima cria um dashboard vazio; adicione os widgets pelo console ou via JSON completo de widgets.

---
## Parte 5 — Criar Alarme

Criar tópico SNS para receber notificações:

```
aws sns create-topic --name lab-cloudwatch-alarmes
```

Anote o ARN retornado (`arn:aws:sns:<REGION>:<ACCOUNT_ID>:lab-cloudwatch-alarmes`) e Subscribe com seu e-mail:

```
aws sns subscribe --topic-arn arn:aws:sns:<REGION>:<ACCOUNT_ID>:lab-cloudwatch-alarmes --protocol email --notification-endpoint seu@email.com
```

Confirme a subscription no e-mail recebido.

Criar o alarme (disparado quando `PedidosSimulados >= 45`):

```
aws cloudwatch put-metric-alarm --alarm-name "Lab-PedidosAltos" --namespace "MeuCurso/Lab" --metric-name "PedidosSimulados" --dimensions Name=Ambiente,Value=Dev --statistic Maximum --period 60 --evaluation-periods 1 --threshold 45 --comparison-operator GreaterThanOrEqualToThreshold --alarm-actions arn:aws:sns:<REGION>:<ACCOUNT_ID>:lab-cloudwatch-alarmes --treat-missing-data notBreaching
```

Publicar valor acima do threshold para disparar o alarme:

```
aws cloudwatch put-metric-data --namespace "MeuCurso/Lab" --metric-name "PedidosSimulados" --value 50 --unit Count --dimensions "Ambiente=Dev"
```

Aguarde ~1 minuto e verifique o estado:

```
aws cloudwatch describe-alarms --alarm-names "Lab-PedidosAltos" --query "MetricAlarms[0].{Estado:StateValue,Razao:StateReason}"
```

Publicar valor abaixo do threshold para retornar ao estado OK:

```
aws cloudwatch put-metric-data --namespace "MeuCurso/Lab" --metric-name "PedidosSimulados" --value 5 --unit Count --dimensions "Ambiente=Dev"
```

---
## Pontos de Verificação

- [ ] Métricas nativas Lambda (`Invocations`, `Errors`, `Duration`) visualizadas no console com p99
- [ ] Métrica `PedidosSimulados` publicada via CLI (namespace `MeuCurso/Lab`)
- [ ] Script `put_metric_data.py` executado — série visível no gráfico do CloudWatch
- [ ] Diferença entre Standard (60s) e High-Resolution (1s) observada no gráfico
- [ ] Dashboard `Lab-CloudWatch-Dashboard` criado com pelo menos 2 widgets
- [ ] Alarme `Lab-PedidosAltos` alternando entre `ALARM` e `OK` conforme os valores publicados

---
## Conceitos Reforçados

- **Namespace** agrupa métricas de um serviço ou aplicação; namespaces customizados ficam em "Custom namespaces"
- **Dimensão** é um par chave-valor que identifica o alvo da métrica — é obrigatória para diferenciar instâncias/funções
- **Standard Resolution** armazena com granularidade de 1 minuto; **High-Resolution** com 1 segundo (5x mais caro)
- Métricas CloudWatch têm retenção de **14 dias** em alta resolução e até **15 meses** em resolução reduzida (agregações de 1h+)
- `treat-missing-data notBreaching` evita alarmes falsos quando não há dados (ex: fora de horário)
- A **estatística** define como múltiplos pontos num período são combinados: Sum, Average, Maximum, Minimum, p99, etc.

---
## Cleanup

Deletar alarme:

```
aws cloudwatch delete-alarms --alarm-names "Lab-PedidosAltos"
```

Deletar dashboard:

```
aws cloudwatch delete-dashboards --dashboard-names "Lab-CloudWatch-Dashboard"
```

Deletar tópico SNS:

```
aws sns delete-topic --topic-arn arn:aws:sns:<REGION>:<ACCOUNT_ID>:lab-cloudwatch-alarmes
```

> Não há API para deletar namespaces de métricas customizadas. Os dados expiram automaticamente após 15 meses sem novos pontos.
