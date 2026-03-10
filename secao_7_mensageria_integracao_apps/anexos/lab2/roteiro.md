# Roteiro — Lab 2: Arquitetura Fanout com SNS + SQS

> **Aviso de compatibilidade de comandos**
> Os comandos deste roteiro sao referencias e podem precisar de adaptacao
> conforme o SO e terminal utilizados (PowerShell, Bash, Zsh, CMD, etc.).
> Converta a sintaxe antes de executar se necessario.
>
> Sugestao de prompt para IA generativa:
> "Converta o comando abaixo para meu SO [Windows/macOS/Linux] e terminal
> [PowerShell/Bash/Zsh/CMD]. Adapte variaveis, redirecionamentos e pipes
> para o equivalente nesse ambiente: <cole o comando aqui>"

## Custos e Free Tier

| Serviço | Free Tier |
|---------|-----------|
| SNS | 1 milhão de publicações/mês (permanente) |
| SQS | 1 milhão de requisições/mês (permanente) |

> **Aviso:** Recursos na nuvem podem gerar custos mesmo dentro do Free Tier, pois ele tem limites mensais e pode ser esgotado. Ao finalizar a prática, **desprovisione todos os recursos** para evitar cobranças inesperadas.

---
## Objetivo

Implementar o padrão Fanout: um tópico SNS distribui mensagens para duas filas SQS independentes. Uma das filas recebe apenas mensagens que passam por um Filter Policy (pedidos premium).

---
## Arquitetura

```
Publisher → SNS Topic: lab2-orders
                ├── SQS: lab2-processing  (sem filtro — recebe tudo)
                └── SQS: lab2-premium      (filtro: order_type = "premium")
```

---
## Recursos a Criar

| Recurso | Nome |
|---------|------|
| Fila SQS | `lab2-processing` |
| Fila SQS | `lab2-premium` |
| Tópico SNS | `lab2-orders` |

---
## Parte 1 — Criar as Filas SQS

Crie duas filas Standard no SQS com **Receive message wait time = 20**. Anote o **ARN** de cada uma.

---
## Parte 2 — Criar o Tópico SNS

Crie um tópico Standard com o nome `lab2-orders`. Anote o **ARN do tópico**.

---
## Parte 3 — Configurar Access Policy nas Filas

As filas precisam autorizar o SNS a enviar mensagens. Para **cada fila**, edite a Access Policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "sns.amazonaws.com"},
      "Action": "sqs:SendMessage",
      "Resource": "ARN_DA_FILA",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "ARN_DO_TOPICO_SNS"
        }
      }
    }
  ]
}
```

Substitua `ARN_DA_FILA` e `ARN_DO_TOPICO_SNS`. O arquivo `sqs-access-policy.json` desta pasta contém o template.

---
## Parte 4 — Criar Subscriptions no SNS

### Subscription 1 — Fila de processamento geral (sem filtro)

- Protocol: `Amazon SQS`
- Endpoint: ARN da fila `lab2-processing`
- **Enable raw message delivery: Yes**

### Subscription 2 — Fila premium (com Filter Policy)

- Protocol: `Amazon SQS`
- Endpoint: ARN da fila `lab2-premium`
- **Enable raw message delivery: Yes**
- **Subscription filter policy:** conteúdo do arquivo `sns-filter-policy.json`:

```json
{"order_type": ["premium"]}
```

---
## Parte 5 — Testar o Fanout

### Publicar pedido PREMIUM

No tópico SNS → *Publish message*:

- **Message attribute:** `order_type` | String | `premium`
- **Body:**
```json
{"order_id": "ORD-PREMIUM-001", "product": "MacBook Pro", "amount": 15000}
```

**Resultado esperado:**
- `lab2-processing` → recebe (sem filtro)
- `lab2-premium` → recebe (filtro satisfeito)

### Publicar pedido STANDARD

- **Message attribute:** `order_type` | String | `standard`
- **Body:**
```json
{"order_id": "ORD-STD-001", "product": "Mouse", "amount": 150}
```

**Resultado esperado:**
- `lab2-processing` → recebe
- `lab2-premium` → **não recebe** (filtro não satisfeito)

### Verificar mensagens

Para cada fila: acesse *Send and receive messages → Poll for messages* e confirme o comportamento esperado.

---
## Pontos de Atenção

- Fanout Pattern: cada fila processa **independentemente** — uma falha não afeta a outra
- Filter Policy é definida **por subscription**, não no tópico
- Subscriber **sem** Filter Policy recebe todas as mensagens
- Raw message delivery: envia só o body (sem o envelope JSON do SNS)
- A Access Policy na fila SQS é **obrigatória** — sem ela, o SNS recebe erro de acesso

---
## Limpeza

1. Delete as subscriptions do tópico `lab2-orders`
2. Delete o tópico `lab2-orders`
3. Delete as filas `lab2-processing` e `lab2-premium`
