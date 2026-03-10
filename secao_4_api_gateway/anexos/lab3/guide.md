# Instructor Guide – Lab 11: Mapping Templates e Transformações com VTL
> Uso interno do instrutor

---

## Abertura do Lab

Aqui o bicho complica — no bom sentido. A Aula 33 apresentou um cenário: o cliente fala um formato, o backend fala outro, e o API Gateway resolve isso no meio sem tocar em nenhum dos dois. Agora você vai ver isso acontecendo ao vivo com VTL. É o lab mais técnico da seção, mas também o que mais abre a cabeça para o poder real do API Gateway. Uma observação importante antes de começar: desta vez vamos usar **Custom Integration** — não Proxy. Essa diferença vai ficar cristalina durante o lab.

---

## Comentários por Parte

### Parte 1 — Criar a Lambda sem Proxy

**Referência teórica:** Aula 29 – Comparação Lambda Proxy vs Custom Integration + Aula 33 – Transformações.

- Ao apresentar o código da `api-gateway-lab11-transform`, destaque: *"perceba que esse código não tem nenhum `event.get('httpMethod')` ou `event.get('path')`. Por quê? Porque não é Proxy — a Lambda só vai receber o que o mapping template definir. Nada mais."*
- Esse é o momento de reforçar: Custom Integration = você é responsável pelo contrato do evento.

---

### Parte 2 — Adicionar o Recurso `/transform`

**Referência teórica:** Aula 27 – Fluxo de requisição no API Gateway.

- Ao criar o método GET **sem** marcar Lambda Proxy, pausar e perguntar: *"o que muda quando desmarcamos isso?"* A resposta que você quer ouvir: o API Gateway não passa mais o envelope completo — agora é você quem define o que chega na Lambda via mapping template.

---

### Parte 3 — Integration Request com VTL

**Referência teórica:** Aula 33 – Mapping Templates, variáveis `$input` e Passthrough Behavior.

- Ao digitar o template VTL ao vivo, leia cada linha: *"`$input.params('firstName')` — aqui estamos pegando o parâmetro da query string chamado 'firstName'. Simples. O `$input` é uma das 4 variáveis principais do VTL."*
- Explique o `#set()` como "criar uma variável local no template" — analogia com `let` em JavaScript ou qualquer linguagem que o aluno conheça.
- Ao configurar o **Passthrough Behavior**, escolha `WHEN_NO_MATCH` e explique: *"se chegar um Content-Type que não mapeei, passa sem transformação. Se eu colocasse NEVER, retornaria 415. Use NEVER quando quiser máximo controle."*

---

### Parte 4 — Integration Response com VTL

**Referência teórica:** Aula 33 – Transformações na resposta, envelope de sucesso.

- Ao criar o template de resposta que adiciona `"status": "success"` e `"timestamp"`, diga: *"isso é padronização de API. Toda resposta sai no mesmo formato, independentemente do que a Lambda retornou. O cliente nunca precisa saber como o backend é organizado por dentro."*
- Compare ao vivo: chame com Proxy Integration (Lab 09) e veja a resposta crua vs. agora com o envelope. O contraste visual é pedagógico.

---

## Encerramento do Lab

VTL não é a linguagem mais elegante do mundo, mas o conceito que ela representa é fundamental: transformação de dados na borda, sem tocar no backend. No exame, você não vai precisar escrever VTL — mas vai precisar saber quando usar Custom Integration vs Proxy e entender o que `NEVER`, `WHEN_NO_MATCH` e `WHEN_NO_TEMPLATES` fazem. Esses três você acabou de ver na prática. No próximo e último lab desta seção, fechamos com controle de acesso por cliente usando API Keys e Usage Plans.
