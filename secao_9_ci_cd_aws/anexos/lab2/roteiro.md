# Roteiro — Lab 2: AWS CodeBuild — Projeto de Build e Cache

> **Compatibilidade de comandos**
> Todos os comandos deste roteiro (`aws`, `git`, `echo`) funcionam diretamente em **Bash e PowerShell** sem adapta\u00e7\u00e3o \u2014 copie e cole no terminal de sua prefer\u00eancia.

## Custos e Free Tier

| Serviço | Free Tier |
|---------|-----------|
| CodeBuild | 100 minutos de build/mês com `build.general1.small` (primeiros 12 meses) |
| S3 | 5 GB storage + 20k GET + 2k PUT (primeiros 12 meses) |
| CloudWatch Logs | 5 GB de ingestão/mês (primeiros 12 meses) |

> **Aviso:** Recursos na nuvem podem gerar custos mesmo dentro do Free Tier, pois ele tem limites mensais e pode ser esgotado. Builds que ficam em loop ou projetos com webhooks ativos que disparam builds frequentes consomem os minutos rapidamente. Ao finalizar, **desabilite webhooks** e mantenha apenas o necessário para os labs seguintes.

---
## Pré-requisito

Lab 1 concluído — repositório `demo-dva-pipeline` com `buildspec.yml` no branch `main`.

---
## Objetivo

Criar um projeto CodeBuild conectado ao CodeCommit, executar um build, visualizar logs por fase e configurar cache de dependências.

---
## Parte 1 — Atualizar o buildspec.yml no Repositório

Substitua o conteúdo do `buildspec.yml` do repositório pelo arquivo desta pasta (versão completa com todas as fases e cache):

```
cd demo-dva-pipeline
# copie o buildspec.yml desta pasta para o repositório
git add buildspec.yml
git commit -m "build: update buildspec with all phases and cache"
git push
```

> **Branch:** o repositório usa `master` por padrão (criado via console do CodeCommit). Confirme com `git branch` antes de fazer push.

---
## Parte 1.5 — Criar o Bucket S3 para Artefatos

O CodeBuild **não cria o bucket automaticamente** — ele precisa existir antes de salvar o projeto.

Nomes de bucket S3 são **globalmente únicos** em toda a AWS. Por convenção, use o Account ID como sufixo para garantir unicidade sem depender de um sufixo aleatório:

```bash
# Descobrir seu Account ID
aws sts get-caller-identity --query Account --output text

# Criar o bucket (substitua <account-id> pelo valor retornado acima)
aws s3 mb s3://codebuild-artifacts-<ACCOUNT_ID> --region sa-east-1
```

> **Por que esse nome?** `codebuild-artifacts-<account-id>` é descritivo (identifica a finalidade), usa o Account ID como sufixo único e segue o padrão recomendado pela AWS para buckets internos. Anote o nome exato — ele será referenciado na configuração de Artefatos e de Cache.

---
## Parte 2 — Criar o Projeto CodeBuild

Console AWS → **CodeBuild** → **Create build project** ("Criar projeto de compilação"):

**Project configuration:**

| Campo | Valor |
|---|---|
| Project name | `demo-dva-build` |

**Source:**

| Campo | Valor |
|---|---|
| Source provider | AWS CodeCommit |
| Repository | `demo-dva-pipeline` |
| Branch | `master` |

**Ambiente** (campos na ordem que aparecem no console PT-BR):

| Campo no console | Valor a selecionar |
|---|---|
| **Modo de provisionamento** | **Sob demanda** ← padrão; "Reservada" é para frotas pré-alocadas (custo fixo) |
| **Imagem do ambiente** | **Imagem gerenciada** ← AWS mantém; "Personalizada" seria uma imagem Docker própria |
| **Computação** | **EC2** ← executa em instâncias EC2; "Lambda" tem execução mais rápida mas limites de tempo/memória menores |
| **Tamanho da computação** | **3 GB de memória, 2 vCPUs** ← menor opção, suficiente para este lab e inclusa no Free Tier |
| **Modo de execução** | **Contêiner** ← isolamento via Docker por build; "Instância" usa a VM inteira (mais lento para provisionar) |
| **Sistema operacional** | **Amazon Linux** |
| **Tempo de execução** | **Standard** |
| **Imagem** | `aws/codebuild/amazonlinux-x86_64-standard:corretto21` (ou a versão mais recente listada) |
| **Versão da imagem** | Usar sempre a versão de imagem mais recente para esse tempo de execução |
| **Função de serviço** | **Nova função de serviço** ← o console gera automaticamente com as permissões básicas |

> **Função de serviço:** Anote o nome gerado (ex.: `codebuild-demo-dva-build-service-role`). Nas partes seguintes do lab, pode ser necessário adicionar permissões extras (SSM, S3) diretamente nessa role via IAM.

**Buildspec** (aba separada no console):

| Campo no console | Valor |
|---|---|
| **Especificação de compilação** | Marcar **"Usar um arquivo buildspec"** ← lê o `buildspec.yml` da raiz do repositório automaticamente |

> Não preencha o nome do arquivo — o padrão `buildspec.yml` na raiz do repositório é detectado automaticamente. Só altere se o arquivo tiver outro nome ou caminho.

**Artefatos** (Artifacts):

| Campo no console | Valor |
|---|---|
| **Tipo** | Amazon S3 |
| **Nome do bucket** | `codebuild-artifacts-<account-id>` ← bucket criado na Parte 1.5 |
| **Nome** | `demo-build-artifact` ← nome do arquivo gerado dentro do bucket |
| **Empacotamento** | **Zip** ← o CodeBuild empacota os artefatos em `demo-build-artifact.zip`; "Nenhum" subiria os arquivos individualmente |

