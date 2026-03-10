# Lab 4 – API Key e Usage Plans

> **Aviso de compatibilidade de comandos**
> Os comandos deste roteiro sao referencias e podem precisar de adaptacao
> conforme o SO e terminal utilizados (PowerShell, Bash, Zsh, CMD, etc.).
> Converta a sintaxe antes de executar se necessario.
>
> Sugestao de prompt para IA generativa:
> "Converta o comando abaixo para meu SO [Windows/macOS/Linux] e terminal
> [PowerShell/Bash/Zsh/CMD]. Adapte variaveis, redirecionamentos e pipes
> para o equivalente nesse ambiente: <cole o comando aqui>"

---
> **Custos e Free Tier**
> - **Amazon API Gateway REST API:** 1 milhão de chamadas gratuitas/mês nos **primeiros 12 meses**
> - **Usage Plans e API Keys:** sem custo adicional — fazem parte do API Gateway
> - **AWS Lambda:** 1 milhão de invocações gratuitas/mês (nível permanente)
>
> ⚠️ **Aviso importante:** qualquer recurso provisionado na AWS pode gerar custos mesmo dentro do free tier, que possui limites mensais. Ao concluir o lab, execute a etapa de limpeza para evitar cobranças inesperadas.
>
> ⚠️ **Usage Plans e API Keys funcionam apenas com REST APIs** — não com HTTP APIs.

---
## Objetivo

Criar **API Keys** e **Usage Plans** para controlar o acesso e os limites de uso por cliente, demonstrando:
1. Acesso bloqueado sem API Key (403)
2. Throttling por plano (429 ao exceder limite)
3. Hierarquia de throttling: conta → stage → usage plan → método

---
## Arquitetura

```
Sem API Key          → 403 Forbidden
API Key (free-tier)  → Rate: 1 req/s  | Quota: 100/dia  → 200 OK (até o limite)
API Key (premium)    → Rate: 100 req/s | Quota: 10k/dia  → 200 OK
```

---
## Pré-requisitos

- Lab 1 concluído (API `lab1-hello-api` com método GET `/hello`)
- `curl` ou ferramenta similar disponível

---
## Parte 1 – Exigir API Key no Método

1. API Gateway → método **GET** em `/hello` → **Method Request**
2. **API Key Required** → editar → selecionar **true** → confirmar
3. Repita para quaisquer outros métodos que devam exigir chave

> Mudanças no método precisam de deploy para ter efeito.

---
## Parte 2 – Criar Usage Plans

### Usage Plan "free-tier"

1. **Usage Plans → Create**
2. Configurações:
   - **Name:** `free-tier`
   - **Enable throttling:** ✅ | Rate: 1 req/s | Burst: 2
   - **Enable quota:** ✅ | 100 requests por **Day**
3. **Next → Add API Stage** → selecione sua API → Stage: `dev` → confirmar → **Next**

### Usage Plan "premium"

1. **Usage Plans → Create**
2. Configurações:
   - **Name:** `premium`
   - **Enable throttling:** ✅ | Rate: 100 req/s | Burst: 200
   - **Enable quota:** ✅ | 10000 requests por **Day**
3. **Next → Add API Stage** → mesma API → Stage: `dev` → **Next**

---
## Parte 3 – Criar API Keys

### API Key para free-tier

1. **API Keys → Create API key** ("Criar chave de API")
   - **Name:** `cliente-free-tier`
   - **API Key:** Auto Generate
2. **Save** → **anote o valor da chave** (visível após criação em "Show")
3. Clique na API Key criada → **Usage Plans → Add to Usage Plan → free-tier**

### API Key para premium

1. **API Keys → Create API key** ("Criar chave de API")
   - **Name:** `cliente-premium`
   - **API Key:** Auto Generate
2. **Save** → anote a chave
3. Clique na API Key → **Usage Plans → Add to Usage Plan → premium**

---
## Parte 4 – Deploy e Testar

