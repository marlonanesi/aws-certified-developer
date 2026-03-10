# Instructor Guide – Lab 13: Criando Tabela e Operações CRUD
> Uso interno do instrutor

---

## Abertura do Lab

Bem-vindos ao DynamoDB na prática. Nas aulas teóricas você viu que DynamoDB é um banco NoSQL key-value + document, totalmente gerenciado, com latência de milissegundos. Agora vamos criar uma tabela de verdade usando o padrão **Composite Primary Key** — PK + SK — e executar as quatro operações CRUD. Presta atenção na modelagem: aqui não existe schema fixo, e essa liberdade é ao mesmo tempo o poder e o perigo do DynamoDB. O design que vamos usar nesse lab é baseado em um caso real de e-commerce.

---

## Comentários por Parte

### Parte 1 — Criar Tabela via Console

**Referência teórica:** Aula 38 – Conceitos NoSQL e DynamoDB + Aula 39 – Partition Keys e Sort Keys.

- Ao configurar `PK` (String) + `SK` (String), conecte com a Aula 39: *"esse par PK+SK é a Composite Primary Key. Nenhum dois itens podem ter a mesma combinação dos dois — mas o mesmo PK pode aparecer em vários itens desde que o SK seja diferente."*
- Ao escolher **On-demand**, diga: *"aqui não precisamos estimar capacidade antecipadamente. A AWS escala automaticamente. Para desenvolvimento e labs, é perfeito. Em produção você avalia se Provisioned com Auto Scaling seria mais econômico para cargas previsíveis."*
- Mostre o status `ACTIVE` antes de prosseguir — acostumar o aluno a verificar o estado do recurso antes de usar.

---

### Parte 2 — CRUD com Python (boto3)

**Referência teórica:** Aula 39 – Design de tabelas com padrão single-table.

- Ao mostrar o item `PK: 'USER#001', SK: 'PROFILE'` junto com `PK: 'USER#001', SK: 'ORDER#2024-001'`, pause e destaque: *"olha o que estamos fazendo: um usuário e seus pedidos na MESMA tabela. PK é o identificador do usuário, SK diferencia o tipo de entidade. Isso é o padrão single-table design que o DynamoDB incentiva."*
- No `PutItem`, mencione a ausência de schema: *"não declarei nenhum campo 'name' ou 'email' na criação da tabela — e mesmo assim está funcionando. No DynamoDB, cada item pode ter atributos completamente diferentes."*
- No `UpdateItem`, mostre o `UpdateExpression` e explique: *"DynamoDB tem sua própria mini-linguagem para updates. `SET` adiciona ou modifica, `REMOVE` exclui atributo, `ADD` soma números. Isso cai no exame."*
- No `DeleteItem` com `ConditionExpression`, diga: *"operação condicional — só deleta se o status for 'pending'. Isso garante consistência sem precisar fazer um get antes. Atômico, eficiente."*

---

### Parte 3 — Verificação via AWS CLI

- Mostre o `describe-table` e aponte o `TableStatus: ACTIVE` e o `BillingMode: PAY_PER_REQUEST`.
- Faça um `scan` rápido pelo console para mostrar os itens inseridos visualmente. O console do DynamoDB é ótimo para inspeção visual.

---

## Encerramento do Lab

Você acabou de criar a espinha dorsal de um sistema de e-commerce no DynamoDB — usuários e pedidos na mesma tabela, usando PK+SK para organizar tudo. Esse padrão single-table é o que engenheiros sêniors AWS usam em produção. Mas agora surge um problema: e se eu precisar buscar todos os pedidos por status, sem saber o userID? O `scan` resolveria, mas é lento e caro. No próximo lab, a solução elegante: Global Secondary Indexes.
