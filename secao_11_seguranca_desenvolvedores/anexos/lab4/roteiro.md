# Lab 4 – Criptografia com AWS KMS

> **Compatibilidade de comandos CLI**
> Este roteiro apresenta blocos para **PowerShell** (Windows) e **Bash** (Linux/macOS/Git Bash/WSL).
> Blocos de base64 e manipulação de arquivo binário diferem significativamente entre os dois terminais — ambas as versões estão documentadas abaixo.
> CMD não é suportado; use PowerShell ou Bash.

---
> **Custos e Free Tier**
> - **Customer Managed Keys (CMK):** **$1,00/mês por chave** — não há free tier para CMKs
> - **Chamadas de API KMS:** $0,03 por 10.000 requisições (primeiras 20.000/mês gratuitas)
> - **AWS Managed Keys** (prefixo `aws/`): gratuitas para uso
> - **Lambda:** 1 milhão de invocações gratuitas/mês (permanente)
> - **S3:** free tier de 5 GB por 12 meses
>
> A CMK criada neste lab **gera custo de $1/mês** até ser agendada para deleção. Execute a limpeza ao finalizar.
>
> ⚠️ **Aviso importante:** qualquer recurso provisionado na AWS pode gerar custos mesmo dentro do free tier, que possui limites mensais. Ao concluir o lab, execute a etapa de limpeza para evitar cobranças inesperadas.
>
> ⚠️ **CMKs têm período mínimo de 7 dias antes da deleção efetiva.** O custo de $1/mês é cobrado até a deleção ser concluída.

---
## Objetivo

Criar uma Customer Managed Key (CMK) no AWS KMS e utilizá-la para:
1. Criptografar e descriptografar dados diretamente (até 4 KB)
2. Aplicar Envelope Encryption para dados maiores
3. Criptografar arquivos em um bucket S3 via SSE-KMS
4. Criptografar variáveis de ambiente de uma função Lambda

---
## Pré-requisitos

- Conta AWS com permissões em KMS, S3 e Lambda
- AWS CLI configurado
- Python 3 com `boto3` instalado
- `cryptography` instalado: `pip install cryptography`

---
## Parte 1 – Criar a CMK

**PowerShell:**
```powershell
# Criar CMK simétrica (ENCRYPT_DECRYPT)
$KEY_ID = aws kms create-key --description "Lab4 - CMK de demonstracao" --key-usage ENCRYPT_DECRYPT --query 'KeyMetadata.KeyId' --output text

Write-Output "Key ID: $KEY_ID"

# Criar alias para facilitar referência
aws kms create-alias --alias-name alias/lab4-cmk --target-key-id $KEY_ID

# Verificar
aws kms describe-key --key-id alias/lab4-cmk
```

**Bash:**
```bash
# Criar CMK simétrica (ENCRYPT_DECRYPT)
KEY_ID=$(aws kms create-key --description "Lab4 - CMK de demonstracao" --key-usage ENCRYPT_DECRYPT --query 'KeyMetadata.KeyId' --output text)

echo "Key ID: $KEY_ID"

# Criar alias para facilitar referência
aws kms create-alias --alias-name alias/lab4-cmk --target-key-id $KEY_ID

# Verificar
aws kms describe-key --key-id alias/lab4-cmk
```

---
## Parte 2 – Encrypt e Decrypt Direto (dados ≤ 4 KB)

**PowerShell:**
```powershell
$PLAINTEXT = "Dado sensivel: senha_db_prod_abc123"

# AWS CLI v2 exige base64 para parâmetros de blob (--plaintext)
$PLAINTEXT_B64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($PLAINTEXT))

# Criptografar
$ENCRYPTED = aws kms encrypt --key-id alias/lab4-cmk --plaintext $PLAINTEXT_B64 --query 'CiphertextBlob' --output text

Write-Output "Criptografado (base64): $ENCRYPTED"

# Descriptografar
$encBytes = [Convert]::FromBase64String($ENCRYPTED)
[IO.File]::WriteAllBytes("$PWD\encrypted.bin", $encBytes)
$decrypted = aws kms decrypt --ciphertext-blob fileb://encrypted.bin --query 'Plaintext' --output text
[System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($decrypted))
Remove-Item encrypted.bin
```

**Bash:**
```bash
PLAINTEXT="Dado sensivel: senha_db_prod_abc123"

# AWS CLI v2 exige base64 para parâmetros de blob (--plaintext)
PLAINTEXT_B64=$(echo -n "$PLAINTEXT" | base64)

# Criptografar
ENCRYPTED=$(aws kms encrypt --key-id alias/lab4-cmk --plaintext "$PLAINTEXT_B64" --query 'CiphertextBlob' --output text)

echo "Criptografado (base64): $ENCRYPTED"

# Descriptografar
echo "$ENCRYPTED" | base64 -d > encrypted.bin
DECRYPTED=$(aws kms decrypt --ciphertext-blob fileb://encrypted.bin --query 'Plaintext' --output text)
echo "$DECRYPTED" | base64 -d
rm encrypted.bin
```

