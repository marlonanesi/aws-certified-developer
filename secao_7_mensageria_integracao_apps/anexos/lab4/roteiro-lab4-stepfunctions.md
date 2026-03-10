# Roteiro — Lab 4: State Machine com AWS Step Functions

> **Aviso de compatibilidade de comandos**
> Os comandos deste roteiro são referências e podem precisar de adaptação
> conforme o SO e terminal utilizados (PowerShell, Bash, Zsh, CMD, etc.).
> Converta a sintaxe antes de executar se necessário.
>
> Sugestão de prompt para IA generativa:
> "Converta o comando abaixo para meu SO [Windows/macOS/Linux] e terminal
> [PowerShell/Bash/Zsh/CMD]. Adapte variáveis, redirecionamentos e pipes
> para o equivalente nesse ambiente: <cole o comando aqui>"

## Custos e Free Tier

| Serviço | Free Tier |
|---------|-----------|
| Step Functions (Standard Workflow) | 4.000 transições de estado/mês (permanente) |
| Lambda | 1 milhão de invocações/mês + 400k GB-s (permanente) |
| CloudWatch Logs | 5 GB de ingestão/mês (primeiros 12 meses) |

> **Aviso:** Recursos na nuvem podem gerar custos mesmo dentro do Free Tier, pois ele tem limites mensais e pode ser esgotado. Ao finalizar a prática, **desprovisione todos os recursos**. Standard Workflows são cobrados por **transição de estado** — cada execução deste lab usa ~5–7 transições.

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

Você tem **duas opções** para criar as 5 funções Lambda com runtime **Python 3.12**. O resultado é idêntico.

---

### Opção A — Script automatizado ✅ recomendado

Os scripts criam automaticamente a IAM Role básica para Lambda, fazem o zip de cada arquivo, criam as funções e exibem todos os ARNs ao final.

**Windows (PowerShell):**
```powershell
.\deploy-lambdas.ps1
```

**macOS / Linux / WSL (Bash):**
```bash
chmod +x deploy-lambdas.sh
./deploy-lambdas.sh
```

✅ Ao final, **copie todos os ARNs** exibidos no terminal — serão necessários na Parte 3.

---

### Opção B — Console AWS (manual)

**Lambda → Criar função → Criar do zero** — repita 5 vezes:

| Função | Arquivo | Handler |
|--------|---------|---------|
| `lab4-validate-order` | `lambda_validate_order.py` | `lambda_validate_order.lambda_handler` |
| `lab4-process-premium` | `lambda_process_premium.py` | `lambda_process_premium.lambda_handler` |
| `lab4-process-standard` | `lambda_process_standard.py` | `lambda_process_standard.lambda_handler` |
| `lab4-notify-customer` | `lambda_notify_customer.py` | `lambda_notify_customer.lambda_handler` |
| `lab4-finalize-order` | `lambda_finalize_order.py` | `lambda_finalize_order.lambda_handler` |

Para cada função:
- Runtime: **Python 3.12**
- Role: crie com `AWSLambdaBasicExecutionRole`
- Cole o conteúdo do arquivo correspondente no editor de código inline
- Clique em **Deploy** após colar o código

✅ Após criar cada função, anote o ARN em **Configuração → ARN da função**.

> **Atenção ao `lambda_finalize_order.py`:** o output do estado Parallel é uma **lista** — um resultado por branch. A função precisa tratar os dois formatos (lista vinda do Parallel e dict vindo do ProcessarStandard). Verifique se o código já contém o tratamento abaixo. Se não contiver, substitua o handler:
>
> ```python
> def lambda_handler(event, context):
>     # Parallel retorna lista — normaliza para dict
>     if isinstance(event, list):
>         merged = {}
>         for item in event:
>             if isinstance(item, dict):
>                 merged.update(item)
>         event = merged
>     return {"final_status": "COMPLETED", **event}
> ```
>
> Esse é um comportamento esperado do Step Functions: o estado Parallel sempre entrega seu output como array para o próximo estado.

