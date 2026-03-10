# Roteiro — Lab 2: Deploy de API Serverless com AWS SAM

> **Compatibilidade de comandos CLI**
> Os comandos avulsos deste roteiro funcionam diretamente em **PowerShell** (Windows) e **Bash** (Linux/macOS/Git Bash) — basta colar e executar.
> Onde há diferença de sintaxe entre os dois shells (variáveis, continuação de linha, curl), o roteiro apresenta as duas versões lado a lado.
> Para CMD ou outros terminais, converta a sintaxe com ajuda de IA generativa.

## Custos e Free Tier

| Serviço | Free Tier |
|---------|-----------|
| SAM / CloudFormation | Gratuito (cobranças são dos recursos provisionados) | 
| Lambda | 1 milhão de invocações/mês + 400k GB-s (permanente) |
| API Gateway HTTP API | 1 milhão de chamadas/mês (primeiros 12 meses) |
| DynamoDB | 25 GB + 25 WCU + 25 RCU (permanente) |
| S3 (bucket de artefatos SAM) | 5 GB storage (primeiros 12 meses) |

> **Aviso:** Recursos na nuvem podem gerar custos mesmo dentro do Free Tier. Ao finalizar a prática, **execute a limpeza** — o CloudFormation removerá todos os recursos criados pelo SAM automaticamente.

---
## Objetivo

Criar e deployar uma API serverless completa usando AWS SAM com:
- Duas funções Lambda em Python (listar e criar tarefas)
- API Gateway HTTP API
- Tabela DynamoDB simples
- Teste local com SAM CLI
- Deploy na AWS via `sam deploy --guided`

---
## Arquitetura

```
                          SAM / CloudFormation
                   (provisiona e conecta tudo)

  Cliente HTTP
      │
      ▼
  API Gateway HTTP API
      │
      ├── GET  /todos ──▶ Lambda: ListTodosFunction
      │                        │
      └── POST /todos ──▶ Lambda: CreateTodoFunction
                               │
                               ▼
                        DynamoDB Table (TodoTable)
```

> O SAM gera automaticamente as IAM Roles, permissões de invocação e injeta `TABLE_NAME` como variável de ambiente em cada Lambda.

---
## Pré-requisitos

- **SAM CLI** instalada (`sam --version`)
- **Docker Desktop** rodando (necessário para testes locais)
- **AWS CLI** configurada com credenciais válidas

---
## Estrutura desta pasta

```
lab2/
├── template.yaml          # Template SAM da aplicação
├── src/
│   └── app.py             # Código das funções Lambda
└── events/
    ├── list_todos.json    # Evento de teste para ListTodosFunction
    └── create_todo.json   # Evento de teste para CreateTodoFunction
```

---
## Parte 1 — Revisar o Template SAM

Abra `template.yaml` e observe:

- **`Transform: AWS::Serverless-2016-10-31`**: declara que é um template SAM — transforma em CloudFormation durante o deploy
- **`Globals`**: define `Runtime`, `Timeout` e `Policies` uma vez — todas as funções herdam automaticamente
- **`DynamoDBCrudPolicy`**: política SAM pré-definida — muito mais concisa do que escrever IAM manualmente
- **`AWS::Serverless::SimpleTable`**: cria uma tabela DynamoDB com chave primária `id` sem precisar definir billing mode, capacidade, etc.
- **`Type: HttpApi`**: cria um API Gateway HTTP API (mais barato e rápido que REST API)
- **`Outputs`**: exporta a URL da API e o nome da tabela após o deploy

---
## Parte 2 — Revisar o Código da Aplicação

Abra `src/app.py` e observe:

- `list_todos`: lê a variável de ambiente `TABLE_NAME` (injetada pelo SAM), faz `table.scan()` e retorna os itens
- `create_todo`: gera um `uuid`, monta o item com título, status e timestamp, e faz `table.put_item()`
- Ambas as funções retornam o formato esperado pelo API Gateway: `statusCode`, `headers` e `body`

