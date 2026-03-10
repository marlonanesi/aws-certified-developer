# Lab 3 – Criando e Usando Lambda Layers

> **Compatibilidade de comandos CLI**
> Os comandos avulsos deste roteiro funcionam diretamente em **PowerShell** (Windows) e **Bash** (Linux/macOS/Git Bash) — basta colar e executar.
> Onde há diferença de sintaxe entre os dois shells, o roteiro apresenta as duas versões lado a lado.
> Para CMD ou outros terminais, converta a sintaxe com ajuda de IA generativa.

---
> **Custos e Free Tier**
> O AWS Lambda oferece **1 milhão de invocações gratuitas por mês** e **400.000 GB-segundos** (nível permanente). Layers não têm custo adicional de armazenamento relevante para tamanhos típicos de laboratório.
>
> ⚠️ **Aviso importante:** qualquer recurso provisionado na AWS pode gerar custos mesmo dentro do free tier, que possui limites mensais. Ao concluir o lab, execute a etapa de limpeza para evitar cobranças inesperadas.

---
## Objetivo

Criar uma Lambda Layer com uma biblioteca externa (`requests`) e um módulo utilitário compartilhado (`utils.py`), depois consumi-la em duas funções Lambda independentes, demonstrando reutilização de código e padronização de logs.

---
## Pré-requisitos

- AWS CLI configurada com permissões em Lambda e IAM
- Python 3.12 e pip instalados localmente
- Terminal PowerShell no Windows

---
## Parte 1 – Preparar e Publicar a Layer

### Passo 1 – Criar a estrutura do pacote

```
New-Item -ItemType Directory -Force -Path lambda-layer/python/lib/python3.12/site-packages

# Instalar requests no diretório correto
pip install requests -t lambda-layer/python/lib/python3.12/site-packages/
```

### Passo 2 – Adicionar o módulo utilitário

Copie o arquivo `utils.py` desta pasta para dentro do pacote:

```
Copy-Item utils.py lambda-layer/python/lib/python3.12/site-packages/
```

### Passo 3 – Empacotar e publicar

```
Compress-Archive -Path lambda-layer/python -DestinationPath minha-layer.zip -Force

# Publicar a layer
aws lambda publish-layer-version --layer-name "utils-e-requests" --region <REGION> --description "Utilitarios compartilhados + requests" --zip-file fileb://minha-layer.zip --compatible-runtimes python3.12 --compatible-architectures x86_64
```

**Anote o `LayerVersionArn` retornado**, no formato:
`arn:aws:lambda:<REGION>:<ACCOUNT_ID>:layer:utils-e-requests:1`

---
## Parte 2 – Criar as Funções Lambda

### Função A – Processador de Pedidos

```
# Empacotar (apenas o código da função — sem bibliotecas, pois estão na layer)
Compress-Archive -Path funcao_pedidos.py -DestinationPath funcao_pedidos.zip -Force

# Criar a role com trust policy para Lambda - parte 1
aws iam create-role --role-name lambda-exec-role --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

# Anexar a policy básica de execução - parte 2
aws iam attach-role-policy --role-name lambda-exec-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

$LAYER_ARN = "arn:aws:lambda:<REGION>:<ACCOUNT_ID>:layer:utils-e-requests:1"  # use o LayerVersionArn retornado acima
$ROLE_ARN = "arn:aws:iam::<ACCOUNT_ID>:role/lambda-exec-role"

aws lambda create-function --function-name processador-pedidos --runtime python3.12 --handler funcao_pedidos.lambda_handler --zip-file fileb://funcao_pedidos.zip --role $ROLE_ARN --layers $LAYER_ARN
```

### Função B – Validador de Clientes

```
Compress-Archive -Path funcao_clientes.py -DestinationPath funcao_clientes.zip

aws lambda create-function --function-name validador-clientes --runtime python3.12 --handler funcao_clientes.lambda_handler --zip-file fileb://funcao_clientes.zip --role $ROLE_ARN --layers $LAYER_ARN
```

> **Usando o console:** em cada função → **Layers** ("Camadas") **→ Add a layer** ("Adicionar uma camada") **→ Custom layers** ("Camadas personalizadas") **→ utils-e-requests → versão 1**.

---
## Parte 3 – Testar as Funções

### Teste na Função A – Pedido válido

```json
{
  "produto_id": "PROD-001",
  "quantidade": 5,
  "cliente_id": "CLI-123"
}
```

### Teste na Função A – Campo obrigatório faltando

```json
{
  "produto_id": "PROD-001"
}
```

Observe a mensagem de erro padronizada — gerada pelo `validar_campos_obrigatorios` do `utils.py`.

### Teste na Função B

```json
{
  "email": "usuario@exemplo.com",
  "nome": "Estudante"
}
```

---
## Parte 4 – CloudWatch Logs Insights

Abra os logs de ambas as funções. O formato JSON é **idêntico** nas duas — porque ambas usam `log_estruturado` da layer.

Query de exemplo no CloudWatch Logs Insights:

```
fields @timestamp, nivel, mensagem, status
| filter nivel = "erro"
| sort @timestamp desc
```

---
## Pontos de Verificação

- O pacote ZIP de cada função contém **apenas o código** — a layer provê as dependências
- Compare o tamanho: função com requests embutido (~2 MB) vs função com layer (~2 KB)
- Uma mesma layer pode ser usada por até **5 layers por função** (limite da AWS)
- Layers ficam em `/opt/python/` no container Lambda — o Python resolve os imports automaticamente
- A layer é **versionada e imutável** — publicar nova versão não quebra funções que usam versões anteriores

---
## Limpeza

```
aws lambda delete-function --function-name processador-pedidos
aws lambda delete-function --function-name validador-clientes
aws lambda delete-layer-version --layer-name utils-e-requests --version-number 1
Remove-Item -Recurse -Force lambda-layer, minha-layer.zip, funcao_pedidos.zip, funcao_clientes.zip -ErrorAction SilentlyContinue
```