---

## Parte 2 — Criar a IAM Role para Step Functions

O Step Functions precisa de permissão para invocar as Lambdas. Sem essa role, a execução falha no primeiro estado.

**Console → IAM → Funções → Criar perfil** (botão laranja)

### Etapa 1 — Selecionar entidade confiável:

- Selecione **"Serviço da AWS"**
- No campo de busca, digite `Step Functions`
- Selecione **Step Functions** na lista
- Clique em **Próximo**

### Etapa 2 — Adicionar permissões:

- Busque por `AWSLambdaRole`
- Marque o checkbox da política **`AWSLambdaRole`**
- Clique em **Próximo**

> A política `AWSLambdaRole` já vem pré-selecionada ao escolher Step Functions como entidade confiável — mantenha-a.

### Etapa 3 — Nomear e criar:

| Campo | Valor |
|---|---|
| Nome da função | `lab4-stepfunctions-role` |

Clique em **Criar função**.

✅ Após criar, abra a role e copie o **ARN** — formato:
```
arn:aws:iam::<ACCOUNT_ID>:role/lab4-stepfunctions-role
```

---

## Parte 3 — Criar a State Machine

**Console → Step Functions → Máquinas de estado → Criar máquina de estado**

O console abre um modal com duas opções:

| Campo | Valor |
|---|---|
| Método | **Criar do zero** |
| Nome | `lab4-order-workflow` |
| Tipo | **Padrão** ✅ |

Clique em **Continuar** — isso abre o **Workflow Studio**.

---

### No Workflow Studio

O console exibe três abas no topo: **Design**, **Código** e **Configuração**.

#### Aba "Código":

Clique na aba **Código**. O editor exibe o ASL padrão.

1. Selecione tudo (**Ctrl+A**)
2. Cole o conteúdo do arquivo `state-machine-definition.json`
3. **Substitua todos os placeholders** pelos ARNs reais:

| Placeholder | ARN da Lambda |
|---|---|
| `ARN_lab4-validate-order` | ARN de `lab4-validate-order` |
| `ARN_lab4-process-premium` | ARN de `lab4-process-premium` |
| `ARN_lab4-process-standard` | ARN de `lab4-process-standard` |
| `ARN_lab4-notify-customer` | ARN de `lab4-notify-customer` |
| `ARN_lab4-finalize-order` | ARN de `lab4-finalize-order` |

Após colar, clique em **Design** para visualizar o fluxo renderizado automaticamente — você verá o Choice, os dois branches do Parallel e o caminho de erro.

#### Aba "Configuração":

Clique na aba **Configuração** e localize a seção **Permissões**:

- Selecione **"Escolher uma função existente"**
- Escolha `lab4-stepfunctions-role`

#### Criar:

Clique em **Criar** (botão laranja no canto superior direito).

> Se aparecer o aviso vermelho **"Fluxo de trabalho não criado"**, verifique se a role está selecionada na aba Configuração antes de criar.

---

## Parte 4 — Executar e Observar

**Console → Step Functions → `lab4-order-workflow` → Iniciar execução**

---

### ✅ Teste 1 — Pedido PREMIUM

Input:
```json
{
  "order_id": "ORD-001",
  "amount": 5000,
  "order_type": "premium"
}
```

**O que observar na Visualização do gráfico:**

1. `ValidarPedido` → 🟢 verde
2. `VerificarTipo` → avalia `$.order_type == "premium"` → branch premium
3. `ProcessarPremiumComNotificacao` → **dois boxes executando simultaneamente** ← esse é o Parallel
4. `AguardarConfirmacao` → estado fica 🟡 laranja por 5 segundos
5. `FinalizarPedido` → 🟢 verde — execução concluída com `SUCCEEDED`

