# Lab — S3 Events + Lambda: Processamento Orientado a Eventos

> **Aviso de compatibilidade de comandos**
> Os comandos deste roteiro sao referencias e podem precisar de adaptacao
> conforme o SO e terminal utilizados (PowerShell, Bash, Zsh, CMD, etc.).
> Converta a sintaxe antes de executar se necessario.
>
> Sugestao de prompt para IA generativa:
> "Converta o comando abaixo para meu SO [Windows/macOS/Linux] e terminal
> [PowerShell/Bash/Zsh/CMD]. Adapte variaveis, redirecionamentos e pipes
> para o equivalente nesse ambiente: <cole o comando aqui>"

> **Aviso de custos:** S3 oferece Free Tier de 5 GB / 20.000 GETs / 2.000 PUTs por mês (12 meses). Lambda oferece 1 milhão de invocações e 400.000 GB-s gratuitos por mês (permanente). Este lab gera poucas invocações e permanece dentro do Free Tier. Revise a aba **Billing** e **desprovisione todos os recursos ao finalizar.**

---
## Objetivo

Configurar S3 Event Notifications para invocar automaticamente uma função Lambda ao realizar uploads no bucket. Compreender resource-based policies, filtros de prefix e suffix, e o modelo de entrega at-least-once do S3.

---
## Pré-requisitos

- AWS CLI configurada com credenciais válidas
- Python 3.x instalado
- Permissões IAM para: S3, Lambda, IAM (criação de role/policy), CloudWatch Logs
- Arquivos do lab no diretório: `lambda_function.py`, `lambda-trust-policy.json`, `notification-config.json`, `notification-config-v2.json`, `setup.sh`, `cleanup.sh`

---
## Parte 1 — Setup da Infraestrutura

O script `setup.sh` automatiza a criação de toda a infraestrutura. Ele executa 6 passos em sequência:

1. Criação da IAM Role com trust policy para a Lambda
2. Attach das políticas `AWSLambdaBasicExecutionRole` + `AmazonS3ReadOnlyAccess`
3. Empacotamento e deploy da função Lambda
4. Criação do bucket S3
5. Adição da resource-based policy na Lambda (permite que o S3 a invoque)
6. Configuração da notificação de eventos no bucket com filtro de prefix `uploads/`

### Executar o setup (Bash / Git Bash / WSL)

```
bash setup.sh
```

### Executar o setup manualmente (passo a passo — qualquer terminal)

Caso não tenha ambiente Bash disponível, execute os comandos individualmente abaixo. Substitua `<ACCOUNT_ID>` e `<REGION>` pelos valores reais.

**Variáveis de referência:**

| Variável | Valor |
|---|---|
| BUCKET_NAME | `dva-lab2-eventos-<ACCOUNT_ID>` |
| FUNCTION_NAME | `dva-lab2-s3-processor` |
| ROLE_NAME | `dva-lab2-lambda-s3-role` |

**[1/6] Criar IAM Role:**

```
aws iam create-role --role-name dva-lab2-lambda-s3-role --assume-role-policy-document file://lambda-trust-policy.json
```

**[2/6] Anexar políticas à Role:**

```
aws iam attach-role-policy --role-name dva-lab2-lambda-s3-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy --role-name dva-lab2-lambda-s3-role --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
```

> Aguarde ~10 segundos para propagação da Role antes de criar a função Lambda.

**[3/6] Empacotar e criar a função Lambda:**

```
aws lambda create-function --function-name dva-lab2-s3-processor --runtime python3.12 --role arn:aws:iam::<ACCOUNT_ID>:role/dva-lab2-lambda-s3-role --handler lambda_function.lambda_handler --zip-file fileb://lambda_function.zip --timeout 30
```

> Compacte o arquivo antes: no PowerShell use `Compress-Archive -Path lambda_function.py -DestinationPath lambda_function.zip`; no Bash use `zip lambda_function.zip lambda_function.py`.

**[4/6] Criar o bucket S3 (us-east-1):**

```
aws s3api create-bucket --bucket dva-lab2-eventos-<ACCOUNT_ID>
```

Para outras regiões, adicione `--create-bucket-configuration LocationConstraint=<REGION>`.

**[5/6] Adicionar resource-based policy na Lambda:**

```
aws lambda add-permission --function-name dva-lab2-s3-processor --statement-id S3InvokePermission --action lambda:InvokeFunction --principal s3.amazonaws.com --source-arn arn:aws:s3:::dva-lab2-eventos-<ACCOUNT_ID> --source-account <ACCOUNT_ID>
```

**[6/6] Configurar notificação de eventos no bucket:**

Edite o `notification-config.json` substituindo `LAMBDA_ARN_PLACEHOLDER` pelo ARN real da Lambda e execute:

```
aws s3api put-bucket-notification-configuration --bucket dva-lab2-eventos-<ACCOUNT_ID> --notification-configuration file://notification-config.json
```

Obter o ARN da Lambda:

```
aws lambda get-function --function-name dva-lab2-s3-processor --query Configuration.FunctionArn --output text
```

---
## Parte 2 — Verificar o Setup

Confirme os recursos criados:

```
aws lambda get-function --function-name dva-lab2-s3-processor --query Configuration.{Estado:State,Runtime:Runtime,Timeout:Timeout}

aws s3api get-bucket-notification-configuration --bucket dva-lab2-eventos-<ACCOUNT_ID>
```

---
## Parte 3 — Testes de Upload

### Iniciar monitoramento de logs em tempo real (Bash / Git Bash / WSL)

