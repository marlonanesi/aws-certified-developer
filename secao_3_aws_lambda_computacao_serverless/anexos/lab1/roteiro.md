# Lab 1 – Criando a Primeira Função Lambda

> **Compatibilidade de comandos CLI**
> Os comandos avulsos deste roteiro funcionam diretamente em **PowerShell** (Windows) e **Bash** (Linux/macOS/Git Bash) — basta colar e executar.
> Onde há diferença de sintaxe entre os dois shells, o roteiro apresenta as duas versões lado a lado.
> Para CMD ou outros terminais, converta a sintaxe com ajuda de IA generativa.

---
> **Custos e Free Tier**
> O AWS Lambda oferece **1 milhão de invocações gratuitas por mês** e **400.000 GB-segundos de computação** (nível permanente, não limitado a 12 meses). Para os testes deste lab, o custo é zero.
> O Amazon CloudWatch Logs inclui **5 GB de ingestão gratuita por mês** (primeiros 12 meses).
>
> ⚠️ **Aviso importante:** qualquer recurso provisionado na AWS pode gerar custos mesmo dentro do free tier, que possui limites mensais. Ao concluir o lab, execute a etapa de limpeza para evitar cobranças inesperadas.

---
## Objetivo

Criar e testar uma função Lambda em Python pelo console AWS, compreendendo o handler, o objeto `event`, o objeto `context`, variáveis de ambiente e logs no CloudWatch.

---
## Pré-requisitos

- Conta AWS com usuário IAM e permissões em Lambda e CloudWatch
- AWS CLI configurada (opcional, para a Parte 6)
- Conhecimento básico de Python

---
## Parte 1 – Criar a Função pelo Console

1. Console AWS → **Lambda → Create function** ("Criar função")
2. Selecione **Author from scratch** ("Criar do zero")
3. Preencha:
   - **Function name:** `minha-primeira-lambda`
   - **Runtime:** Python 3.12
   - **Architecture:** x86_64
4. Em **Permissions:** deixe **Create a new role with basic Lambda permissions** ("Criar uma nova função com permissões básicas de Lambda") (padrão)
5. Clique em **Create function** ("Criar função")

---
## Parte 2 – Escrever o Código

No editor do console, substitua o código padrão pelo conteúdo do arquivo `lambda_handler.py` incluído nesta pasta.

Após colar o código, clique em **Deploy** ("Implantar").

---
## Parte 3 – Configurar Variável de Ambiente

1. **Configuration** ("Configuração") **→ Environment variables** ("Variáveis de ambiente") **→ Edit** ("Editar")
2. **Add environment variable** ("Adicionar variável de ambiente"):
   - Key: `APP_ENV`
   - Value: `desenvolvimento`
3. **Save**

---
## Parte 4 – Criar e Executar Testes

### Teste 1 – Saudação básica

1. Aba **Test** ("Testar") **→ Create new test event** ("Criar novo evento de teste")
2. **Event name:** `teste-saudacao`
3. **Event JSON:**
```json
{
  "name": "Estudante",
  "action": "greet"
}
```
4. Clique em **Test**

**Resultado esperado:**
```json
{
  "statusCode": 200,
  "body": "{\"message\": \"Olá, Estudante! Ambiente: desenvolvimento\", ...}"
}
```

### Teste 2 – Echo do evento

```json
{
  "name": "Lambda",
  "action": "echo",
  "dados": [1, 2, 3]
}
```

### Teste 3 – Evento vazio (valores padrão)

```json
{}
```

Observe que os valores padrão entram em ação: `name = 'Mundo'`, `action = 'greet'`, `APP_ENV = 'dev'`.

---
## Parte 5 – Analisar os Logs no CloudWatch

1. Após cada teste: **Monitor → View CloudWatch logs**
2. Abra o **Log Group** da função e clique no **Log Stream** mais recente
3. Observe:
   - `START RequestId:` — início da invocação
   - Saídas dos `print()` do código
   - `END RequestId:`
   - `REPORT` — duração, memória usada e billed duration

**Cold Start vs Warm Start:** na primeira execução, `Init Duration` aparece no `REPORT`. Nas invocações subsequentes, essa linha não aparece — o container já está aquecido.

---
## Parte 6 – Invocar via AWS CLI (opcional)

**Bash (Linux/macOS/Git Bash/WSL):**
```bash
aws lambda invoke \
  --function-name minha-primeira-lambda \
  --payload '{"name": "CLI", "action": "greet"}' \
  --cli-binary-format raw-in-base64-out \
  response.json

cat response.json
```

**PowerShell (Windows):**
```powershell
aws lambda invoke `
  --function-name minha-primeira-lambda `
  --payload '{"name": "CLI", "action": "greet"}' `
  --cli-binary-format raw-in-base64-out `
  response.json

Get-Content response.json
```

---
## Parte 7 – Ajustar Timeout e Memória

1. **Configuration → General configuration → Edit**
2. Altere:
   - **Memory:** 256 MB
   - **Timeout:** 10 segundos
3. Salve e re-execute os testes
4. Compare o `REPORT` no CloudWatch — observe `Duration` e `Max Memory Used`

---
## Pontos de Verificação

- `context.function_name` retorna o nome exato da função
- `context.aws_request_id` é único por invocação — útil para rastreamento
- `context.get_remaining_time_in_millis()` diminui a cada chamada durante a execução
- A variável `APP_ENV` configurada aparece no log, mas `AWS_REGION` e outras variáveis reservadas já existem sem configuração manual

---
## Limpeza

```
aws lambda delete-function --function-name minha-primeira-lambda
```

> Funciona em Bash e PowerShell sem adaptação.

Ou pelo console: selecione a função → **Actions → Delete function**.
