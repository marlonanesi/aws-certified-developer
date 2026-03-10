# Instructor Guide – Lab 15: Query vs Scan na Prática
> Uso interno do instrutor

---

## Abertura do Lab

Esse é o lab do "vendo para crer". A Aula 44 afirmou que Scan é lento e caro — mas quanto mais lento? Quanto mais caro? Agora vamos medir. Vamos criar uma tabela com 200+ itens, executar Query e Scan para o mesmo resultado, e comparar as métricas na sua cara. Spoiler: a diferença é chocante. E quando você ver o `ConsumedCapacity` de cada operação, você nunca mais vai olhar para um `scan()` da mesma forma.

---

## Comentários por Parte

### Parte 1 — Popular a Tabela

**Referência teórica:** Aula 44 – Query vs Scan, custo em RCU + Aula 42 – Distribuição de dados.

- Ao usar `batch_writer`, diga: *"BatchWriteItem agrupa até 25 PutItem em uma única chamada. No free tier isso é importante — mas em produção, o benefício real é reduzir o número de round-trips ao DynamoDB."*
- Após popular, mostre o `scan(Select='COUNT')` para contar itens. Pergunte: *"se eu tivesse pedido Count com uma condição, isso ainda seria Scan? Sim. O Select='COUNT' cobra RCUs sobre todos os itens lidos — o filtro vem depois."*

---

### Parte 2 — Query vs Scan: Comparação Direta

**Referência teórica:** Aula 44 – Query obrigatoriamente usa PK, Scan lê tudo.

- Ao executar o **Query** para um usuário específico, destaque o tempo de resposta e os `ConsumedCapacity`. Diga: *"o Query foi direto na partição do USER#0010 — não olhou para mais nenhum item da tabela."*
- Ao executar o **Scan** com `FilterExpression` para o mesmo usuário, mostre o `ScannedCount` vs `Count`: *"ScannedCount = quantos itens o DynamoDB leu. Count = quantos voltaram. Aqui ele leu 200 itens para retornar 4. E cobraram RCU por todos os 200."*
- Pause aqui e deixe o número impactar: *"a query pagou por 4 leituras. O scan pagou por 200. Para uma tabela de 1 milhão de itens, essa diferença é devastadora."*

---

### Parte 3 — FilterExpression e ProjectionExpression

**Referência teórica:** Aula 44 – FilterExpression não reduz custo, só o resultado.

- Ao mostrar `FilterExpression` no Scan com status='pending': *"atenção — FilterExpression é aplicado DEPOIS da leitura. O DynamoDB já consumiu RCU de todos os itens antes de filtrar. É diferente de KeyConditionExpression no Query, que evita a leitura desnecessária desde o início."*
- No `ProjectionExpression`, mostre como reduzir os atributos retornados: *"isso não reduz RCU — o item lido ainda é o mesmo. Mas reduz tráfego de rede e memória no lado da aplicação."*

---

### Parte 4 — Parallel Scan

**Referência teórica:** Aula 44 – quando Scan é inevitável, otimize.

- Ao mostrar Parallel Scan com `TotalSegments=4`: *"quando você realmente precisa fazer um Scan completo — export de dados, migração, análise pontual — Parallel Scan divide a tabela em segmentos e processa em threads paralelas. 4x mais rápido, mas 4x mais RCU consumido ao mesmo tempo. Cuidado com throttling."*
- Compare o tempo do scan sequencial vs parallel — o impacto visual ajuda a gravar o tradeoff.

---

## Encerramento do Lab

Agora você tem os números. Query é cirúrgico, Scan é bruto. A regra prática: se você perceber que está fazendo Scans frequentes em produção, é um sinal claro de que a tabela precisa ser redesenhada — provavelmente com um GSI para o padrão de acesso que você está forçando via Scan. Esse insight vale mais do que qualquer questão de exame. No próximo e último lab de DynamoDB, vamos para um nível acima: processar mudanças na tabela em tempo real com DynamoDB Streams e Lambda.
