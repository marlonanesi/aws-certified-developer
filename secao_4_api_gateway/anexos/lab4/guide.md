# Instructor Guide – Lab 12: API Key e Usage Plans
> Uso interno do instrutor

---

## Abertura do Lab

Imagine que você publicou uma API e quer cobrar por ela — um plano gratuito com 100 chamadas por dia e um plano premium com 10.000. Ou simplesmente quer garantir que um parceiro não derrube seu backend à noite com um script maluco. Esse é o lab de monetização e controle de acesso. A Aula 35 explicou throttling, quotas e API Keys na teoria — agora você vai setar isso e testar na prática, vendo com os próprios olhos o 429 e o 403 aparecendo quando os limites são respeitados.

---

## Comentários por Parte

### Parte 1 — Habilitar API Key Required no Método

**Referência teórica:** Aula 35 – Usage Plans e API Keys.

- Ao marcar `API Key Required = true` no método GET, diga: *"isso é só a metade da história — habilitar o campo no método. A outra metade é existir um Usage Plan associado com uma API Key. Sem as duas partes, não funciona."*
- Reforce o aviso crítico: *"e precisa fazer deploy depois! Mudança sem deploy não tem efeito — como vimos na Aula 31."*

---

### Parte 2 — Criar os Usage Plans

**Referência teórica:** Aula 35 – Throttle (rate + burst) e Quota.

- Ao criar o `free-tier` com Rate=1 e Burst=2, contextualize: *"rate é a velocidade sustentada, burst é o pico momentâneo. Um cliente free pode fazer 1 req/s mas pode ter um pico de 2 de uma vez. Analogia: é a diferença entre velocidade máxima permitida e o quanto você pode pisar fundo por 1 segundo."*
- Ao criar o `premium`, compare os números lado a lado. O aluno precisa ver visualmente o que $$ compra: 100x mais rate, 100x mais quota.
- Ao associar a API e o Stage, diga: *"Usage Plan sem stage associado não funciona — é ele que sabe onde aplicar as regras."*

---

### Parte 3 — Criar API Keys

**Referência teórica:** Aula 35 – API Key no header `x-api-key`.

- Ao gerar a API Key e copiar o valor, *"esse valor vai no header das requisições. É o que o API Gateway usa para identificar quem está chamando — não é autenticação de identidade, é identificação de cliente para controle de quota."*
- Destaque a distinção: API Key ≠ autenticação. Para autenticação real, use IAM, Cognito ou Lambda Authorizer. API Key é para throttling e monetização.

---

### Parte 4 — Testar os Cenários

- **Sem API Key:** mostre o `403 Forbidden`. Diga: *"o gateway nem chegar na Lambda — barrou na borda."*
- **Com API Key free-tier:** dispare várias chamadas rápidas e mostre o `429 Too Many Requests` quando passar o rate limit. Conecte com a Aula 35: *"429 = throttle atingido. O cliente precisa implementar retry com exponential backoff."*
- **Com API Key premium:** mesmas chamadas passam tranquilamente. O contraste é o melhor professor.

---

## Encerramento do Lab

Seção 4 concluída! Você passou de uma API simples para um produto API com múltiplos ambientes, transformações de dados e controle granular por cliente. Esses quatro labs cobrem a grande maioria das questões de API Gateway no exame AWS Developer Associate — e mais importante, refletem como APIs reais são construídas e operadas. Na próxima seção vamos mergulhar no DynamoDB, o banco de dados NoSQL preferido de quem trabalha com serverless na AWS.