**Bash (Linux/macOS/Git Bash/WSL):**
```bash
# Deploy para aplicar API Key Required
# Actions → Deploy API → dev → Deploy

API_URL="https://<API_ID>.execute-api.<REGION>.amazonaws.com/dev"
FREE_KEY="<SUA_API_KEY_FREE>"
PREMIUM_KEY="<SUA_API_KEY_PREMIUM>"

# Sem API Key — deve retornar 403 Forbidden
curl "$API_URL/hello"

# Com API Key free-tier — deve retornar 200
curl -H "x-api-key: $FREE_KEY" "$API_URL/hello?name=Estudante"

# Com API Key premium — deve retornar 200
curl -H "x-api-key: $PREMIUM_KEY" "$API_URL/hello?name=Estudante"
```

**PowerShell (Windows):**
```powershell
# Deploy para aplicar API Key Required
# Actions → Deploy API → dev → Deploy

$API_URL = "https://<API_ID>.execute-api.<REGION>.amazonaws.com/dev"
$FREE_KEY = "<SUA_API_KEY_FREE>"
$PREMIUM_KEY = "<SUA_API_KEY_PREMIUM>"

# Sem API Key — deve retornar 403 Forbidden
curl.exe "$API_URL/hello"

# Com API Key free-tier — deve retornar 200
curl.exe -H "x-api-key: $FREE_KEY" "$API_URL/hello?name=Estudante"

# Com API Key premium — deve retornar 200
curl.exe -H "x-api-key: $PREMIUM_KEY" "$API_URL/hello?name=Estudante"
```

---
## Parte 5 – Demonstrar Throttling do Free Tier

O plano free-tier tem rate de 1 req/s. Enviar várias requisições em sequência rápida deve acionar o throttling:

**Bash:**
```bash
for i in $(seq 1 10); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "x-api-key: $FREE_KEY" "$API_URL/hello")
  echo "Requisicao $i: HTTP $STATUS"
done
```

**PowerShell:**
```powershell
1..10 | ForEach-Object {
  $STATUS = (curl.exe -s -o NUL -w "%{http_code}" `
    -H "x-api-key: $FREE_KEY" "$API_URL/hello")
  Write-Host "Requisicao $($_): HTTP $STATUS"
}
```

**Resultado esperado:** as primeiras retornam 200, depois começa a receber **429 Too Many Requests**.

### Comparar com Premium

**Bash:**
```bash
for i in $(seq 1 10); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "x-api-key: $PREMIUM_KEY" "$API_URL/hello")
  echo "Requisicao $i: HTTP $STATUS"
done
```

**PowerShell:**
```powershell
1..10 | ForEach-Object {
  $STATUS = (curl.exe -s -o NUL -w "%{http_code}" `
    -H "x-api-key: $PREMIUM_KEY" "$API_URL/hello")
  Write-Host "Requisicao $($_): HTTP $STATUS"
}
```

Com 100 req/s de rate, todas devem retornar 200.

---
## Parte 6 – Visualizar Uso e Métricas

1. **Usage Plans → free-tier → API Keys** → clique na chave → aba **Usage**
2. **CloudWatch → Metrics → API Gateway → By API** → métricas: `Count`, `4XXError`, `5XXError`, `Latency`

---
## Parte 7 – Hierarquia de Throttling

O limite mais restritivo sempre prevalece:

```
Conta AWS (10.000 req/s — limite global)
    └── API/Stage (configurável por stage)
        └── Usage Plan (por plano de cliente)
            └── Método específico (opcional, por recurso+método)
```

Para demonstrar: configure o stage com Rate 50 req/s. O plano premium (100 req/s) fica limitado a 50 — o stage é o gargalo.

**Stages → dev → Stage Settings → Edit → Rate: 50 → Save**

---
## Pontos de Verificação

- Sem API Key → **403 Forbidden**
- Rate excedida → **429 Too Many Requests**
- Quota diária excedida → **429 Too Many Requests** (com mensagem diferente)
- O header correto é `x-api-key` (minúsculo)
- API Keys **identificam** clientes — não substituem autenticação (Cognito, IAM). Use ambos em produção
- Usage Plans são exclusivos de **REST APIs** — HTTP APIs não suportam esse recurso

---
## Limpeza

```
# Pelo console:
# API Keys → deletar cliente-free-tier e cliente-premium
# Usage Plans → deletar free-tier e premium

# Remover API Key Required do método (para não afetar outros labs)
# Method Request → API Key Required → false → Deploy API
```

> O console é a forma mais prática para limpeza neste lab. Os comandos AWS CLI acima funcionam em Bash e PowerShell.
