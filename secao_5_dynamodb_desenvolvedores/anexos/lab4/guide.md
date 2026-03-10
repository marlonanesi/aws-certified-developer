# Instructor Guide – Lab 16: DynamoDB Streams integrado com Lambda
> Uso interno do instrutor

---

## Abertura do Lab

Aqui chegamos no padrão de arquitetura event-driven com DynamoDB. Pensa no caso de uso clássico: um pedido muda de status para "shipped" e automaticamente um e-mail de confirmação é disparado, um log de auditoria é criado, e um sistema de analytics é notificado — tudo isso sem que a aplicação principal saiba. É o CDC: Change Data Capture. A Aula 47 explicou o conceito de Streams. Agora vamos ativar isso numa tabela real e ver a Lambda disparando em tempo real para cada mudança.

---

## Comentários por Parte

### Parte 1 — Criar Tabela com Stream Habilitado

**Referência teórica:** Aula 47 – DynamoDB Streams e CDC, View Types.

- Ao criar a tabela via CLI com `StreamViewType=NEW_AND_OLD_IMAGES`, pause e explique os 4 tipos: *"KEYS_ONLY = só as chaves do item. NEW_IMAGE = como ficou depois. OLD_IMAGE = como estava antes. NEW_AND_OLD_IMAGES = os dois. Escolhemos o mais completo porque no lab queremos ver toda a informação da mudança."*
- Contextualize o caso de uso: *"auditoria, por exemplo, precisa do OLD_IMAGE para saber o que mudou. Uma notificação de envio precisa só do NEW_IMAGE."*
- Ao obter o Stream ARN, diga: *"esse ARN identifica exclusivamente o stream desta tabela. É o que conectamos ao trigger da Lambda."*

---

### Parte 2 — Criar a Função Lambda

**Referência teórica:** Aula 47 – Lambda como consumidor do Stream.

- Ao criar a IAM Role com `AWSLambdaDynamoDBExecutionRole`, foque: *"essa policy dá à Lambda permissão para ler do stream — DescribeStream, GetRecords, GetShardIterator, ListStreams. Sem ela, a Lambda nem consegue fazer polling no stream."*
- Ao mostrar o código da Lambda, explique a estrutura do evento: *"cada invocação pode conter múltiplos Records. Cada Record tem `eventName` — INSERT, MODIFY, REMOVE — e as imagens do item. É aí que você implementa sua lógica de negócio."*
- Destaque o `eventName` no loop: *"aqui você bifurca seu processamento: INSERT dispara boas-vindas, MODIFY verifica se status mudou para 'shipped', REMOVE dispara limpeza. Tudo event-driven, tudo desacoplado."*

---

### Parte 3 — Configurar o Event Source Mapping

**Referência teórica:** Aula 47 – polling gerenciado, shard iterator, batch size.

- Ao criar o trigger com `BatchSize=5` e `StartingPosition=TRIM_HORIZON`: *"TRIM_HORIZON = começa a processar desde o início do stream. LATEST = só eventos a partir de agora. Para produção, geralmente LATEST. Para recuperação de dados, TRIM_HORIZON."*
- Explique o polling: *"a Lambda não fica esperando o DynamoDB chamar ela. É ao contrário: a Lambda faz polling no stream periodicamente — esse processo é gerenciado automaticamente pelo event source mapping. Você não paga pelo polling, só pela execução."*
- Mencione o `BisectBatchOnFunctionError`: *"se a Lambda falhar, o DynamoDB vai dividir o batch ao meio e tentar de novo. Isso evita que um item problemático bloqueie o stream para sempre — é o mecanismo de retry inteligente."*

---

### Parte 4 — Disparar Eventos e Observar

- Execute INSERT, UPDATE e DELETE na tabela e mostre os logs no CloudWatch em tempo real. A latência costuma ser de segundos — é impactante para o aluno ver o log aparecer quase imediatamente.
- Abra o log de um MODIFY e destaque o `OldImage` vs `NewImage`: *"é exatamente aqui que você implementaria: 'o status mudou de pending para shipped? Então dispara o e-mail de envio.' Sem precisar que a aplicação principal saiba disso."*
- Se der tempo, mostre as métricas do Event Source Mapping no Lambda: `IteratorAge` é especialmente importante — indica o atraso entre o evento acontecer e a Lambda processar. Em sistemas saudáveis, deve ser próximo de zero.

---

## Encerramento do Lab

Seção 5 completa! Você foi de criar uma tabela básica com CRUD até implementar um pipeline de eventos em tempo real com DynamoDB Streams e Lambda — o coração das arquiteturas event-driven modernas na AWS. Dominar DynamoDB não é só saber o que é PK e SK: é entender quando usar GSI ao invés de Scan, por que o design da tabela deve seguir os padrões de acesso, e como Streams transforma um banco de dados em uma fonte de eventos. Isso é o que separa um desenvolvedor AWS júnior de um sênior. Parabéns pela seção, e vejo você na próxima!
