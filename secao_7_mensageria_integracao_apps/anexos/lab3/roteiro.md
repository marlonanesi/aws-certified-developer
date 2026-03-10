# Roteiro — Lab 3: Regras e Eventos no Amazon EventBridge

> **Compatibilidade de comandos CLI**
> Este roteiro inclui comandos que funcionam diretamente em **Bash** (Linux/macOS/Git Bash) e **PowerShell** (Windows).
> Para a Parte 6 (publicação de eventos), use `put-events.sh` (Bash) ou `put-events.ps1` (PowerShell) — ambos estão nesta pasta.
> Caso precise de execução em CMD, converta a sintaxe com ajuda de IA generativa.

## Custos e Free Tier

| Serviço | Free Tier |
|---------|-----------|
| EventBridge (eventos customizados) | Primeiros 5 milhões de eventos/mês gratuitos |
| SQS | 1 milhão de requisições/mês (permanente) |
| CloudWatch Logs | 5 GB de ingestão/mês (primeiros 12 meses) |

> **Aviso:** Recursos na nuvem podem gerar custos mesmo dentro do Free Tier, pois ele tem limites mensais e pode ser esgotado. Ao finalizar a prática, **desprovisione todos os recursos** para evitar cobranças inesperadas. Scheduled Rules que permanecem ativas continuam gerando eventos a cada ciclo.

---
## Objetivo

Criar um Event Bus customizado, publicar eventos via CLI, criar regras com Event Pattern e Scheduled Rule, e rotear eventos para targets (SQS e CloudWatch Logs).

---
## Arquitetura

```
CLI → Custom Event Bus (lab3-bus)
          ├── Rule 1 (Event Pattern: status=confirmed) → SQS Queue
          └── Rule 2 (Schedule: rate 5min)             → CloudWatch Log Group
```

---
## Recursos a Criar

| Recurso | Nome |
|---------|------|
| Custom Event Bus | `lab3-bus` |
| Fila SQS | `lab3-events-queue` |
| Log Group | `/lab3/scheduled-events` |
| Rule 1 | `lab3-order-rule` |
| Rule 2 | `lab3-scheduled-rule` |

---
## Parte 1 — Criar o Custom Event Bus

EventBridge → Event buses → **Create event bus** → Nome: `lab3-bus`.

---
## Parte 2 — Criar a Fila SQS Target

Crie uma fila Standard `lab3-events-queue` com **Receive message wait time = 20**. Anote o **ARN**.

Em seguida, edite a Access Policy da fila para permitir que o EventBridge envie mensagens:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "events.amazonaws.com"},
    "Action": "sqs:SendMessage",
    "Resource": "ARN_DA_FILA"
  }]
}
```

O template está no arquivo `sqs-resource-policy.json` desta pasta. Substitua `ARN_DA_FILA`.

---
## Parte 3 — Criar Log Group

CloudWatch → Log groups → **Create log group**:
- Nome: `/lab3/scheduled-events`
- Retention: `1 day`

---
## Parte 4 — Rule 1: Event Pattern (Pedidos Confirmados)

EventBridge → Rules → **Create rule** ("Criar regra"):

| Campo | Valor |
|---|---|
| Nome | `lab3-order-rule` |
| Event bus | `lab3-bus` |
| Rule type | Rule with an event pattern |
| Event source | Other |
| Event pattern | (conteúdo do arquivo `event-pattern.json`) |
| Target | SQS queue → `lab3-events-queue` |

```json
{
  "source": ["lab3.orders"],
  "detail-type": ["OrderPlaced"],
  "detail": {
    "status": ["confirmed"]
  }
}
```

---
## Parte 5 — Rule 2: Scheduled Rule

**Create rule** ("Criar regra") (atenção: Scheduled Rules usam o **Default event bus**, não custom):

| Campo | Valor |
|---|---|
| Nome | `lab3-scheduled-rule` |
| Event bus | **default** |
| Rule type | Schedule |
| Rate | `5 minutes` |
| Target | CloudWatch log group → `/lab3/scheduled-events` |

---
## Parte 6 — Publicar Eventos via CLI

### Usando os scripts desta pasta

**Bash / Git Bash:**
```bash
bash put-events.sh
```

**PowerShell (Windows):**
```powershell
.\put-events.ps1
```

### Ou execute os comandos diretamente (funciona em Bash e PowerShell)

**Evento 1 — `status=confirmed` (deve chegar na fila SQS):**
```
aws events put-events --entries '[{"Source":"lab3.orders","DetailType":"OrderPlaced","Detail":"{\"order_id\":\"ORD-001\",\"status\":\"confirmed\",\"amount\":500}","EventBusName":"lab3-bus"}]'
```

**Evento 2 — `status=pending` (não deve chegar na fila SQS):**
```
aws events put-events --entries '[{"Source":"lab3.orders","DetailType":"OrderPlaced","Detail":"{\"order_id\":\"ORD-002\",\"status\":\"pending\",\"amount\":200}","EventBusName":"lab3-bus"}]'
```

Após cada envio, acesse `lab3-events-queue → Send and receive messages → Poll for messages` para verificar.

### Via Console

EventBridge → Event buses → `lab3-bus` → **Send events**:
- Event source: `lab3.orders`
- Detail type: `OrderPlaced`
- Detail: `{"order_id": "ORD-003", "status": "confirmed", "amount": 1500}`

---
## Parte 7 — Verificar Scheduled Rule

Aguarde até 5 minutos e acesse CloudWatch → Log groups → `/lab3/scheduled-events`. Deve haver log streams com os eventos agendados.

---
## Pontos de Atenção

- Event Pattern filtra por **conteúdo** do evento (JSON matching)
- Scheduled Rules usam o **Default event bus** — nunca custom bus
- Máximo de **5 targets por rule**
- Custom Event Bus isola domínios de negócio
- EventBridge ≠ SNS: EventBridge filtra conteúdo, SNS filtra atributos da mensagem
- A resource policy na fila SQS é **obrigatória** para permitir que o EventBridge envie

---
## Limpeza

1. Delete as rules: `lab3-order-rule` e `lab3-scheduled-rule`
2. Delete o event bus `lab3-bus`
3. Delete a fila `lab3-events-queue`
4. Delete o log group `/lab3/scheduled-events`
