# Instructor Guide – Lab 10: Múltiplos Stages com Stage Variables
> Uso interno do instrutor

---

## Abertura do Lab

No lab anterior criamos uma API funcional. Mas no mundo real, ninguém joga diretamente no ambiente de produção — você tem dev, staging, prod. E a pergunta é: como a mesma API se comporta diferente em cada ambiente sem você duplicar código? A resposta está nas Stage Variables. O que você vai ver agora é um padrão que toda empresa que usa API Gateway aplica. Presta atenção porque isso conecta direto com gerenciamento de ambientes — tema que aparece tanto no exame quanto em entrevistas técnicas.

---

## Comentários por Parte

### Parte 1 — Criar Versões e Aliases da Lambda

**Referência teórica:** Aula 31 – Stages, Deployments e Stage Variables.

- Ao publicar a versão 1 da Lambda, conecte com o conceito de imutabilidade: *"uma versão publicada é congelada — o código nunca muda. Isso é o que garante estabilidade em produção."*
- Ao criar os aliases `dev` e `prod`, use a analogia da Aula 31: *"alias é como um ponteiro. Você pode mover o ponteiro para outra versão sem mudar o que o cliente chama."*
- Reforce: `$LATEST` sempre aponta para o código mais atual — nunca use `$LATEST` diretamente em prod.

---

### Parte 2 — Reconfigurar a Integração com Stage Variables

**Referência teórica:** Aula 31 – Stage Variables, sintaxe `${stageVariables.nome}`.

- Ao mostrar o ARN com `${stageVariables.lambdaAlias}`, leia em voz alta e devagar: *"no momento em que a requisição chegar, o API Gateway vai substituir essa variável pelo valor configurado naquele stage específico."*
- Destaque o popup de permissão que aparece ao salvar — é o CLI command para dar invoke permission para cada alias. Mostre que você precisaria rodar o comando para `dev` e `prod` separadamente. Conecta com a Aula 29 sobre resource-based policies.

---

### Parte 3 — Criar os Stages dev e prod

**Referência teórica:** Aula 31 – Stages com configurações independentes.

- Ao criar o stage `dev` e definir `lambdaAlias = dev`, diga: *"agora o URL .../dev/hello vai executar o alias dev da Lambda. Se eu mudar o código e quiser testar, publico um `$LATEST`, o alias dev já aponta para ele."*
- Ao criar o stage `prod` com `lambdaAlias = prod`, pergunte retoricamente: *"e se quiser fazer um hotfix em prod? Publico uma nova versão, aponto o alias prod para ela — sem alterar nada na configuração do API Gateway."*
- Faça o deploy dos dois stages e compare as URLs — URL diferente e comportamento diferente, mesma API.

---

### Parte 4 — Testar e Comparar Respostas

- Execute a mesma chamada nos dois endpoints e mostre o campo `stageAlias` na resposta variando entre `dev` e `prod`. É o momento mais visual do lab — aluno vê na prática o que a teoria descrevia.
- Se der tempo, mostre o Deployment History — conecta com o conceito de rollback da Aula 31.

---

## Encerramento do Lab

Com Stage Variables você acabou de implementar um padrão profissional de gerenciamento de ambientes: a mesma API, o mesmo código de configuração, comportamentos completamente separados por stage. Isso elimina o risco de acidentalmente testar código de dev em produção, e é exatamente como times de engenharia sérios operam. No próximo lab vamos dar um passo além e transformar dados dentro do próprio API Gateway antes mesmo de chegar na Lambda — os Mapping Templates com VTL.