```
aws logs tail /aws/lambda/dva-lab2-s3-processor --follow &
```

> No PowerShell, execute o monitoramento em um terminal separado sem o `&`:
> `aws logs tail /aws/lambda/dva-lab2-s3-processor --follow`

### Teste 1 — Upload dentro do prefixo (deve acionar a Lambda)

```
aws s3 cp teste.txt s3://dva-lab2-eventos-<ACCOUNT_ID>/uploads/teste.txt
```

> No PowerShell: `New-Item teste.txt; Set-Content teste.txt "dados de teste"` para criar o arquivo.

Aguarde ~5 segundos e observe os logs — o evento deve aparecer com o caminho `uploads/teste.txt`.

### Teste 2 — Upload fora do prefixo (NÃO deve acionar a Lambda)

```
aws s3 cp teste.txt s3://dva-lab2-eventos-<ACCOUNT_ID>/outros/teste.txt
```

Nenhum log deve aparecer — o filtro de prefix `uploads/` bloqueia a notificação.

### Teste 3 — Diferentes tipos de arquivo (dentro do prefixo)

```
aws s3 cp foto.jpg s3://dva-lab2-eventos-<ACCOUNT_ID>/uploads/foto.jpg
aws s3 cp dados.csv s3://dva-lab2-eventos-<ACCOUNT_ID>/uploads/dados.csv
aws s3 cp relatorio.pdf s3://dva-lab2-eventos-<ACCOUNT_ID>/uploads/relatorio.pdf
```

> Nos testes acima, você pode usar qualquer arquivo disponível localmente ou criar arquivos de texto simples com extensões `.jpg`, `.csv` e `.pdf`. O conteúdo não importa — a Lambda roteia pelo nome da extensão.

Nos logs, observe que cada tipo dispara uma branch diferente na função:
- `.jpg` → mensagem `[IMAGEM]`
- `.csv` → mensagem `[ETL]`
- `.pdf` → mensagem `[PDF]`

---
## Parte 4 — Filtros Múltiplos (Bônus)

Para aplicar prefix **e** suffix simultaneamente, use o `notification-config-v2.json`.

Edite o arquivo substituindo `LAMBDA_ARN_PLACEHOLDER` pelo ARN real da Lambda e aplique:

```
aws s3api put-bucket-notification-configuration --bucket dva-lab2-eventos-<ACCOUNT_ID> --notification-configuration file://notification-config-v2.json
```

**Validação dos filtros combinados:**

```
# Deve acionar — prefix: uploads/  suffix: .jpg
aws s3 cp foto.jpg s3://dva-lab2-eventos-<ACCOUNT_ID>/uploads/nova-foto.jpg

# NÃO deve acionar — prefix: uploads/  suffix: .csv (sem regra para esta combinação)
aws s3 cp dados.csv s3://dva-lab2-eventos-<ACCOUNT_ID>/uploads/dados.csv

# Deve acionar — prefix: data/  suffix: .csv
aws s3 cp dados.csv s3://dva-lab2-eventos-<ACCOUNT_ID>/data/novos-dados.csv
```

---
## Pontos de Verificação

- [ ] Setup concluído sem erros — IAM Role, Lambda, Bucket e notificação criados
- [ ] Upload em `uploads/` gera log na Lambda com detalhes do evento (bucket, objeto, tamanho)
- [ ] Upload em `outros/` **não** gera log — filtro de prefix funciona
- [ ] Três tipos de arquivo geram logs com prefixos diferentes: `[IMAGEM]`, `[ETL]`, `[PDF]`
- [ ] (Bônus) Filtros combinados prefix+suffix funcionam conforme o `notification-config-v2.json`

---
## Conceitos Reforçados

- **Resource-based policy é obrigatória:** sem ela o S3 recebe erro de permissão ao tentar invocar a Lambda — erro frequente na prova
- O `--principal s3.amazonaws.com` + `--source-account` evita o problema de "confused deputy"
- Filtros de prefix e suffix reduzem custo e processamento desnecessário — são aplicados **antes** da invocação
- S3 Event Notifications usa entrega **at-least-once**: o mesmo evento pode ser entregue mais de uma vez; implemente idempotência no código da Lambda
- AWS recomenda migrar para **EventBridge** em novos projetos: mesmos eventos S3, mas com roteamento por múltiplos destinos e regras avançadas
- Um bucket S3 não pode ter prefix e suffix simultâneos na **mesma regra** — use regras separadas (como no `notification-config-v2.json`)

---
## Cleanup

> **Importante:** Desprovisione os recursos para evitar cobranças futuras.

### Via script (Bash / Git Bash / WSL)

```
bash cleanup.sh
```

### Manualmente (qualquer terminal)

```
aws s3 rm s3://dva-lab2-eventos-<ACCOUNT_ID> --recursive
aws s3 rb s3://dva-lab2-eventos-<ACCOUNT_ID>

aws lambda delete-function --function-name dva-lab2-s3-processor

aws logs delete-log-group --log-group-name /aws/lambda/dva-lab2-s3-processor

aws iam detach-role-policy --role-name dva-lab2-lambda-s3-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam detach-role-policy --role-name dva-lab2-lambda-s3-role --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

aws iam delete-role --role-name dva-lab2-lambda-s3-role
```

Confirmar que os recursos foram removidos:

```
aws lambda list-functions --query "Functions[?FunctionName=='dva-lab2-s3-processor']"
aws s3 ls | grep dva-lab2
```

> No Windows/PowerShell: substitua `grep` por `Select-String -Pattern "dva-lab2"`.
