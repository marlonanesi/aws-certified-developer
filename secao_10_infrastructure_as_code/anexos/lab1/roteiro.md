# Roteiro — Lab 1: Stack CloudFormation com S3, IAM e Lambda

> **Compatibilidade de comandos CLI**
> Os comandos avulsos deste roteiro funcionam diretamente em **PowerShell** (Windows) e **Bash** (Linux/macOS/Git Bash) — basta colar e executar.
> Onde há diferença de sintaxe entre os dois shells, o roteiro apresenta as duas versões lado a lado.
> Para CMD ou outros terminais, converta a sintaxe com ajuda de IA generativa.

## Custos e Free Tier

| Serviço | Free Tier |
|---------|-----------|
| CloudFormation | Gratuito (cobranças são dos recursos provisionados) |
| S3 | 5 GB storage + 20k GET + 2k PUT (primeiros 12 meses) |
| Lambda | 1 milhão de invocações/mês + 400k GB-s (permanente) |
| IAM | Gratuito |

> **Aviso:** Recursos na nuvem podem gerar custos mesmo dentro do Free Tier, pois ele tem limites mensais e pode ser esgotado. Ao finalizar a prática, **delete a stack** — o CloudFormation removerá todos os recursos criados automaticamente (exceto o bucket, que precisa estar vazio).

---
## Objetivo

Criar uma stack CloudFormation completa que provisiona um bucket S3, uma role IAM e uma função Lambda, utilizando Intrinsic Functions (`!Ref`, `!GetAtt`, `!Sub`), parâmetros e outputs exportados.

---
## Parte 1 — Revisar o Template

O arquivo `lab1-stack.yaml` desta pasta contém o template completo. Antes de criar a stack, observe:

- **`Parameters`**: `EnvironmentName` com valores permitidos `dev/staging/prod` e padrão `dev`
- **`!Sub '${EnvironmentName}-${AWS::AccountId}'`**: garante nome de bucket globalmente único
- **`!GetAtt LambdaExecutionRole.Arn`**: referencia o ARN da role de uma forma que cria dependência automática (CloudFormation cria a Role antes da Lambda)
- **`!Ref AppBucket`** na variável de ambiente: passa o nome do bucket para o código Lambda
- **`Outputs` com `Export`**: permite que outras stacks importem esses valores via `Fn::ImportValue`

---
## Parte 2 — Criar a Stack via Console

1. CloudFormation → **Create stack** ("Criar stack") → **With new resources** ("Com novos recursos")
2. *Specify template* → **Upload a template file** → selecione `lab1-stack.yaml`
3. **Stack name:** `lab1-cfn-stack`
4. **EnvironmentName:** `dev` (padrão)
5. Clique em **Next** → **Next** → marque o checkbox **"I acknowledge that AWS CloudFormation might create IAM resources"** → **Submit**

---
## Parte 3 — Acompanhar a Criação

Na aba **Events**, observe os recursos sendo criados:

> **Como ler a aba Events:** os eventos são exibidos em **ordem cronológica inversa** — o evento mais recente fica no **topo**. Você verá vários `CREATE_IN_PROGRESS` no meio da lista; isso é normal, são os estados intermediários de cada recurso. A stack está concluída quando o **primeiro evento do topo** (o mais recente) mostrar o nome da própria stack com status `CREATE_COMPLETE`.

- A **Role IAM** é criada antes da Lambda (dependência resolvida automaticamente via `!GetAtt`)
- Aguarde status `CREATE_COMPLETE`
- Acesse a aba **Outputs** para ver os valores exportados (BucketName, BucketArn, FunctionName, FunctionArn)

---
## Parte 4 — Testar a Lambda

CloudFormation → Outputs → copie o **FunctionName**.

Lambda → Functions → `[nome]` → **Test**:

```json
{"key": "test"}
```

Resposta esperada:
```json
{
  "statusCode": 200,
  "body": "{\"message\": \"Hello from CloudFormation!\", \"bucket\": \"lab1-app-bucket-dev-...\", \"environment\": \"dev\"}"
}
```

---
## Parte 5 — Explorar via CLI

```
# Listar stacks ativas
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE

# Ver outputs da stack
aws cloudformation describe-stacks --stack-name lab1-cfn-stack --query "Stacks[0].Outputs"

# Ver todos os recursos da stack
aws cloudformation list-stack-resources --stack-name lab1-cfn-stack
```

---
## Parte 6 — Atualizar com Change Set

Um Change Set mostra exatamente o que será alterado antes de aplicar — fundamental para produção.

No template `lab1-stack.yaml`, a tag `ManagedBy: CloudFormation` já está incluída. Para simular uma atualização, abra `lab1-stack.yaml` e adicione uma segunda tag ao bucket — acrescente as linhas abaixo logo após `Value: CloudFormation`:

```yaml
        - Key: Version
          Value: v2
```

O bloco `Tags` do bucket ficará assim: 

```yaml
      Tags:
        - Key: Environment
          Value: !Ref EnvironmentName
        - Key: ManagedBy
          Value: CloudFormation
        - Key: Version
          Value: v2
```

Salve o arquivo antes de fazer o upload no Change Set. 

**Criar Change Set:**
1. Console → CloudFormation → stack `lab1-cfn-stack` → **Stack actions** ("Ações da stack") → **Create change set for current stack" ("Criar conjunto de alterações para a stack atual")
2. Upload do template modificado
3. Observe o Change Set detalhando apenas os recursos e propriedades afetados
4. **Execute change set**

---
## Pontos de Atenção

- **Dependências automáticas:** `!GetAtt` e `!Ref` entre recursos criam ordem de criação implícita — sem precisar de `DependsOn` explícito
- **`!Sub` vs `!Join`:** `!Sub` é mais legível para interpolação de strings; `!Join` é útil para listas
- **`!GetAtt` vs `!Ref`:** `!Ref` em uma Lambda retorna o nome; `!GetAtt AppFunction.Arn` retorna o ARN
- **IAM capabilities:** obrigatório marcar no wizard ao criar recursos IAM — protege contra criação acidental de permissões amplas
- **Rollback automático:** se algum recurso falha na criação, CloudFormation reverte todos os já criados
- **Exports e imports:** um Output exportado não pode ser deletado enquanto outra stack o estiver importando

---
## Erros Comuns

| Erro | Causa | Solução |
|------|-------|---------|
| `ROLLBACK_COMPLETE` | Algum recurso falhou | Verificar aba Events para o erro específico |
| Bucket name already exists | Nome não único globalmente | `!Sub` com `${AWS::AccountId}` garante unicidade |
| IAM capabilities required | Template cria recursos IAM | Marcar o checkbox no wizard |
| Cannot delete stack — exports in use | Output importado por outra stack | Deletar a stack que importa primeiro |

---
## Limpeza

**PowerShell:**
```powershell
# Esvaziar o bucket antes (necessário para CloudFormation conseguir deletá-lo)
$ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
aws s3 rm "s3://lab1-app-bucket-dev-$ACCOUNT_ID" --recursive

# Deletar a stack (remove todos os recursos)
aws cloudformation delete-stack --stack-name lab1-cfn-stack
```

**Bash:**
```bash
# Esvaziar o bucket antes (necessário para CloudFormation conseguir deletá-lo)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws s3 rm s3://lab1-app-bucket-dev-${ACCOUNT_ID} --recursive

# Deletar a stack (remove todos os recursos)
aws cloudformation delete-stack --stack-name lab1-cfn-stack
```