**Logs** → CloudWatch logs: habilitado, group name: `/codebuild/demo-dva-build`.

> **Webhook (trigger por push):** o campo de webhook de Source **não aparece para CodeCommit** — ele só existe quando o provedor é GitHub ou Bitbucket. Para CodeCommit, o trigger automático é configurado via **Gatilhos do CodeCommit** ou **EventBridge** (Parte 7).

---
## Parte 3 — Executar o Primeiro Build

Projeto → **Start build** → **Start build** (configurações padrão).

Acompanhe as fases em tempo real:
`QUEUED → PROVISIONING → DOWNLOAD_SOURCE → INSTALL → PRE_BUILD → BUILD → POST_BUILD → UPLOAD_ARTIFACTS → FINALIZING`

Clique em cada fase para ver os logs detalhados e os comandos executados.

---
## Parte 4 — Verificar Artefato e Logs

**Artefato no S3:**
- S3 → bucket criado → arquivo `demo-build-artifact.zip`
- Faça download e verifique o conteúdo interno (`app.zip`)

**Logs no CloudWatch:**
- CloudWatch → Log groups → `/codebuild/demo-dva-build`
- Abra o log stream mais recente
- Observe as marcações de fase (`=== INSTALL PHASE ===`, etc.)

---
## Parte 5 — Variáveis Sensíveis via SSM Parameter Store (demonstração)

```
# Criar parâmetro de demonstração
aws ssm put-parameter --name "/myapp/api-key" --value "valor-secreto-demo" --type SecureString

# Para usar no buildspec, descomente a seção parameter-store no buildspec.yml
# e adicione a permissão ssm:GetParameters à service role do CodeBuild
```

---
## Parte 6 — Habilitar Cache S3

Projeto → **Edit** → **Artifacts** → Cache:
- Type: S3
- Location: mesmo bucket, path `cache/`

Execute um segundo build e compare o tempo — a fase `INSTALL` deve ser mais rápida pela reutilização do cache pip.

---
## Parte 7 — Trigger Automático por Push (EventBridge)

Como o provedor é **CodeCommit**, não há opção de webhook na aba Source do CodeBuild. O caminho correto é criar uma **regra no EventBridge**.

> **Atenção — o botão "Criar trigger" dentro do CodeBuild** (CodeBuild → projeto → Criar trigger) serve apenas para **cronogramas** (cron ou período regular), não para disparo por push. Ignore essa opção para este objetivo. Os **Gatilhos do CodeCommit** (repositório → Settings → Triggers) também não servem aqui — eles suportam apenas SNS e Lambda como destino, não CodeBuild diretamente.

**Pelo console do EventBridge:**
1. Console → **Amazon EventBridge** → **Regras** → **Criar regra**
2. Nome: `codebuild-trigger-demo-dva` → Próximo
3. **Fonte do evento:** Eventos da AWS ou de parceiros do EventBridge
4. **Método de criação:** selecione **Padrão personalizado (editor JSON)**
   - O formulário padrão não expõe os filtros de branch — é necessário usar o JSON
5. Cole o padrão abaixo no editor JSON (substitua `<account-id>`):
```json
{
  "source": ["aws.codecommit"],
  "detail-type": ["CodeCommit Repository State Change"],
  "resources": ["arn:aws:codecommit:sa-east-1:<account-id>:demo-dva-pipeline"],
  "detail": {
    "event": ["referenceUpdated"],
    "referenceType": ["branch"],
    "referenceName": ["master"]
  }
}
```
6. Próximo → **Destino:** AWS CodeBuild → selecione o projeto `demo-dva-build`
7. Função de execução: **Criar uma nova função** (EventBridge cria automaticamente com `codebuild:StartBuild`)
8. Próximo → Criar regra

> **Não há delay.** Se o build não aparecer em 10–15 segundos após o push, use o checklist abaixo.

**Checklist de diagnóstico se o build não disparar:**
- [ ] A regra do EventBridge está com status **Habilitada** (em inglês: *Enabled*)?
- [ ] O nome do repositório no filtro bate exatamente com `demo-dva-pipeline`?
- [ ] O push foi para a branch `master` (confirme com `git branch`)
- [ ] A role da regra tem permissão `codebuild:StartBuild`? (IAM → role criada pelo EventBridge)
- [ ] Verifique **EventBridge → Regras → `codebuild-trigger-demo-dva` → Monitoramento** para ver se o evento foi recebido mas o destino falhou

Teste após configurar a regra:
```bash
echo "# trigger test" >> README.md
git add README.md
git commit -m "test: trigger build via push"
git push
```

Volte ao CodeBuild e verifique o build disparado automaticamente. No console PT-BR o status aparece como **"Em andamento"** — isso confirma que o trigger funcionou corretamente.

---
## Pontos de Atenção

- `CODEBUILD_BUILD_SUCCEEDING=0` em `post_build` significa que uma fase anterior falhou — permite ações condicionais
- Variáveis de ambiente em texto puro ficam visíveis nos logs — use Parameter Store (`SecureString`) ou Secrets Manager para valores sensíveis
- Cache S3: só reduz tempo se o ambiente for recriado entre builds — o ambiente Managed é sempre novo
- Webhook ativo = cada push no repositório dispara um build — desabilite ao terminar o lab para não consumir minutos do Free Tier

---
## Limpeza

> **Mantenha o projeto `demo-dva-build`** — ele é reutilizado no Lab 4 (CodePipeline).

Para desabilitar webhook: Projeto → **Edit** → **Source** → desmarque webhook.

Para excluir ao final da seção:
```
aws codebuild delete-project --name demo-dva-build
aws s3 rb s3://codebuild-artifacts-<account-id> --force
```
