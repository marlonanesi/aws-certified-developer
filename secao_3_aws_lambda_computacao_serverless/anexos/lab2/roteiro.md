# Lab 2 – Memória, Timeout e Variáveis de Ambiente

> **Compatibilidade de comandos CLI**
> Os comandos avulsos deste roteiro funcionam diretamente em **PowerShell** (Windows) e **Bash** (Linux/macOS/Git Bash) — basta colar e executar.
> Onde há diferença de sintaxe entre os dois shells, o roteiro apresenta as duas versões lado a lado.
> Para CMD ou outros terminais, converta a sintaxe com ajuda de IA generativa.

---
> **Custos e Free Tier**
> O AWS Lambda oferece **1 milhão de invocações gratuitas por mês** e **400.000 GB-segundos de computação** (nível permanente). Os experimentos de memória deste lab podem consumir mais GB-segundos, mas ainda dentro do free tier para volumes de teste.
> Fórmula de custo: `(memória em GB) × (duração em segundos)` = GB-segundos consumidos.
>
> ⚠️ **Aviso importante:** qualquer recurso provisionado na AWS pode gerar custos mesmo dentro do free tier, que possui limites mensais. Ao concluir o lab, execute a etapa de limpeza para evitar cobranças inesperadas.

---
## Objetivo

Explorar na prática as configurações de memória, timeout e variáveis de ambiente do Lambda, observando o impacto no desempenho e no custo via logs do CloudWatch.

---
## Pré-requisitos

- Conta AWS com permissões em Lambda e CloudWatch
- AWS CLI configurada

---
## Parte 1 – Criar a Função

1. Console → **Lambda → Create function** ("Criar função") **→ Author from scratch** ("Criar do zero")
2. **Function name:** `lambda-config-lab`
3. **Runtime:** Python 3.12
4. Cole o código do arquivo `lambda_config.py` incluído nesta pasta
5. **Deploy** ("Implantar")

---
## Parte 2 – Configurar Variáveis de Ambiente

1. **Configuration** ("Configuração") **→ Environment variables** ("Variáveis de ambiente") **→ Edit** ("Editar")
2. Adicione:

| Key | Value |
|---|---|
| `APP_ENV` | `producao` |
| `DB_HOST` | `meu-rds.cluster.us-east-1.rds.amazonaws.com` |
| `FEATURE_NOVA` | `true` |

3. **Save**

Execute um teste com `{"workload": "light"}` e observe essas variáveis nos logs do CloudWatch.

---
## Parte 3 – Experimento de Memória × Desempenho

O objetivo é comparar **tempo de execução** e **custo real** em diferentes configurações de memória.

### Experimento A – 128 MB

1. **Configuration → General configuration → Edit**
2. Memory: **128 MB** | Timeout: **30s** → Save
3. Execute: `{"workload": "heavy"}`
4. Anote no `REPORT` do CloudWatch: **Duration** e **Max Memory Used**

### Experimento B – 512 MB

1. Altere Memory para **512 MB** → Save
2. Execute: `{"workload": "heavy"}`
3. Anote **Duration** e **Max Memory Used**

### Experimento C – 1769 MB (1 vCPU completo)

1. Altere Memory para **1769 MB** → Save
2. Execute: `{"workload": "heavy"}`
3. Anote **Duration** e **Max Memory Used**

### Calcular o custo relativo

Use a fórmula: **(memória em GB) × (duração em segundos) = GB-segundos**

| Memória | Duration | GB-segundos | Observação |
|---|---|---|---|
| 128 MB (0,125 GB) | ? ms | ? | baseline |
| 512 MB (0,5 GB) | ? ms | ? | ? |
| 1769 MB (1,727 GB) | ? ms | ? | ? |

> **Conclusão possível:** mais memória = CPU mais rápida = duração menor. O custo final pode ser igual ou até menor com mais memória, dependendo do workload.

---
## Parte 4 – Testando o Timeout

1. Defina Memory: **128 MB**, Timeout: **3 segundos**
2. Execute: `{"workload": "heavy"}`
3. Se a função demorar mais de 3 s, o CloudWatch exibirá:
   ```
   Task timed out after 3.00 seconds
   ```
4. Aumente o timeout para **15 segundos** e re-execute — observe a conclusão normal

---
## Parte 5 – Variáveis Reservadas da AWS

Adicione temporariamente ao código estas linhas após os imports para visualizar as variáveis injetadas automaticamente pelo runtime:

```python
import os
print(os.environ.get('AWS_REGION'))
print(os.environ.get('AWS_LAMBDA_FUNCTION_NAME'))
print(os.environ.get('AWS_LAMBDA_FUNCTION_MEMORY_SIZE'))
print(os.environ.get('AWS_LAMBDA_FUNCTION_VERSION'))
```

Execute qualquer teste — essas variáveis existem sem nenhuma configuração manual.

---
## Pontos de Verificação

- O campo `Billed Duration` no `REPORT` é arredondado para cima em incrementos de 1 ms
- `Max Memory Used` indica o pico real — se muito próximo do limite, considere aumentar
- Variáveis de ambiente são visíveis em texto puro no console por padrão; para dados sensíveis, use KMS (visto na Seção 11)
- Não é possível definir `AWS_` como prefixo de variáveis customizadas — é reservado pela AWS

---
## Limpeza

```
aws lambda delete-function --function-name lambda-config-lab
```

> Funciona em Bash e PowerShell sem adaptação.
