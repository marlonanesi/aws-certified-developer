# Roteiro — Lab 3: Regras e Eventos no Amazon EventBridge

> **Compatibilidade de comandos CLI**
> Este roteiro inclui comandos que funcionam diretamente em **Bash** (Linux/macOS/Git Bash) e **PowerShell** (Windows).
> Para a Parte 6 (publicação de eventos), use `put-events.sh` (Bash) ou `put-events.ps1` (PowerShell) — ambos estão nesta pasta.
> Caso precise de execução em CMD, converta a sintaxe com ajuda de IA generativa:
> "Converta o comando abaixo para meu SO [Windows/macOS/Linux] e terminal [PowerShell/Bash/Zsh/CMD]."

## Custos e Free Tier

| Serviço | Free Tier |
|---------|-----------|
| EventBridge (eventos customizados) | Primeiros 5 milhões de eventos/mês gratuitos |
| SQS | 1 milhão de requisições/mês (permanente) |
| CloudWatch Logs | 5 GB de ingestão/mês (primeiros 12 meses) |

> **Aviso:** Recursos na nuvem podem gerar custos mesmo dentro do Free Tier. Ao finalizar a prática, **desprovisione todos os recursos**. Scheduled Rules ativas continuam gerando eventos a cada ciclo mesmo sem consumidores.

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

**Console → EventBridge → Barramentos de eventos → Criar barramento de eventos**

- Nome: `lab3-bus`
- Restante: padrão

✅ Anote o nome — você vai referenciá-lo nas regras e nos comandos CLI.

---

## Parte 2 — Criar a Fila SQS Target

**Console → SQS → Criar fila**

| Campo | Valor |
|---|---|
| Tipo | Standard |
| Nome | `lab3-events-queue` |
| **Tempo de espera do recebimento da mensagem** | **20 segundos** |
| Restante | padrão |

✅ Anote o **ARN** da fila — disponível na aba *Detalhes* logo após a criação.

### Configurar Access Policy da fila

A fila precisa autorizar o EventBridge a escrever nela. Sem isso, o evento é descartado silenciosamente.

**Console → SQS → `lab3-events-queue` → aba *Política de acesso* → Editar**

Cole o JSON abaixo substituindo `ARN_DA_FILA` pelo ARN real:

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

> **Nota:** o principal aqui é `events.amazonaws.com` — diferente do Lab 2 (SNS), que usava `sns.amazonaws.com`. Cada serviço tem seu próprio identificador.

---

## Parte 3 — Criar o Log Group

**Console → CloudWatch → Logs → Gerenciamento de logs → Criar grupo de logs**

| Campo | Valor |
|---|---|
| **Nome do grupo de logs** | `/lab3/scheduled-events` |
| **Configuração de retenção** | **1 dia** |
| Classe de log | Padrão |

> **Atenção ao nome:** use exatamente `/lab3/scheduled-events` com as barras. O console PT-BR chama o campo de *"Nome do grupo de logs"*.

---

## Parte 4 — Rule 1: Event Pattern (Pedidos Confirmados)

**Console → EventBridge → Regras → Criar regra**

> **Atenção — construtor visual:** o console abre automaticamente um construtor visual com drag-and-drop. Você vai usar a aba **Configurar** para definir o nome e barramento, e a aba **Construir** para montar o Event Pattern.

### Aba "Configurar":

| Campo | Valor |
|---|---|
| Nome | `lab3-order-rule` |
| Barramento de eventos | `lab3-bus` |
| Ativação | Ativo ✅ |

### Aba "Construir" — bloco "Acionando eventos":

1. Clique no **+** do bloco **"Acionando eventos"** (lado esquerdo do canvas)
2. Na lista lateral, **não selecione** nenhum dos eventos sugeridos (EC2, GuardDuty etc.)
3. Selecione **"Eventos personalizados"**
4. No campo **"(filtro) Padrão de evento"**, cole:

```json
{
  "source": ["lab3.orders"],
  "detail-type": ["OrderPlaced"],
  "detail": {
    "status": ["confirmed"]
  }
}
```

> **Se aparecer o modal "Discrepância detectada":** o console detectou diferença entre o bloco visual e o JSON. Marque o checkbox **"Substitua Eventos acionadores pela origem do evento e pelo tipo de detalhe definidos no (filtro) Padrão de evento"** e clique em **"Aceitar alteração"**. O bloco visual vai atualizar para mostrar `lab3.orders / OrderPlaced`.

### Aba "Destinos" — bloco "Destinos":

1. Clique no **+** do bloco **"Destinos"** (lado direito do canvas)
2. Na lista lateral, clique em **"Fila do SQS"**
3. Selecione `lab3-events-queue`

Clique em **Criar** (botão laranja).

---

## Parte 5 — Rule 2: Scheduled Rule

> **Pegadinha de prova:** Scheduled Rules usam **obrigatoriamente o Default event bus**. Não existe agendamento em custom bus — o console não permite.