Para a demonstração completa via Python, execute:
```
python kms_demo.py
```

> No Linux/macOS use `python3 kms_demo.py` se necessário.

---
## Parte 3 – Envelope Encryption (dados > 4 KB)

O script `kms_demo.py` demonstra o fluxo completo:

1. **Gerar Data Key** via `kms.generate_data_key()` → retorna a chave em plaintext e cifrada
2. **Criptografar os dados** localmente com a data key (plaintext)
3. **Descartar** a data key plaintext da memória
4. **Armazenar** os dados cifrados + data key cifrada (o KMS não armazena nada)
5. **Descriptografar:** chamar `kms.decrypt()` para recuperar a data key → usar para decifrar os dados

Execute a seção de envelope encryption:
```
python kms_demo.py --action envelope
```

> No Linux/macOS use `python3 kms_demo.py --action envelope` se necessário.

---
## Parte 4 – S3 com SSE-KMS

**PowerShell:**
```powershell
# Criar bucket (nome deve ser único globalmente)
# PowerShell: usa timestamp Unix via .NET
$BUCKET = "lab4-kms-$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"
aws s3 mb s3://$BUCKET

# Upload com AWS Managed Key
aws s3 cp roteiro.md s3://$BUCKET/arquivo-managed.md --sse aws:kms

# Upload com CMK específica
aws s3 cp roteiro.md s3://$BUCKET/arquivo-cmk.md --sse aws:kms --sse-kms-key-id alias/lab4-cmk

# Verificar metadados de criptografia
aws s3api head-object --bucket $BUCKET --key arquivo-cmk.md
```

**Bash:**
```bash
# Criar bucket (nome deve ser único globalmente)
BUCKET="lab4-kms-$(date +%s)"
aws s3 mb s3://$BUCKET

# Upload com AWS Managed Key
aws s3 cp roteiro.md s3://$BUCKET/arquivo-managed.md --sse aws:kms

# Upload com CMK específica
aws s3 cp roteiro.md s3://$BUCKET/arquivo-cmk.md --sse aws:kms --sse-kms-key-id alias/lab4-cmk

# Verificar metadados de criptografia
aws s3api head-object --bucket $BUCKET --key arquivo-cmk.md
```

> Os campos relevantes na resposta: `ServerSideEncryption` e `SSEKMSKeyId`.

---
## Parte 5 – Lambda com Variáveis de Ambiente Criptografadas

1. Console → **Lambda → Create function** ("Criar função") → name: `lab4-lambda` → Runtime: Python 3.12
2. **Configuration** ("Configuração") **→ Environment variables** ("Variáveis de ambiente") **→ Edit** ("Editar")
3. Adicionar: `DB_PASSWORD` = `MinhaS3nh@123`
4. Expandir **Encryption configuration** → selecionar `alias/lab4-cmk`
5. Salvar
6. Usar o código:
```python
import os

def lambda_handler(event, context):
    db_password = os.environ.get('DB_PASSWORD', '')
    return {
        'statusCode': 200,
        'body': f"Password length: {len(db_password)}"
    }
```

O valor é decriptado automaticamente pela Lambda no momento da inicialização usando a CMK.

---
## Pontos de Verificação

- No CloudTrail, cada chamada `Encrypt`/`Decrypt` gera um evento auditável com `KeyId`
- Sem a permissão `kms:Decrypt` na policy do chamador → `AccessDeniedException`
- A Key Policy no console mostra o statement `EnableIAMAccess` que delega controle ao IAM
- O `CiphertextBlob` contém metadados que identificam qual CMK foi usada (o KMS sabe descriptografar sem precisar indicar a key)

---
## Limpeza

**PowerShell:**
```powershell
# Remover alias antes de agendar deleção
aws kms delete-alias --alias-name alias/lab4-cmk

# Agendar deleção da CMK (mínimo 7 dias — custo encerrado após deleção efetiva)
aws kms schedule-key-deletion --key-id $KEY_ID --pending-window-in-days 7

# Deletar bucket S3
aws s3 rb s3://$BUCKET --force

# Deletar Lambda
aws lambda delete-function --function-name lab4-lambda
```

**Bash:**
```bash
# Remover alias antes de agendar deleção
aws kms delete-alias --alias-name alias/lab4-cmk

# Agendar deleção da CMK
aws kms schedule-key-deletion --key-id $KEY_ID --pending-window-in-days 7

# Deletar bucket S3
aws s3 rb s3://$BUCKET --force

# Deletar Lambda
aws lambda delete-function --function-name lab4-lambda
```
