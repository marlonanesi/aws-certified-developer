# Lab — Criando Tabela DynamoDB e Operações CRUD

> **Aviso de compatibilidade de comandos**
> Os comandos deste roteiro sao referencias e podem precisar de adaptacao
> conforme o SO e terminal utilizados (PowerShell, Bash, Zsh, CMD, etc.).
> Converta a sintaxe antes de executar se necessario.
>
> Sugestao de prompt para IA generativa:
> "Converta o comando abaixo para meu SO [Windows/macOS/Linux] e terminal
> [PowerShell/Bash/Zsh/CMD]. Adapte variaveis, redirecionamentos e pipes
> para o equivalente nesse ambiente: <cole o comando aqui>"

> **Aviso de custos:** Recursos criados na AWS podem gerar cobranças, mesmo que pequenas. O DynamoDB oferece um nível gratuito permanente de 25 GB de armazenamento, 25 WCU e 25 RCU (suficiente para este lab). Ainda assim, revise o uso na aba **Billing** do console. **Ao finalizar, desprovisione todos os recursos criados.**

---
## Objetivo

Criar uma tabela DynamoDB com chave composta (Partition Key + Sort Key) e executar as quatro operações fundamentais: Create, Read, Update e Delete, utilizando CLI e Python (boto3).

---
## Pré-requisitos

- AWS CLI configurada com credenciais válidas
- Python 3.x instalado com boto3 (`pip install boto3`)
- Permissões IAM para DynamoDB (console e CLI)

---
## Parte 1 — Criar a Tabela via Console

1. Acesse o console AWS e navegue para **DynamoDB > Tables > Create table** ("Criar tabela").
2. Preencha os campos:

   | Campo | Valor |
   |---|---|
   | Table name | `DVA-Lab-Orders` |
   | Partition key | `PK` (String) |
   | Sort key | `SK` (String) |
   | Capacity mode | On-demand |

3. Clique em **Create table** ("Criar tabela") e aguarde o status **Active**.

4. Verifique via CLI:

   ```
   aws dynamodb describe-table --table-name DVA-Lab-Orders --query "Table.{Nome:TableName,Status:TableStatus,Chaves:KeySchema}"
   ```

---
## Parte 2 — Operações CRUD com Python

O arquivo `dynamodb_crud.py` contém todas as operações prontas para execução.

1. Revise o arquivo para entender cada função antes de executar.
2. Confirme que a região no código corresponde à sua:

   ```python
   dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
   ```

3. Execute:

   ```
   python dynamodb_crud.py
   ```

4. Observe a saída — ela mostra o resultado de cada operação e executa uma query final para confirmar o estado após update e delete.

---
## Parte 3 — Operações via CLI (Complementar)

Pratique as mesmas operações diretamente no terminal para fixar o formato DynamoDB JSON (tipo explícito):

### PutItem

```
aws dynamodb put-item --table-name DVA-Lab-Orders --item '{
    "PK": {"S": "USER#003"},
    "SK": {"S": "PROFILE"},
    "name": {"S": "Ana Costa"},
    "email": {"S": "ana@email.com"}
  }'
```

### GetItem

```
aws dynamodb get-item --table-name DVA-Lab-Orders --key '{"PK": {"S": "USER#003"}, "SK": {"S": "PROFILE"}}'
```

### UpdateItem

```
aws dynamodb update-item --table-name DVA-Lab-Orders --key '{"PK": {"S": "USER#003"}, "SK": {"S": "PROFILE"}}' --update-expression "SET city = :c" --expression-attribute-values '{":c": {"S": "Curitiba"}}' --return-values ALL_NEW
```

### DeleteItem

```
aws dynamodb delete-item --table-name DVA-Lab-Orders --key '{"PK": {"S": "USER#003"}, "SK": {"S": "PROFILE"}}' --return-values ALL_OLD
```

---
## Pontos de Verificação

- [ ] Tabela criada com PK (String) e SK (String) no modo on-demand
- [ ] Script Python executado com sucesso — todas as operações concluídas
- [ ] Query final mostra 2 pedidos (ORDER#2024-001 e ORDER#2024-002 — o terceiro foi deletado)
- [ ] Status do ORDER#2024-002 exibido como `shipped` após o update
- [ ] Operações CLI retornam os dados esperados

---
## Conceitos Reforçados

- **PutItem** substitui o item inteiro se a chave já existir
- **GetItem** exige PK + SK completos — é O(1), não faz scan
- **UpdateItem** modifica apenas os atributos especificados — o resto é preservado
- **ExpressionAttributeNames** é necessário para atributos com nome reservado (ex.: `status`)
- **ReturnValues** permite recuperar o estado anterior ou posterior sem uma segunda leitura
- Formato CLI usa tipo explícito: `{"S": "valor"}`, `{"N": "123"}`, `{"BOOL": true}`

---
## Cleanup

> **Importante:** Desprovisione os recursos para evitar cobranças futuras.

```
aws dynamodb delete-table --table-name DVA-Lab-Orders
```

Confirme a exclusão:

```
aws dynamodb list-tables --query "TableNames"
```
