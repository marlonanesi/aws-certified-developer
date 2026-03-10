# Lab — Global Secondary Indexes (GSI) para Padrões de Acesso Alternativos

> **Aviso de compatibilidade de comandos**
> Os comandos deste roteiro sao referencias e podem precisar de adaptacao
> conforme o SO e terminal utilizados (PowerShell, Bash, Zsh, CMD, etc.).
> Converta a sintaxe antes de executar se necessario.
>
> Sugestao de prompt para IA generativa:
> "Converta o comando abaixo para meu SO [Windows/macOS/Linux] e terminal
> [PowerShell/Bash/Zsh/CMD]. Adapte variaveis, redirecionamentos e pipes
> para o equivalente nesse ambiente: <cole o comando aqui>"

> **Aviso de custos:** Recursos criados na AWS podem gerar cobranças. O DynamoDB oferece nível gratuito permanente de 25 GB, 25 WCU e 25 RCU. GSIs em modo on-demand não têm custo fixo adicional, mas consomem RCUs separadas das da tabela base. Revise a aba **Billing** ao final. **Desprovisione todos os recursos ao terminar.**

---
## Objetivo

Criar Global Secondary Indexes (GSI) em uma tabela DynamoDB existente para habilitar padrões de acesso que seriam impossíveis (ou muito caros) com a chave primária original.

---
## Pré-requisitos

- Tabela `DVA-Lab-Orders` do lab anterior com itens inseridos
- Se não tiver a tabela, execute o lab anterior (lab1) primeiro
- Python 3.x com boto3 instalado

---
## Contexto

A tabela `DVA-Lab-Orders` tem `PK` como Partition Key e `SK` como Sort Key. Com essa estrutura é possível:

| Operação | Possível? |
|---|---|
| Buscar perfil por `USER#ID` | Sim — GetItem |
| Buscar todos os pedidos de um usuário | Sim — Query com begins\_with |
| Buscar pedidos por **status** | Não — apenas Scan (caro) |
| Buscar pedidos por **categoria** e valor | Não — apenas Scan (caro) |

A solução é criar GSIs que indexam esses atributos.

---
## Parte 1 — Inserir Dados Adicionais

Execute o script de setup para enriquecer a tabela com mais pedidos e os atributos que serão indexados:

```
python setup_dados.py
```

O script insere pedidos com os campos `status`, `category` e `total` que os GSIs irão indexar.

---
## Parte 2 — Criar os GSIs

### Via Console

1. Acesse **DynamoDB > Tables > DVA-Lab-Orders > Indexes > Create index** ("Criar índice").

2. Crie o primeiro GSI:

   | Campo | Valor |
   |---|---|
   | Partition key | `status` (String) |
   | Sort key | `date` (String) |
   | Index name | `status-date-index` |
   | Projected attributes | All |

3. Aguarde o status **Active** (1–2 minutos), depois crie o segundo:

   | Campo | Valor |
   |---|---|
   | Partition key | `category` (String) |
   | Sort key | `total` (Number) |
   | Index name | `category-total-index` |
   | Projected attributes | All |

### Via CLI (alternativa)

```
aws dynamodb update-table --table-name DVA-Lab-Orders --attribute-definitions AttributeName=status,AttributeType=S AttributeName=date,AttributeType=S --global-secondary-index-updates '[{
    "Create": {
      "IndexName": "status-date-index",
      "KeySchema": [
        {"AttributeName": "status", "KeyType": "HASH"},
        {"AttributeName": "date", "KeyType": "RANGE"}
      ],
      "Projection": {"ProjectionType": "ALL"}
    }
  }]'
```

> Aguarde o primeiro GSI ficar **Active** antes de criar o segundo — a CLI aceita apenas um por vez.

```
# Verificar status dos índices
aws dynamodb describe-table --table-name DVA-Lab-Orders --query "Table.GlobalSecondaryIndexes[*].{Nome:IndexName,Status:IndexStatus}"
```

---
## Parte 3 — Consultas via GSI

Após os dois GSIs estarem **Active**, execute:

```
python dynamodb_gsi_queries.py
```

O script demonstra:
1. Query por status (`pending`, `delivered`) via `status-date-index`
2. Query por status com filtro de intervalo na sort key (date range)
3. Query por categoria ordenada por valor total via `category-total-index`
4. Query por categoria com mínimo de valor (range na sort key numérica)
5. Comparação direta entre Scan+Filter e Query via GSI — observação de RCUs

---
## Pontos de Verificação

- [ ] Dois GSIs criados e com status **Active**
- [ ] Query por `status='pending'` retorna apenas itens com esse status
- [ ] Query por categoria com `ScanIndexForward=False` retorna itens do maior para o menor total
- [ ] Comparação mostra que Scan examina **todos** os itens da tabela; Query via GSI examina apenas os relevantes

---
## Conceitos Reforçados

- GSIs permitem queries em atributos que não são PK/SK da tabela base
- Um GSI tem sua própria PK (e SK opcional) independente da tabela
- **Projected attributes** define quais atributos são copiados para o índice (`ALL`, `KEYS_ONLY`, `INCLUDE`)
- `ScanIndexForward=False` inverte a ordenação pela sort key
- GSIs têm latência de replicação eventual — novos itens podem demorar milissegundos para aparecer no índice
- O custo de Scan escala linearmente com o tamanho da tabela; Query via GSI escala com o resultado

---
## Cleanup

> **Importante:** Desprovisione para evitar cobranças.

```
aws dynamodb delete-table --table-name DVA-Lab-Orders
```

Os GSIs são removidos junto com a tabela.