---
## Parte 3 — Build

```
sam build
```

O SAM empacota o código e dependências na pasta `.aws-sam/build/`. Sempre execute `sam build` antes de testes locais ou deploy.

---
## Parte 4 — Teste Local com Eventos

> **Nota:** O teste local usa Lambda runtime emulado via Docker. Chamadas ao DynamoDB falharão por não haver tabela real — isso é esperado. O objetivo é verificar que a função inicializa e que o código não tem erros de importação.

```
# Testar função de listagem
sam local invoke ListTodosFunction -e events/list_todos.json

# Testar função de criação
sam local invoke CreateTodoFunction -e events/create_todo.json
```

---
## Parte 5 — API Local (opcional)

Inicie a API localmente em um terminal separado:

```
sam local start-api
```

Em outro terminal, teste os endpoints:

**PowerShell:**
```powershell
# Listar (espera erro de DynamoDB — comportamento esperado)
Invoke-RestMethod -Uri http://localhost:3000/todos -Method GET

# Criar
Invoke-RestMethod -Uri http://localhost:3000/todos -Method POST `
  -ContentType "application/json" `
  -Body '{"title": "Aprender SAM CLI"}'
```

**Bash:**
```bash
# Listar (espera erro de DynamoDB — comportamento esperado)
curl http://localhost:3000/todos

# Criar
curl -X POST http://localhost:3000/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "Aprender SAM CLI"}'
```

Encerre a API local com `Ctrl+C` antes de prosseguir.

---
## Parte 6 — Validar Template

```
sam validate
```

Deve retornar sem erros. Se houver erros de YAML ou referências inválidas, corrija antes de fazer deploy.

---
## Parte 7 — Deploy na AWS

```
sam deploy --guided
```

Preencha as opções interativas:

| Pergunta | Valor |
|----------|-------|
| Stack Name | `lab2-todo-api` |
| AWS Region | `us-east-1` (ou sua região) |
| Confirm changes before deploy | `y` |
| Allow SAM CLI IAM role creation | `y` |
| Disable rollback | `n` |
| Save arguments to configuration file | `y` |

Aguarde a conclusão. Ao final, anote a `ApiUrl` exibida nos Outputs.

> Em deploys futuros, basta executar `sam deploy` (sem `--guided`) — as configurações ficam salvas em `samconfig.toml`.

---
## Parte 8 — Testar a API Real

Substitua a URL abaixo pela `ApiUrl` dos Outputs do deploy.

**PowerShell:**
```powershell
$API_URL = "https://XXXXXXXXXX.execute-api.us-east-1.amazonaws.com"

# Criar uma tarefa
Invoke-RestMethod -Uri "$API_URL/todos" -Method POST `
  -ContentType "application/json" `
  -Body '{"title": "Completar certificacao DVA-C02"}'

# Listar todas as tarefas
Invoke-RestMethod -Uri "$API_URL/todos" -Method GET
```

**Bash:**
```bash
API_URL="https://XXXXXXXXXX.execute-api.us-east-1.amazonaws.com"

# Criar uma tarefa
curl -X POST "${API_URL}/todos" \
  -H "Content-Type: application/json" \
  -d '{"title": "Completar certificacao DVA-C02"}'

# Listar todas as tarefas
curl "${API_URL}/todos"
```

---
## Parte 9 — Explorar os Recursos Criados

```
# Ver a stack CloudFormation gerada pelo SAM
aws cloudformation describe-stacks --stack-name lab2-todo-api --query "Stacks[0].Outputs"

# Ver todos os recursos criados na stack
aws cloudformation list-stack-resources --stack-name lab2-todo-api
```

Veja também o template CloudFormation expandido que o SAM gerou:

**PowerShell:**
```powershell
Get-Content .aws-sam\build\template.yaml
```

**Bash:**
```bash
cat .aws-sam/build/template.yaml
```

