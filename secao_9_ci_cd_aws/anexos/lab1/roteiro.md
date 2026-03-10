# Roteiro — Lab 1: AWS CodeCommit — Repositório e Primeiro Commit

> **Compatibilidade de comandos**
> A maior parte dos comandos deste roteiro são `git` e `aws` sem variáveis — funcionam diretamente em **Bash e PowerShell**.
> Os poucos blocos que usam variáveis ou redirecionamentos de arquivo indicam o terminal alvo:
> - Linux / macOS / Git Bash → bloco `bash`
> - Windows PowerShell → bloco `powershell`

## Custos e Free Tier

| Serviço | Free Tier |
|---------|-----------|
| CodeCommit | 5 usuários ativos/mês + 50 GB storage + 10.000 req Git/mês |

> **Aviso:** Recursos na nuvem podem gerar custos mesmo dentro do Free Tier, pois ele tem limites mensais e pode ser esgotado. Ao finalizar a prática, **desprovisione todos os recursos** que não forem necessários para os labs seguintes.

> **Nota:** O repositório `demo-dva-pipeline` criado neste lab é reutilizado nos Labs 2, 3 e 4. Mantenha-o ativo durante toda a seção e exclua apenas ao final.

---
## Objetivo

Criar um repositório CodeCommit, configurar autenticação HTTPS com credenciais Git IAM, clonar localmente e realizar o primeiro commit e push.

---
## Parte 1 — Criar o Repositório

Console AWS → **CodeCommit** → **Create repository** ("Criar repositório"):

| Campo | Valor |
|---|---|
| Repository name | `demo-dva-pipeline` |
| Description | `Repositório demo para curso Preparatorio da certificacao AWS Developer Associate DVA` |

Anote a **URL HTTPS** do repositório — usada para clonar. 

---
## Parte 2 — Criar Credenciais Git IAM (HTTPS)

IAM → **Users** → selecione seu usuário → aba **Security credentials**:

1. Role até **HTTPS Git credentials for AWS CodeCommit**
2. Clique em **Generate credentials**
3. **Salve o usuário e a senha imediatamente** — a senha não pode ser visualizada novamente

> Essas credenciais são independentes da senha do console AWS. São usadas exclusivamente para autenticação Git via HTTPS com o CodeCommit — ponto recorrente no exame DVA.

---
## Parte 3 — Clonar o Repositório

```

git clone (aws codecommit get-repository --repository-name demo-dva-pipeline --query "repositoryMetadata.cloneUrlHttp" --output text)

```

Quando solicitado, use as **credenciais Git IAM** da Parte 2.

---
## Parte 4 — Criar Arquivos e Primeiro Commit

Copie os arquivos `app.py` e `buildspec.yml` desta pasta para o diretório do repositório clonado, ou crie-os diretamente:

```
# Configure identidade Git (necessário na primeira vez)
git config user.email "seu@email.com"
git config user.name "Seu Nome"

git add .
git commit -m "feat: initial commit - add app.py and buildspec"
git push
```

---
## Parte 5 — Verificar no Console

CodeCommit → repositório `demo-dva-pipeline`:
- Aba **Code**: arquivos commitados visíveis
- Aba **Commits**: histórico de commits
- Aba **Branches**: branch `main` criada automaticamente no primeiro push

---
## Parte 6 — Criar Branch e Pull Request (opcional)

```
git checkout -b feature/add-readme
```

Crie o arquivo `README.md`:

**Bash:**
```bash
cat > README.md << 'EOF'
# Demo Pipeline DVA-C02

Repositório de demonstração para o curso AWS Developer Associate.
EOF
```

**PowerShell:**
```powershell
@"
# Demo Pipeline DVA-C02

Repositório de demonstração para o curso AWS Developer Associate.
"@ | Set-Content README.md
```

Em seguida, em ambos os terminais:
```
git add README.md
git commit -m "docs: add README"
git push -u origin feature/add-readme
```

No console CodeCommit: **Pull requests** → **Create pull request** → Source: `feature/add-readme` → Destination: `main`. Observe o processo de review e merge.

---
## Pontos de Atenção

- Credenciais Git IAM ≠ senha do console AWS — são geradas separadamente em *Security credentials*
- Roles IAM **não funcionam** para autenticação Git HTTPS no CodeCommit — apenas credenciais Git IAM ou SSH key
- Token de autenticação expira periodicamente — gere novamente se necessário
- Git Credential Manager (Windows/macOS) pode cachear as credenciais automaticamente

---
## Limpeza

> **Mantenha o repositório durante toda a seção 9** — ele é reutilizado nos Labs 2, 3 e 4.

Para excluir ao final da seção completa:
```
aws codecommit delete-repository --repository-name demo-dva-pipeline
```
