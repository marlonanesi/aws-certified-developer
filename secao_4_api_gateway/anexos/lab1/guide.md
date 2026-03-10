# Instructor Guide – Lab 09: REST API integrada com Lambda
> Uso interno do instrutor

---

## Abertura do Lab

Chegamos no momento em que a teoria encontra a prática! Você acabou de ver na teoria que o API Gateway é a "porta de entrada" da aplicação e que a integração Lambda Proxy é a mais usada no mundo real. Agora vamos criar isso do zero: uma função Lambda respondendo via HTTP, como se fosse uma API de verdade em produção. Presta atenção em cada etapa porque você vai perceber como é simples e poderoso ao mesmo tempo. Vamos lá?

---

## Comentários por Parte

### Parte 1 — Criar a Função Lambda

**Referência teórica:** Aula 29 – Integrações Lambda, HTTP e Mock.

- Ao criar a função, destaque que estamos usando **Python 3.12** e uma role básica — sem privilégios desnecessários. Boa prática de segurança desde o início.
- Quando mostrar o código, pause no objeto de retorno com `statusCode`, `headers` e `body`. Diga: *"esse formato é obrigatório na Lambda Proxy Integration — é o contrato entre a Lambda e o API Gateway. Sem ele, a API retorna 502."*
- Ao testar direto na Lambda com o payload simulando uma requisição GET, aproveite para mostrar como o evento completo chega: method, path, queryStringParameters. É o "pacote completo" que a Aula 29 descreveu.

---

### Parte 2 — Criar a API REST no Console

**Referência teórica:** Aula 27 – Visão Geral do API Gateway + Aula 29 – Integração Lambda.

- Ao criar o recurso `/hello`, comente: *"no mundo real, aqui seria /orders, /users, /products — qualquer endpoint do seu domínio."*
- Na hora de marcar **Use Lambda Proxy Integration**, reforce: *"essa caixinha determina se o API Gateway vai passar tudo para a Lambda ou se vai filtrar. Proxy = tudo passa. É a opção recomendada para quem está começando e para a maioria dos casos."*
- Mostre o popup de permissão que o console cria automaticamente (resource-based policy) — conecta com o que foi dito sobre o serviço ser gerenciado.

---

### Parte 3 — Deploy e Teste

**Referência teórica:** Aula 31 – Stages e Deployments.

- Antes de clicar em Deploy, pergunte para a câmera: *"o que acontece se eu testar a URL antes de fazer o deploy?"* — antecipa o conceito da Aula 31 de que mudanças não ficam visíveis automaticamente.
- Após o deploy, mostre a URL com o stage no path: `.../dev/hello`. Reconnecte com a Aula 31: *"esse 'dev' no path é o nome do nosso stage."*
- Execute o `curl` com e sem o `?name=...` para mostrar o comportamento da query string — o aluno vê a Lambda processando dados reais.

---

### Parte 4 — Testando com Postman (opcional)

- Se usar Postman, mostre os headers de resposta, especialmente o `X-Custom-Header` que colocamos no código. Reforça que a Lambda controla headers da resposta.
- Abra o CloudWatch imediatamente após para mostrar o log do `print("Event:", ...)`. Liga monitoramento à prática desde o lab 1.

---

## Encerramento do Lab

Parabéns — você acabou de criar sua primeira API real na AWS! Uma requisição HTTP saiu do seu terminal, passou pelo API Gateway, acionou uma função serverless, e uma resposta JSON voltou em milissegundos — sem um servidor para gerenciar. Isso é exatamente o que o exame AWS Developer Associate espera que você entenda e, mais importante, é o padrão que você vai encontrar em projetos reais. No próximo lab, vamos evoluir isso criando ambientes separados de dev e prod com Stage Variables.
