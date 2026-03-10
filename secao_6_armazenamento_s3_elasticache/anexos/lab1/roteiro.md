# Lab — Presigned URLs: Acesso Temporário Seguro ao S3

> **Aviso de compatibilidade de comandos**
> Os comandos deste roteiro sao referencias e podem precisar de adaptacao
> conforme o SO e terminal utilizados (PowerShell, Bash, Zsh, CMD, etc.).
> Converta a sintaxe antes de executar se necessario.
>
> Sugestao de prompt para IA generativa:
> "Converta o comando abaixo para meu SO [Windows/macOS/Linux] e terminal
> [PowerShell/Bash/Zsh/CMD]. Adapte variaveis, redirecionamentos e pipes
> para o equivalente nesse ambiente: <cole o comando aqui>"

> **Aviso de custos:** O S3 oferece Free Tier de 5 GB de armazenamento, 20.000 GETs e 2.000 PUTs por mês (primeiros 12 meses). Este lab utiliza poucos objetos pequenos, mantendo-se dentro do Free Tier para a grande maioria dos casos. Ainda assim, revise o uso na aba **Billing** e **desprovisione todos os recursos ao finalizar.**

---
## Objetivo

Gerar Presigned URLs temporárias que permitem acesso controlado a objetos privados do S3 sem expor credenciais AWS. Compreender a diferença entre `generate_presigned_url` (GET/PUT) e `generate_presigned_post` (formulários com validações).

---
## Pré-requisitos

- AWS CLI configurada com credenciais válidas
- Python 3.x instalado com `boto3` e `requests`:

  ```
  pip install boto3 requests
  ```

- Permissões IAM para S3 (criação de bucket, put/get de objetos)

---
## Parte 1 — Criar o Bucket e o Objeto de Teste

### Obter o Account ID e a região configurada

```
aws sts get-caller-identity --query Account --output text
aws configure get region
```

Anote os valores — eles compõem o nome do bucket:

```
dva-lab1-s3-dva-presigned-<ACCOUNT_ID>
```

### Criar o bucket

Para `sa-east-1`:

```
aws s3api create-bucket --bucket dva-lab1-s3-dva-presigned-<ACCOUNT_ID>
```

Para qualquer outra região:

```
aws s3api create-bucket --bucket dva-lab1-s3-dva-presigned-<ACCOUNT_ID> --create-bucket-configuration LocationConstraint=sa-east-1
```

### Enviar um objeto de teste (necessário para o script de download)

Crie um arquivo local e faça upload:

```
aws s3 cp arquivo-teste.txt s3://dva-lab1-s3-dva-presigned-<ACCOUNT_ID>/arquivo-teste.txt
```

> No Windows/PowerShell, crie o arquivo com `New-Item arquivo-teste.txt` ou `Set-Content arquivo-teste.txt "Conteudo de teste para presigned URL"`.

### Confirmar que o bucket está privado

```
aws s3api get-bucket-acl --bucket dva-lab1-s3-dva-presigned-<ACCOUNT_ID>
```

---
## Parte 2 — Editar os Scripts Python

Nos três arquivos, localize a constante `BUCKET_NAME` e substitua pelo nome real do bucket criado:

```python
BUCKET_NAME = "dva-lab1-s3-dva-presigned-<ACCOUNT_ID>"
```

---
## Parte 3 — Presigned URL para Download (GET)

O arquivo `generate_presigned_download.py` gera duas URLs:
- Uma com validade de 1 hora
- Uma com validade de 10 segundos (para testar o comportamento após expiração)

Execute:

```
python generate_presigned_download.py
```

**Após a execução:**

1. Copie a URL de 1 hora e acesse-a no navegador — o conteúdo do arquivo deve ser exibido sem autenticação.
2. Aguarde 10 segundos e acesse a URL curta — o S3 deverá retornar erro `ExpiredToken` ou `Request has expired`.
3. Observe que a URL foi gerada **localmente** (sem round-trip ao S3) — a autenticação ocorre apenas no momento do uso.

---
## Parte 4 — Presigned URL para Upload (PUT)

O arquivo `generate_presigned_upload.py` gera uma URL de upload e simula o envio usando `requests.put`.

Execute:

```
python generate_presigned_upload.py
```

**Após a execução:**

Confirme que o objeto foi criado no bucket:

```
aws s3 ls s3://dva-lab1-s3-dva-presigned-<ACCOUNT_ID>/
```

O arquivo `upload-via-put.txt` deve aparecer na listagem.

> **PUT vs POST:** A URL PUT é ideal para apps server-to-server. Não permite impor restrições de tamanho ou content-type no lado do S3 — essas validações ficam a cargo do backend.

---
## Parte 5 — Presigned POST com Condições (Formulários Web)

O arquivo `generate_presigned_post.py` gera um formulário POST com restrições de content-type e tamanho (máximo 10 MB).

Execute:

```
python generate_presigned_post.py
```

**Observe na saída:**

- O campo `url` é o endpoint do S3 (não contém a chave do objeto — ela vai nos campos do formulário).
- O campo `fields` contém todos os campos obrigatórios que o cliente (browser/app) deve enviar junto com o arquivo.
- O script cria um arquivo de teste local e realiza o upload automaticamente via `requests.post`.
- O S3 retorna **HTTP 204** para uploads bem-sucedidos via POST (sem body de resposta).

> **Para produção:** o backend entrega `url` + `fields` ao browser; o browser faz o POST diretamente ao S3 sem passar pelo servidor.

---
## Pontos de Verificação

- [ ] Bucket criado e confirmado como privado
- [ ] `generate_presigned_download.py` executado — URL de 1h funciona no navegador sem credenciais
- [ ] URL de 10 segundos falha após a expiração com erro de assinatura
- [ ] `generate_presigned_upload.py` executado — objeto `upload-via-put.txt` visível no bucket
- [ ] `generate_presigned_post.py` executado — retorno HTTP 204 confirmado
- [ ] Diferença entre PUT (simples) e POST (com condições) compreendida

---
## Conceitos Reforçados

- Presigned URL é assinada com as credenciais do **gerador** — quem usa a URL age com as permissões desse IAM entity
- A URL é gerada **localmente** pelo SDK — nenhuma chamada vai ao S3 no momento da geração
- `ExpiresIn` define a janela de acesso; para produção, 15–60 minutos é o intervalo recomendado
- `generate_presigned_url` com `put_object` → upload direto (método HTTP PUT); sem restrições de tamanho no S3
- `generate_presigned_post` → formulário multipart; permite validar content-type e tamanho **no S3** via `Conditions`
- Erro `SignatureDoesNotMatch` indica que a URL foi modificada ou copiada incompleta
- Na prova: "acesso temporário a objeto privado do S3 sem expor credenciais" = Presigned URL

---
## Cleanup

> **Importante:** Desprovisione os recursos para evitar cobranças futuras.

Remover todos os objetos e o bucket:

```
aws s3 rb s3://dva-lab1-s3-dva-presigned-<ACCOUNT_ID> --force
```

Confirmar que o bucket foi removido:

```
aws s3 ls | Select-String -Pattern dva-lab1-s3-dva
```

> No Windows/PowerShell: substitua `grep` por `Select-String -Pattern "dva-lab1-s3-dva"`.
