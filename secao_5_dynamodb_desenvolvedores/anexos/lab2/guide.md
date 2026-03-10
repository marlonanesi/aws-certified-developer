# Instructor Guide – Lab 14: Implementando GSI para Queries Alternativas
> Uso interno do instrutor

---

## Abertura do Lab

Acabamos o Lab 1 com um problema real: nossa tabela é rápida para buscar pedidos por usuário, mas e se o time de suporte precisar listar todos os pedidos com status "pending"? Com a tabela atual, a única opção seria um Scan — lento e caro. Nas aulas você viu que GSI resolve exatamente isso: cria uma visão alternativa da tabela sem alterar nada na estrutura original. Hoje vamos criar dois índices diferentes e ver o poder das queries alternativas sem gastar um centavo a mais de leitura desnecessária.

---

## Comentários por Parte

### Parte 1 — Inserir Dados Adicionais

**Referência teórica:** Aula 39 – Design single-table, padrões de acesso.

- Ao inserir itens de múltiplos usuários, reforce o padrão: *"perceba que USER#002 e USER#003 têm a mesma estrutura de PK+SK que o USER#001 do lab anterior. Uma tabela, múltiplos usuários — cada um isolado pela PK."*
- Mencione que adicionamos o atributo `category` pensando já nos índices que vamos criar. Em DynamoDB, o design orientado a acesso começa antes de inserir o primeiro item.

---

### Parte 2 — Criar GSI via Console

**Referência teórica:** Aula 42 – Cardinalidade e distribuição + design de índices.

- Ao criar o GSI com `status` como PK, conecte com a Aula 42: *"lembrando: em uma tabela base, 'status' seria uma PK terrível pela baixa cardinalidade. Em um GSI, isso é aceitável porque é um acesso específico e controlado — não é a distribuição principal da tabela."*
- Ao adicionar `date` como SK do GSI: *"agora posso buscar 'todos os pedidos pending ordenados por data'. Dois atributos trabalhando juntos — exatamente o pattern da Sort Key."*
- Mostre que criar um GSI em uma tabela existente funciona sem downtime — reforça a característica fully managed do DynamoDB.

---

### Parte 3 — Queries via GSI com boto3

**Referência teórica:** Aula 44 – Query vs Scan, eficiência de leitura.

- Ao executar o query no GSI por status, mostre o `IndexName` no código: *"é obrigatório dizer qual índice você está consultando. Sem isso, ele vai na tabela base e precisaria da PK do usuário."*
- Compare o `ConsumedCapacity` entre o query no GSI vs um `scan` com FilterExpression: *"o query no GSI consumiu 0.5 RCU. O scan consumiu X RCU — mesmo que o resultado final seja o mesmo. É por isso que GSI existe."*
- Ao criar o segundo GSI com `category`, mostre que você pode ter até 20 GSIs por tabela — cada um atendendo um padrão de acesso diferente.

---

### Parte 4 — GSI Projections

- Ao configurar `ALL` vs `KEYS_ONLY`, use a analogia: *"KEYS_ONLY é o índice de um livro — tem a referência mas você precisa ir buscar o conteúdo completo. ALL é o índice com o capítulo inteiro copiado — mais rápido, mas ocupa mais espaço e custa mais para manter atualizado."*
- Mostre que `ProjectionExpression` nos queries controla quais atributos retornam — reduz tráfego de rede e custo.

---

## Encerramento do Lab

GSI é um dos recursos mais poderosos do DynamoDB — e um dos mais cobrados no exame. Você acabou de ver que com dois índices bem planejados, nossa tabela atende quatro padrões de acesso diferentes sem nenhum Scan. Esse é o princípio: design orientado a acesso, não a entidade. No próximo lab fechamos o comparativo definitivo entre Query e Scan, incluindo como usar Parallel Scan quando você realmente precisa percorrer a tabela inteira.