**Console → EventBridge → Regras → Criar regra**

> **Atenção — construtor visual:** o console vai abrir novamente o construtor visual de eventos, que **não serve para agendamento**. Procure o banner azul no topo da tela com o texto:
> *"Se você quiser criar uma regra programada, use o **construtor de regras programadas**"*
> Clique nesse link. Ele abre um fluxo em etapas completamente diferente.

### Etapa 1 — Detalhe da regra programada:

| Campo | Valor |
|---|---|
| Nome | `lab3-scheduled-rule` |
| Barramento de eventos | `default` (fixo — não é possível alterar) |
| Ativação | Ativo ✅ |

> Ignore o banner azul sobre o **EventBridge Scheduler** — é um serviço diferente e mais novo. Para este lab, clique em **Próximo** sem entrar nele.

### Etapa 2 — Definir programação:

Selecione **"Taxa de frequência"**:

| Campo | Valor |
|---|---|
| Valor | `5` |
| Unidade | `Minutos` |

### Etapa 3 — Selecionar destinos:

- Selecione **"Grupo de logs do CloudWatch"**
- Escolha `/lab3/scheduled-events`

Avance até **Etapa 5 → Revisar e criar**.

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

### Ou execute os comandos diretamente

**Evento 1 — `status=confirmed` (deve chegar na fila SQS):**

```
aws events put-events --entries '[{"Source":"lab3.orders","DetailType":"OrderPlaced","Detail":"{\"order_id\":\"ORD-001\",\"status\":\"confirmed\",\"amount\":500}","EventBusName":"lab3-bus"}]'
```

Resultado esperado no terminal:
```json
{
    "FailedEntryCount": 0,
    "Entries": [{"EventId": "..."}]
}
```

> `FailedEntryCount: 0` confirma que o EventBridge **aceitou** o evento no bus. A regra ainda precisa avaliar o pattern antes de entregar na fila.

**Evento 2 — `status=pending` (NÃO deve chegar na fila SQS):**

```
aws events put-events --entries '[{"Source":"lab3.orders","DetailType":"OrderPlaced","Detail":"{\"order_id\":\"ORD-002\",\"status\":\"pending\",\"amount\":200}","EventBusName":"lab3-bus"}]'
```

> O terminal retorna `FailedEntryCount: 0` novamente — o evento foi aceito no bus, mas o EventBridge avaliou o pattern, não houve match com `status=confirmed` e o evento foi **descartado silenciosamente**. A fila nunca o recebeu.

### Verificar na fila

**Console → SQS → `lab3-events-queue` → *Enviar e receber mensagens* → *Sondar mensagens***

✅ Apenas o ORD-001 deve aparecer. O ORD-002 foi descartado pelo EventBridge.

### Alternativa: publicar via Console do EventBridge

**EventBridge → Barramentos de eventos → `lab3-bus` → Enviar eventos**

| Campo | Valor |
|---|---|
| Origem do evento | `lab3.orders` |
| Tipo de detalhe | `OrderPlaced` |
| Detalhe | `{"order_id": "ORD-003", "status": "confirmed", "amount": 1500}` |

---

## Parte 7 — Verificar Scheduled Rule

Aguarde até **5 minutos** e acesse:

**Console → CloudWatch → Logs → Gerenciamento de logs → `/lab3/scheduled-events`**

Devem aparecer log streams com entradas automáticas geradas pelo EventBridge a cada ciclo.

> **Importante:** a Scheduled Rule escreve no Log Group independentemente dos eventos que você publicou via CLI. As duas regras são completamente independentes — a Rule 1 reage a eventos no `lab3-bus`, a Rule 2 dispara por tempo no `default bus`.

---

## Pontos de Atenção

- Event Pattern filtra por **conteúdo** do evento (JSON matching) — diferente do SNS que filtra por atributos externos
- Scheduled Rules usam **obrigatoriamente o Default event bus** — o console não permite selecionar custom bus
- Eventos que não batem em nenhuma regra são **descartados silenciosamente** — para capturá-los, crie uma regra "catch-all" sem filtro apontando para um Log Group ou SQS de auditoria
- Máximo de **5 targets por rule**
- A resource policy na fila SQS é **obrigatória** — sem ela o EventBridge recebe erro e o evento é perdido
- `FailedEntryCount: 0` no CLI indica que o evento chegou ao bus, não que foi entregue ao target

---

## Limpeza

> **Importante:** delete a Scheduled Rule primeiro — ela está ativa e continua gerando eventos a cada 5 minutos.

1. **EventBridge → Regras** → exclui `lab3-scheduled-rule`
2. **EventBridge → Regras** → exclui `lab3-order-rule`
3. **EventBridge → Barramentos de eventos** → exclui `lab3-bus`
4. **SQS** → exclui `lab3-events-queue`
5. **CloudWatch → Grupos de logs** → exclui `/lab3/scheduled-events`
