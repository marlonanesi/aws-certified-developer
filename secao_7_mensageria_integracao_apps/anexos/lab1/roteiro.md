# Roteiro — Lab 1: Fila SQS com DLQ e Integração Lambda

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
| SQS | 1 milhão de requisições/mês (permanente) |
| Lambda | 1 milhão de invocações/mês + 400k GB-s (permanente) |
| CloudWatch Logs | 5 GB de ingestão/mês (primeiros 12 meses) |

> **Aviso:** Recursos na nuvem podem gerar custos mesmo dentro do Free Tier, pois ele tem limites mensais e pode ser esgotado. Ao finalizar a prática, **desprovisione todos os recursos** para evitar cobranças inesperadas.

---
## Objetivo

Criar uma fila SQS Standard com Dead Letter Queue (DLQ), configurar Long Polling e integrar com uma função Lambda via Event Source Mapping. Verificar o fluxo completo: mensagem → fila → Lambda → DLQ (em caso de falha).

---
## Recursos a Criar

| Recurso | Nome |
|---------|------|
| Fila DLQ | `lab1-dlq` |
| Fila Principal | `lab1-main-queue` |
| Função Lambda | `lab1-sqs-processor` |

> **Ordem importa:** crie a DLQ **antes** da fila principal.

---
## Parte 1 — Criar a DLQ

No console SQS, crie uma fila Standard com o nome `lab1-dlq`. Mantenha as configurações padrão. Anote o **ARN** da fila criada.

---
## Parte 2 — Criar a Fila Principal

Crie uma segunda fila Standard com o nome `lab1-main-queue`. Ajuste:

| Configuração | Valor |
|---|---|
| Visibility timeout | `60` segundos |
| Receive message wait time | `20` segundos ← **Long Polling** |
| Dead-letter queue | `lab1-dlq` |
| Maximum receives | `3` |

O campo **Receive message wait time = 20** ativa o Long Polling: o cliente espera até 20 segundos por mensagens antes de retornar vazio, reduzindo chamadas desnecessárias e custo.

---
## Parte 3 — Criar a Função Lambda

Crie uma Lambda com o nome `lab1-sqs-processor`, runtime **Python 3.12**. Use o código do arquivo `lambda_function.py` desta pasta.

**Permissão necessária:** na aba *Configuration → Permissions*, acesse a Execution Role e adicione a policy `AWSLambdaSQSQueueExecutionRole`.

---
## Parte 4 — Configurar Event Source Mapping

Na Lambda, clique em **Add trigger → SQS**. Configure:

| Campo | Valor |
|---|---|
| SQS queue | `lab1-main-queue` |
| Batch size | `5` |
| Batch window | `0` segundos |

O Event Source Mapping faz o Lambda escalar automaticamente à medida que a fila cresce.

---
## Parte 5 — Testar

### Mensagem válida

Acesse `lab1-main-queue → Send and receive messages`. Envie:

```json
{"order_id": "ORD-001", "product": "Notebook", "amount": 2999.90}
```

Verifique os logs em *Lambda → Monitor → View CloudWatch logs*.

### Mensagem inválida → DLQ

Envie **3 vezes** o conteúdo abaixo (corpo inválido para forçar falha):

```
INVALID_JSON_CONTENT
```

Após 3 falhas, acesse `lab1-dlq → Send and receive messages → Poll for messages`. A mensagem deve aparecer lá.

### Verificar Long Polling

Acesse `lab1-main-queue → Send and receive messages`. Observe o campo **Wait time: 20 seconds** — confirma que o Long Polling está ativo.

---
## Pontos de Atenção

- `ReceiveMessageWaitTimeSeconds > 0` ativa Long Polling (máximo: 20s)
- DLQ deve ser do **mesmo tipo** que a fila principal (Standard↔Standard, FIFO↔FIFO)
- `maxReceiveCount`: número de falhas antes de mover para a DLQ
- Visibility Timeout da fila deve ser **maior** que o timeout da Lambda
- Event Source Mapping: a Lambda escala automaticamente com o crescimento da fila

---
## Limpeza

1. Delete a Lambda `lab1-sqs-processor`
2. Delete as filas `lab1-main-queue` e `lab1-dlq`
3. Delete o log group `/aws/lambda/lab1-sqs-processor` no CloudWatch
