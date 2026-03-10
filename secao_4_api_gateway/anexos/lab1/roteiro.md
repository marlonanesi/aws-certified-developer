# Lab 1 – REST API integrada com Lambda (Lambda Proxy Integration)

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
> - **Amazon CloudWatch Logs:** 5 GB de ingestão gratuita/mês (primeiros 12 meses)
>
> Para volumes de teste deste lab, o custo tende a ser zero dentro do free tier.
>
> ⚠️ **Aviso importante:** qualquer recurso provisionado na AWS pode gerar custos mesmo dentro do free tier, que possui limites mensais. Ao concluir o lab, execute a etapa de limpeza para evitar cobranças inesperadas.

---
## Objetivo

Criar uma REST API no API Gateway integrada com uma função Lambda usando **Lambda Proxy Integration**, expor um endpoint `GET /hello` e testá-lo via `curl` ou ferramenta similar.

---
## Arquitetura

```
Cliente (curl / Postman)
    ↓  HTTP GET /hello
Amazon API Gateway (REST API)
    ↓  Lambda Proxy Integration
AWS Lambda (Python 3.12)
    ↓  Retorna JSON
API Gateway → Cliente
```

---
## Pré-requisitos

- Conta AWS com permissões em Lambda, API Gateway e CloudWatch
- AWS CLI configurada (para os testes via terminal)

---
## Parte 1 – Criar a Função Lambda

1. Console AWS → **Lambda → Create function** ("Criar função") **→ Author from scratch** ("Criar do zero")
2. Configurações:
   - **Function name:** `api-lab1-hello`
   - **Runtime:** Python 3.12
   - **Architecture:** x86_64
   - **Execution role:** Create a new role with basic Lambda permissions ("Criar uma nova função com permissões básicas de Lambda")
3. Cole o código do arquivo `lambda_hello.py` incluído nesta pasta
4. Clique em **Deploy** ("Implantar")

### Testar a Lambda diretamente

1. **Test** ("Testar") **→ Create new test event** ("Criar novo evento de teste"), nome `TestProxy`
2. Payload:
```json
{
  "httpMethod": "GET",
  "path": "/hello",
  "queryStringParameters": { "name": "Estudante" },
  "headers": { "Accept": "application/json" },
  "body": null
}
```
3. Execute e confirme que retorna `statusCode: 200`.

---
## Parte 2 – Criar a REST API

1. **Amazon API Gateway → Create API** ("Criar API") **→ REST API → Build** ("Compilar")
2. Configurações:
   - **API name:** `lab1-hello-api`
   - **Endpoint Type:** Regional
3. **Create API** ("Criar API")

### Criar o recurso `/hello`

1. **Actions → Create Resource** ("Criar recurso")
   - **Resource Name:** `hello`
   - **Resource Path:** `/hello`
   - ✅ Enable API Gateway CORS
2. **Create Resource** ("Criar recurso")

### Criar o método GET

1. Com `/hello` selecionado → **Actions → Create Method** ("Criar método") **→ GET** → confirmar
2. Configurações de integração:
   - **Integration type:** Lambda Function
   - ✅ **Use Lambda Proxy integration** (essencial para este lab)
   - **Lambda Region:** sua região
   - **Lambda Function:** `api-lab1-hello`
3. **Save** → no popup de permissões, clique **OK**

---
## Parte 3 – Deploy da API

1. **Actions → Deploy API**
2. **Deployment stage:** `[New Stage]`
3. **Stage name:** `dev`
4. **Deploy**

Anote a URL gerada:
```
https://<API_ID>.execute-api.<REGION>.amazonaws.com/dev
```

---
## Parte 4 – Testar a API

### Via console

1. Clique no método **GET** em `/hello` → **TEST**
2. Deixe os campos em branco → **Test**
3. Confirme resposta com `statusCode 200`

### Via terminal

**Bash (Linux/macOS/Git Bash/WSL):**
```bash
API_URL="https://<API_ID>.execute-api.<REGION>.amazonaws.com/dev"

# GET básico (usa nome padrão "Mundo")
curl "$API_URL/hello"

# GET com parâmetro de query
curl "$API_URL/hello?name=Estudante"

# Verbose — para ver os headers de resposta
curl -v "$API_URL/hello?name=Estudante"
```

**PowerShell (Windows):**
```powershell
$API_URL = "https://<API_ID>.execute-api.<REGION>.amazonaws.com/dev"

# GET básico
curl.exe "$API_URL/hello"

# GET com parâmetro de query
curl.exe "$API_URL/hello?name=Estudante"

# Verbose
curl.exe -v "$API_URL/hello?name=Estudante"
```

> `curl.exe` usa o binário real do Windows 10+, evitando o alias `Invoke-WebRequest` do PowerShell 5.1.

**Resposta esperada:**
```json
{
  "message": "Olá, Estudante! Bem-vindo ao API Gateway.",
  "method": "GET",
  "path": "/hello"
}
```

---
## Parte 5 – Explorar o Evento da Proxy Integration

Na Lambda, o print do evento completo aparece nos logs do CloudWatch:

1. **CloudWatch → Log Groups → /aws/lambda/api-lab1-hello**
2. Abra o log stream mais recente e observe todos os campos enviados pelo API Gateway: `httpMethod`, `path`, `headers`, `queryStringParameters`, `requestContext`, `stageVariables`, etc.

### Simular resposta de erro 400

Adicione temporariamente ao código a seguinte validação:

```python
if name and len(name) < 2:
    return {
        'statusCode': 400,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'error': 'name deve ter ao menos 2 caracteres'})
    }
```

Teste com `?name=A` e confirme que recebe HTTP 400.

---
## Parte 6 – Adicionar Método POST (opcional)

1. Em `/hello` → **Actions → Create Method** ("Criar método") **→ POST**
2. Configure com Lambda Proxy Integration para a mesma função
3. Atualize o código conforme o arquivo `lambda_hello.py` (seção POST)
4. **Deploy** ("Implantar") novamente

**Bash:**
```bash
curl -X POST "$API_URL/hello" \
  -H "Content-Type: application/json" \
  -d '{"name": "Estudante"}'
```

**PowerShell:**
```powershell
curl.exe -X POST "$API_URL/hello" `
  -H "Content-Type: application/json" `
  -d '{"name": "Estudante"}'
```

---
## Pontos de Verificação

- Com Lambda Proxy Integration, a Lambda recebe **todo o contexto** da requisição HTTP
- A Lambda **deve** retornar um objeto com `statusCode`, `headers` e `body` — caso contrário o API Gateway retorna erro
- O `body` deve ser uma **string** (usar `json.dumps()`), não um dict Python
- Logs no CloudWatch aparecem imediatamente após invocação — útil para debug

---
## Limpeza

```
aws lambda delete-function --function-name api-lab1-hello
aws apigateway delete-rest-api --rest-api-id <API_ID>
```

> Ambos os comandos funcionam em Bash e PowerShell sem alteração.

Ou pelo console: Lambda → **Delete function** | API Gateway → **Delete API**.

Se for seguir os labs seguintes em sequência, pode manter pois reaproveitaremos alguns recursos! Ou delete e aproveite para exercitar os conceitos, ficamos bom em algo pela repetição!