Compare com o `template.yaml` original — note como o SAM expandiu `AWS::Serverless::Function` em `AWS::Lambda::Function` + `AWS::Lambda::Permission` + policies IAM completas.

---
## Parte 10 — Validar na Console AWS

### Pegar a URL e testar via terminal

```powershell
# Obter a ApiUrl dos Outputs da stack
aws cloudformation describe-stacks --stack-name lab2-todo-api --query "Stacks[0].Outputs"

$API_URL = "https://COLOQUE_SUA_URL_AQUI.execute-api.sa-east-1.amazonaws.com"

# Criar tarefas
Invoke-RestMethod -Uri "$API_URL/todos" -Method POST `
  -ContentType "application/json" `
  -Body '{"title": "Validar deploy SAM"}'

Invoke-RestMethod -Uri "$API_URL/todos" -Method POST `
  -ContentType "application/json" `
  -Body '{"title": "Verificar DynamoDB no console"}'

# Listar todas
Invoke-RestMethod -Uri "$API_URL/todos" -Method GET
```

### O que conferir no Console AWS

**Lambda** → Functions:
- Confirmar que `ListTodosFunction` e `CreateTodoFunction` existem
- Em cada função: aba **Configuration → Environment variables** — deve exibir `TABLE_NAME` com o nome físico da tabela
- Aba **Configuration → Permissions** — verificar a Role criada e a política `DynamoDBCrudPolicy` anexada

**API Gateway** → APIs:
- Localizar a API do tipo **HTTP API** criada pelo SAM
- Aba **Routes**: confirmar `GET /todos` e `POST /todos` com integrações Lambda

**DynamoDB** → Tables:
- Localizar a tabela `lab2-todo-api-TodoTable-*`
- Aba **Explore items**: verificar os itens criados via `POST`, com `id` (UUID), `title`, `done` e `createdAt`

**CloudFormation** → Stacks → `lab2-todo-api`:
- Aba **Resources**: listar os 9 recursos criados pelo SAM
- Aba **Outputs**: copiar a `ApiUrl` diretamente daqui
- Aba **Template**: ver o template CloudFormation expandido que o SAM gerou

---
## Pontos de Atenção

- **`Transform` obrigatório**: sem `Transform: AWS::Serverless-2016-10-31` o CloudFormation não reconhece os tipos SAM
- **`sam build` antes de tudo**: sem build o código não está empacotado — nem teste local nem deploy funcionam
- **`Globals`**: evita repetir `Runtime`, `Timeout` e `Policies` em cada função — alteração em um lugar propaga para todas
- **`samconfig.toml`**: salvo automaticamente após `--guided` — permite `sam deploy` sem parâmetros nos próximos deploys
- **Template expandido**: `.aws-sam/build/template.yaml` mostra que SAM é uma abstração sobre CloudFormation

---
## Erros Comuns

| Erro | Causa | Solução |
|------|-------|---------|
| Docker not running | Docker offline | Iniciar Docker Desktop antes do `sam local invoke` |
| No such handler `app.list_todos` | `CodeUri` errado ou arquivo ausente | Verificar que `src/app.py` existe e `CodeUri: src/` está no template |
| IAM error no deploy | `--guided` não marcou IAM capabilities | Responder `y` em "Allow SAM CLI IAM role creation" |
| Table not found (local) | DynamoDB local não configurado | Esperado — o deploy real na AWS funciona corretamente |
| `sam deploy` falha sem `--guided` | `samconfig.toml` não existe | Executar `sam deploy --guided` ao menos uma vez |

---
## Limpeza

```
aws cloudformation delete-stack --stack-name lab2-todo-api
```

> O bucket S3 criado automaticamente pelo SAM para armazenar os artefatos de build (nome começa com `aws-sam-cli-managed-default-`) **não é deletado** pela stack. Se quiser removê-lo manualmente: AWS Console → S3 → localize o bucket → Empty → Delete.
