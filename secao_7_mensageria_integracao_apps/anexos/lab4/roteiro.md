# Roteiro — Lab 4: State Machine com AWS Step Functions

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
| Step Functions (Standard Workflow) | 4.000 transições de estado/mês (permanente) |
| Lambda | 1 milhão de invocações/mês + 400k GB-s (permanente) |
| CloudWatch Logs | 5 GB de ingestão/mês (primeiros 12 meses) |

> **Aviso:** Recursos na nuvem podem gerar custos mesmo dentro do Free Tier, pois ele tem limites mensais e pode ser esgotado. Ao finalizar a prática, **desprovisione todos os recursos** para evitar cobranças inesperadas. Standard Workflows são cobrados por **transição de estado** — cada execução deste lab usa ~5–7 transições.

---
## Objetivo

Criar uma state machine que processa pedidos com Choice (roteamento), Parallel (execução simultânea), Wait, Retry e Catch declarativos. Observar o fluxo visual em tempo real no console.

---
## Arquitetura do Workflow

```
[ValidarPedido] → [VerificarTipo: premium?]
                        ├── Sim → [Parallel: ProcessarPremium + NotificarCliente]
                        └── Não → [ProcessarStandard]
                              ↓
                   [AguardarConfirmacao: 5s]
                              ↓
                   [FinalizarPedido]
```

Em caso de falha persistente em `ValidarPedido` (após 3 retries): `→ [PedidoInvalido: Fail]`

---
## Parte 1 — Criar as Funções Lambda

Você tem **duas opções** para criar as 5 funções Lambda com runtime **Python 3.12**. Escolha a que preferir — o resultado é idêntico.

---

### Opção A — Script automatizado (recomendado para agilidade)

Os scripts criam automaticamente a IAM Role básica para Lambda, fazem o zip de cada arquivo, criam (ou atualizam) as funções e exibem todos os ARNs ao final.

**Windows (PowerShell):**
```powershell
.\deploy-lambdas.ps1
```

**macOS / Linux / WSL (Bash):**
```bash
chmod +x deploy-lambdas.sh
./deploy-lambdas.sh
```

Ao final, o script exibe os ARNs no terminal. **Copie-os** — serão usados na Parte 3.

---

### Opção B — Console AWS (manual)

Crie 5 funções Lambda manualmente em **Lambda → Create function → Author from scratch**:

| Função | Arquivo | Handler |
|--------|---------|---------|
| `lab4-validate-order` | `lambda_validate_order.py` | `lambda_validate_order.lambda_handler` |
| `lab4-process-premium` | `lambda_process_premium.py` | `lambda_process_premium.lambda_handler` |
| `lab4-process-standard` | `lambda_process_standard.py` | `lambda_process_standard.lambda_handler` |
| `lab4-notify-customer` | `lambda_notify_customer.py` | `lambda_notify_customer.lambda_handler` |
| `lab4-finalize-order` | `lambda_finalize_order.py` | `lambda_finalize_order.lambda_handler` |

Para cada função: runtime **Python 3.12**, role com `AWSLambdaBasicExecutionRole`. Cole o conteúdo do arquivo correspondente no editor de código inline.

Após criar todas, **anote o ARN de cada uma** (visível em *Configuration → Function ARN*).

---

---
## Parte 2 — Criar a IAM Role para Step Functions

IAM → Roles → **Create role** ("Criar função"):

| Campo | Valor |
|---|---|
| Trusted entity | AWS service → Step Functions |
| Policy | `AWSLambdaRole` |
| Nome | `lab4-stepfunctions-role` |

Anote o **ARN da role**.

---
## Parte 3 — Criar a State Machine

Step Functions → State machines → **Create state machine**:

| Campo | Valor |
|---|---|
| Authoring method | Write your workflow in code |
| Type | Standard |
| Nome | `lab4-order-workflow` |
| Permissions | Existing role → `lab4-stepfunctions-role` |

Cole o conteúdo do arquivo `state-machine-definition.json` no campo de definição ASL. **Substitua todos os placeholders** `ARN_lab4-*` pelos ARNs reais das Lambdas criadas no Parte 1.

---
## Parte 4 — Executar e Observar

### Pedido PREMIUM

State machine → **Start execution** → Input:

```json
{
  "order_id": "ORD-001",
  "amount": 5000,
  "order_type": "premium"
}
```

Observe o **visual workflow**: ValidarPedido → VerificarTipo → ProcessarPremiumComNotificacao (Parallel simultâneo) → AguardarConfirmacao (5s) → FinalizarPedido.

### Pedido STANDARD

```json
{
  "order_id": "ORD-002",
  "amount": 150,
  "order_type": "standard"
}
```

Observe o caminho alternativo: sem o estado Parallel, vai direto para ProcessarStandard.

---
## Parte 5 — Analisar a Execução

Na execução concluída, explore:

- **Graph view:** fluxo visual com estados coloridos (verde = sucesso, vermelho = falha)
- **Events:** histórico completo de cada transição com timestamp
- **Input/Output por estado:** clique em cada step para ver o payload transformado

O `ValidarPedido` tem 10% de chance de falhar — se ocorrer, observe o **Retry** com backoff exponencial (2s → 4s → 8s). Após 3 falhas, o Catch redireciona para `PedidoInvalido`.

---
## Pontos de Atenção

- **Standard Workflow:** exactly-once, duração até 1 ano, cobrado por transição de estado
- **Express Workflow:** at-least-once, duração até 5 minutos, alto throughput, cobrado por GB-s
- **Retry declarativo no ASL:** `IntervalSeconds`, `MaxAttempts`, `BackoffRate`
- **Catch:** captura erros e desvia para estado de fallback (não lança exceção para fora)
- **Parallel:** todos os branches devem completar antes de avançar para o próximo estado
- **Map:** processa cada item de uma lista (diferente do Parallel, que executa branches fixos)
- **Wait com callback token:** permite aprovação humana (`taskToken` + `SendTaskSuccess`)

---
## Limpeza

1. Delete a state machine `lab4-order-workflow`
2. Delete as Lambdas: `lab4-validate-order`, `lab4-process-premium`, `lab4-process-standard`, `lab4-notify-customer`, `lab4-finalize-order`
3. Delete as IAM roles `lab4-stepfunctions-role` e `lab4-lambda-basic-role` (esta última criada pelo script, se usou a Opção A)
4. Delete os log groups das Lambdas no CloudWatch
