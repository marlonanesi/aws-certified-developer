# Lab 3 – Mapping Templates e Transformações com VTL

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
> - **AWS Lambda:** 1 milhão de invocações gratuitas/mês (nível permanente)
>
> ⚠️ **Aviso importante:** qualquer recurso provisionado na AWS pode gerar custos mesmo dentro do free tier, que possui limites mensais. Ao concluir o lab, execute a etapa de limpeza para evitar cobranças inesperadas.

---
## Objetivo

Usar **Mapping Templates em VTL (Velocity Template Language)** para:
1. Transformar query strings em JSON estruturado antes de enviar à Lambda (**Integration Request**)
2. Transformar a resposta da Lambda em um envelope padronizado antes de retornar ao cliente (**Integration Response**)
3. Entender o **Passthrough Behavior** (`WHEN_NO_MATCH` vs `NEVER`)

> **Importante:** Mapping Templates requerem **Lambda Custom Integration** — não Proxy Integration. Este lab cria um novo recurso `/transform` com Custom Integration.

---
## Arquitetura

```
Cliente → GET /transform?firstName=Ana&lastName=Silva
    ↓  Integration Request (VTL)
    ↓  Transforma query params → JSON body
Lambda recebe: { "fullName": "Ana Silva", "nameLength": 9 }
    ↓  Processa e retorna
Lambda retorna: { "greeting": "Olá, Ana Silva!", "chars": 9 }
    ↓  Integration Response (VTL)
    ↓  Envolve em envelope padronizado
Cliente recebe: { "status": "success", "data": { ... }, "meta": { ... } }
```

---
## Pré-requisitos

- Lab 1 concluído (API existente)
- AWS CLI configurada com permissões em Lambda e API Gateway

---
## Parte 1 – Criar a Lambda para o Lab (sem Proxy)

1. **Lambda → Create function** ("Criar função") **→ Author from scratch** ("Criar do zero")
   - **Function name:** `api-lab3-transform`
   - **Runtime:** Python 3.12
2. Cole o código do arquivo `lambda_transform.py` incluído nesta pasta
3. **Deploy**

Esta Lambda espera receber **apenas os campos que o VTL definir** — ela não precisa conhecer o formato de evento do API Gateway.

---
## Parte 2 – Adicionar o Recurso `/transform` na API

1. No API Gateway → **Actions → Create Resource** ("Criar recurso")
   - **Resource Name:** `transform`
   - **Resource Path:** `/transform`
   - ✅ Enable CORS
2. **Create Resource** ("Criar recurso")

### Criar método GET com Custom Integration

1. `/transform` → **Actions → Create Method** ("Criar método") **→ GET**
2. Configurações:
   - **Integration type:** Lambda Function
   - ❌ **NÃO marque** Use Lambda Proxy integration (diferença-chave deste lab)
   - **Lambda Function:** `api-lab3-transform`
3. **Save**

---
## Parte 3 – Configurar Integration Request (VTL)

1. Clique no método **GET** em `/transform` → **Integration Request**
2. Expanda **Mapping Templates**
3. **Request body passthrough:** `When there are no templates defined (recommended)`
4. **Add mapping template** → Content-Type: `application/json` → confirmar
5. Cole o template VTL do arquivo `vtl_request.vm` incluído nesta pasta
6. **Save**

---
## Parte 4 – Configurar Integration Response (VTL)

1. Volte ao método **GET** → **Integration Response**
2. Expanda a linha **200** → expanda **Mapping Templates**
3. **Add mapping template** → Content-Type: `application/json` → confirmar
4. Cole o template VTL do arquivo `vtl_response.vm` incluído nesta pasta
5. **Save**

---
## Parte 5 – Deploy e Testar

**Bash (Linux/macOS/Git Bash/WSL):**
```bash
# Deploy para o stage dev
# Actions → Deploy API → dev → Deploy

API_URL="https://<API_ID>.execute-api.<REGION>.amazonaws.com/dev"

# Teste via console: GET em /transform → TEST
# Query Strings: firstName=Ana&lastName=Silva

# Teste via terminal
curl "$API_URL/transform?firstName=Ana&lastName=Silva"
```

**PowerShell (Windows):**
```powershell
# Deploy para o stage dev
# Actions → Deploy API → dev → Deploy

$API_URL = "https://<API_ID>.execute-api.<REGION>.amazonaws.com/dev"

# Teste via terminal
curl.exe "$API_URL/transform?firstName=Ana&lastName=Silva"
```

**Resposta esperada:**
```json
{
  "status": "success",
  "data": {
    "greeting": "Olá, Ana Silva!",
    "characterCount": 9,
    "processed": true
  },
  "meta": {
    "requestId": "...",
    "stage": "dev"
  }
}
```

---
## Parte 6 – Testar Passthrough Behavior com NEVER

1. **Integration Request → Request body passthrough → Never** → Save → Redeploy

**Bash:**
```bash
# Content-Type mapeado (application/json) — deve funcionar
curl "$API_URL/transform?firstName=Ana&lastName=Silva"

# Content-Type sem template mapeado — deve retornar 415
curl -H "Content-Type: text/plain" "$API_URL/transform?firstName=Ana&lastName=Silva"
```

**PowerShell:**
```powershell
# Content-Type mapeado — deve funcionar
curl.exe "$API_URL/transform?firstName=Ana&lastName=Silva"

# Content-Type sem template mapeado — deve retornar 415
curl.exe -H "Content-Type: text/plain" "$API_URL/transform?firstName=Ana&lastName=Silva"
```

Com `NEVER`, o API Gateway rejeita qualquer Content-Type sem template correspondente. Garante validação estrita.

2. Retorne para `When there are no templates defined` → Redeploy.

---
## Parte 7 – Comparar Proxy vs Custom Integration

**Bash:**
```bash
# Lambda Proxy (Lab 1) — Lambda recebe o evento completo do API Gateway
curl "$API_URL/hello?name=Estudante"

# Lambda Custom Integration (Lab 3) — Lambda recebe apenas o que o VTL produziu
curl "$API_URL/transform?firstName=Ana&lastName=Silva"
```

**PowerShell:**
```powershell
# Lambda Proxy (Lab 1)
curl.exe "$API_URL/hello?name=Estudante"

# Lambda Custom Integration (Lab 3)
curl.exe "$API_URL/transform?firstName=Ana&lastName=Silva"
```

Inspecione os logs do CloudWatch de cada função para ver a diferença no evento recebido:
- **Proxy:** objeto completo com `httpMethod`, `headers`, `requestContext`, `stageVariables`, etc.
- **Custom:** apenas os campos definidos no template VTL

---
## Pontos de Verificação

- A Lambda `api-lab3-transform` **não conhece** o formato de evento do API Gateway — só recebe o JSON que o VTL construiu
- O template de **Integration Request** roda **antes** de chamar a Lambda; o de **Integration Response** roda **depois** do retorno
- `$input.params('nome')` lê query string ou path parameter
- `$input.path('$')` na resposta lê o corpo retornado pela Lambda
- `$context.requestId` e `$context.stage` são variáveis de contexto injetadas pelo API Gateway

---
## Limpeza

## Limpeza

```
aws lambda delete-function --function-name api-lab3-transform
# O recurso /transform pode ser deletado via console: Actions → Delete Resource
```

> Funciona em Bash e PowerShell sem adaptação.