> **Comportamento esperado do Parallel:** os branches `ProcessarPremium` e `NotificarCliente` executam ao mesmo tempo. O Step Functions só avança para `AguardarConfirmacao` depois que **ambos** completam. Se um falhar, o Parallel inteiro falha.

---

### 🔀 Teste 2 — Pedido STANDARD

Input:
```json
{
  "order_id": "ORD-002",
  "amount": 150,
  "order_type": "standard"
}
```

**O que observar:**

O `VerificarTipo` avalia `$.order_type` — não bate com `"premium"`, cai no `Default` e vai direto para `ProcessarStandard`, sem o estado Parallel.

---

## Parte 5 — Analisar a Execução

Na execução concluída, o console oferece três visões — explore todas:

### Visualização do gráfico

Estados coloridos conforme legenda na tela:
- 🟢 **Com êxito** — estado completou com sucesso
- 🔴 **Com falha** — estado falhou (após retries esgotados)
- 🟠 **Erro detectado** — falhou mas foi tratado pelo Catch
- 🟡 **Em andamento** — estado ainda em execução (visível no Wait)

Clique em qualquer estado para ver o **input e output** daquele step no painel direito — útil para entender como o payload é transformado a cada transição.

### Eventos

Histórico completo de cada transição com timestamp preciso. Use para debugging: você vê exatamente em qual estado a execução parou e qual foi o erro.

### Input/Output por estado

Observe como o output de um estado vira o input do próximo. No caminho premium, o output do Parallel é uma **lista com dois objetos** — um de cada branch. O `FinalizarPedido` recebe e mescla essa lista.

---

### 💥 Bônus — Observar Retry em ação

O `ValidarPedido` tem **10% de chance de falhar** intencionalmente. Se ocorrer:

- Observe o estado ficando vermelho, depois reiniciando — isso é o **Retry com backoff exponencial**
- 1ª falha: aguarda 2s → 2ª falha: aguarda 4s → 3ª falha: aguarda 8s
- Após a 3ª falha: o **Catch** redireciona para `PedidoInvalido` com status `FAILED`

> Tudo isso sem uma linha de try/catch no código da Lambda — está declarado no ASL com `IntervalSeconds`, `MaxAttempts` e `BackoffRate`.

Para forçar o erro e ver o Retry garantidamente, edite temporariamente a `lab4-validate-order` para sempre lançar uma exceção, execute, observe, e depois reverta.

---

## Pontos de Atenção

- **Standard Workflow:** exactly-once, duração até 1 ano, cobrado por transição de estado — ideal para processos de negócio
- **Express Workflow:** at-least-once, duração até 5 minutos, alto throughput, cobrado por GB-s — ideal para alto volume e curta duração
- **Retry declarativo no ASL:** `IntervalSeconds`, `MaxAttempts`, `BackoffRate` — sem código no Lambda
- **Catch:** captura erros após retries esgotados e desvia para estado de fallback — não lança exceção para fora
- **Parallel:** output é sempre uma **lista** — o próximo estado recebe um array com um resultado por branch
- **Choice State:** não tem `Next` direto — sempre sai por uma condição ou pelo `Default`
- **Map:** processa cada item de uma lista de forma dinâmica — diferente do Parallel, que executa branches fixos definidos no ASL
- **Wait com callback token:** permite aprovação humana — a execução pausa até alguém chamar `SendTaskSuccess` com o `taskToken`
- **`End: true`** marca o estado final de um caminho — obrigatório em cada branch do Parallel

---

## Limpeza

1. **Step Functions** → exclui `lab4-order-workflow`
2. **Lambda** → exclui as 5 funções: `lab4-validate-order`, `lab4-process-premium`, `lab4-process-standard`, `lab4-notify-customer`, `lab4-finalize-order`
3. **IAM** → exclui `lab4-stepfunctions-role` e `lab4-lambda-basic-role` (esta última criada pelo script, se usou a Opção A)
4. **CloudWatch → Grupos de logs** → exclui os log groups das 5 Lambdas (`/aws/lambda/lab4-*`)
