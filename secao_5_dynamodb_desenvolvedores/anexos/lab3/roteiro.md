# Lab — Query vs Scan: Comparação Prática de Performance e Custo

> **Aviso de compatibilidade de comandos**
> Os comandos deste roteiro sao referencias e podem precisar de adaptacao
> conforme o SO e terminal utilizados (PowerShell, Bash, Zsh, CMD, etc.).
> Converta a sintaxe antes de executar se necessario.
>
> Sugestao de prompt para IA generativa:
> "Converta o comando abaixo para meu SO [Windows/macOS/Linux] e terminal
> [PowerShell/Bash/Zsh/CMD]. Adapte variaveis, redirecionamentos e pipes
> para o equivalente nesse ambiente: <cole o comando aqui>"

> **Aviso de custos:** Operações na AWS podem gerar cobranças. O DynamoDB tem nível gratuito permanente de 25 GB, 25 WCU e 25 RCU. Este lab usa o modo **PROVISIONED** — o custo fica dentro do free tier. Use uma tabela nova e remova ao final. Revise o uso na aba **Billing**. **Desprovisione todos os recursos ao terminar para evitar surpresas mesmo dentro do free tier.**

---
## Objetivo

Comparar na prática a diferença de performance e custo (RCUs) entre Query e Scan, incluindo o comportamento de FilterExpression, ProjectionExpression, paginação e ordenação.

---
## Pré-requisitos

- Python 3.x com boto3 instalado
- AWS CLI configurada com permissões para DynamoDB

---
## Parte 1 — Criar e Popular a Tabela de Teste

O script `setup_tabela.py` cria uma nova tabela `DVA-Lab-QueryScan` e insere aproximadamente 200 itens (50 usuários com 1–4 pedidos cada).

```
python setup_tabela.py
```

Aguarde a mensagem de conclusão antes de prosseguir.

---
## Parte 2 — Executar os Testes Comparativos

```
python query_vs_scan.py
```

O script executa cinco testes em sequência:

| Teste | O que demonstra |
|---|---|
| 1 — Query vs Scan single user | Query consome drasticamente menos RCUs que Scan para o mesmo resultado |
| 2 — FilterExpression myth | Filter reduz dados **retornados**, mas RCUs são os mesmos que sem filtro |
| 3 — ProjectionExpression | Reduz payload de rede; RCUs baseados no tamanho do item na tabela |
| 4 — Paginação | `Limit` + `LastEvaluatedKey` — como iterar sobre todos os itens de forma controlada |
| 5 — ScanIndexForward | Controla ordenação ASC/DESC pela Sort Key sem custo adicional |

---
## Pontos de Verificação

- [ ] Teste 1: Query usa significativamente menos RCUs que Scan para o mesmo conjunto de resultados
- [ ] Teste 2: Scan com `FilterExpression(status=cancelled)` consome os **mesmos** RCUs que Scan sem filtro
- [ ] Teste 3: ProjectionExpression reduz os campos retornados mas RCUs permanecem iguais
- [ ] Teste 4: Paginação via `LastEvaluatedKey` retorna todos os itens em múltiplas páginas
- [ ] Teste 5: `ScanIndexForward=False` inverte a ordem dos resultados na Query

---
## Conceitos Reforçados

- **Query** usa o índice da PK — escala com o resultado, não com o tamanho da tabela
- **Scan** lê cada item da tabela — custo proporcional ao tamanho total, independente do filtro
- **FilterExpression** é aplicado **após** a leitura — não reduz RCUs, só limita o payload retornado
- **ProjectionExpression** reduz bytes transferidos pela rede, mas RCUs são calculados pelo tamanho do item no storage
- **ReturnConsumedCapacity='TOTAL'** é a forma correta de medir custo real de cada operação
- **Limit** controla itens **examinados** por request; combine com `LastEvaluatedKey` para paginação correta
- Scan frequente em produção é sinal para redesenhar o modelo de dados ou criar um GSI

---
## Cleanup

> **Importante:** Desprovisione para evitar cobranças.

```
aws dynamodb delete-table --table-name DVA-Lab-QueryScan
```
