# Lab 1 — EC2: Instância, User Data e IMDS v2

> **Aviso de compatibilidade de comandos**
> Os comandos deste roteiro foram escritos para **PowerShell (Windows)**.
> Backtick `` ` `` é o caractere de continuação de linha no PowerShell.
> Variáveis usam a sintaxe `$VARIAVEL` ou `$env:VARIAVEL`.
>
> Para converter para Bash/Zsh (macOS/Linux), substitua `` ` `` por `\`
> e `$env:VAR` por `export VAR=valor`.
>
> Sugestão de prompt para IA generativa:
> "Converta o comando abaixo para meu SO [Windows/macOS/Linux] e terminal
> [PowerShell/Bash/Zsh]. Adapte variáveis, redirecionamentos e continuação
> de linha para o equivalente nesse ambiente: <cole o comando aqui>"

---

> **Custos e Free Tier**
> O Amazon EC2 oferece **750 horas/mês de t2.micro ou t3.micro** nos primeiros 12 meses (Free Tier).
> O AWS Systems Manager Session Manager é **gratuito** — não há custo de porta aberta nem key pair.
> O Amazon CloudWatch Logs inclui **5 GB de ingestão gratuita/mês** nos primeiros 12 meses.
>
> ⚠️ **Aviso importante:** instâncias EC2 no estado **Running** geram custo por hora.
> Ao finalizar o lab, encerre (terminate) a instância para evitar cobranças inesperadas.

---

## Objetivo

Lançar uma instância EC2 com User Data, conectar via Session Manager (sem SSH, sem key pair),
e consultar o Instance Metadata Service na versão segura (IMDSv2) para extrair
metadados e credenciais IAM temporárias diretamente da instância.

---

## Pré-requisitos

- Conta AWS com usuário IAM com permissões em: `EC2`, `IAM`, `SSM`
- AWS CLI instalada e configurada (`aws configure`)
- PowerShell com AWS CLI disponível no PATH

Verificar configuração:
```powershell
aws sts get-caller-identity
```

---

## Parte 1 — Criar a IAM Role para a Instância EC2

A instância precisa de uma IAM Role com a policy `AmazonSSMManagedInstanceCore`
para permitir acesso via Session Manager **sem precisar abrir porta SSH**.

### 1.1 — Criar a Role

Use o arquivo `iam-trust-policy.json` incluído nesta pasta:

```powershell
aws iam create-role `
  --role-name EC2-SSM-Lab-Role `
  --assume-role-policy-document file://iam-trust-policy.json
```

### 1.2 — Anexar a policy gerenciada

```powershell
aws iam attach-role-policy `
  --role-name EC2-SSM-Lab-Role `
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
```

### 1.3 — Criar o Instance Profile

```powershell
aws iam create-instance-profile `
  --instance-profile-name EC2-SSM-Lab-Profile

aws iam add-role-to-instance-profile `
  --instance-profile-name EC2-SSM-Lab-Profile `
  --role-name EC2-SSM-Lab-Role
```

> Aguarde 10–15 segundos antes de continuar para a propagação da role.

---

## Parte 2 — Criar o Security Group

A instância **não precisa de porta 22 aberta** (Session Manager elimina essa necessidade).
Criaremos um Security Group sem inbound rules.

```powershell
# Pegar o VPC padrão
$VPC_ID = aws ec2 describe-vpcs `
  --filters "Name=isDefault,Values=true" `
  --query "Vpcs[0].VpcId" `
  --output text

Write-Host "VPC padrão: $VPC_ID"

# Criar Security Group
$SG_ID = aws ec2 create-security-group `
  --group-name "lab-ec2-imds-sg" `
  --description "Lab EC2 IMDS - sem inbound" `
  --vpc-id $VPC_ID `
  --query "GroupId" `
  --output text

Write-Host "Security Group criado: $SG_ID"
```

---

## Parte 3 — Obter a AMI mais recente do Amazon Linux 2023

```powershell
$AMI_ID = aws ec2 describe-images `
  --owners amazon `
  --filters `
    "Name=name,Values=al2023-ami-*-x86_64" `
    "Name=state,Values=available" `
  --query "sort_by(Images, &CreationDate)[-1].ImageId" `
  --output text

Write-Host "AMI selecionada: $AMI_ID"
```

---

## Parte 4 — Lançar a Instância com User Data

O User Data (arquivo `user_data.sh`) instala e configura automaticamente
o agente SSM e o `jq` (para formatar JSON no terminal).

```powershell
$INSTANCE_ID = aws ec2 run-instances `
  --image-id $AMI_ID `
  --instance-type t3.micro `
  --iam-instance-profile Name=EC2-SSM-Lab-Profile `
  --security-group-ids $SG_ID `
  --user-data file://user_data.sh `
  --metadata-options "HttpTokens=required,HttpEndpoint=enabled" `
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=lab-ec2-imds}]" `
  --query "Instances[0].InstanceId" `
  --output text

Write-Host "Instância lançada: $INSTANCE_ID"
```

> **Atenção:** `HttpTokens=required` força o uso exclusivo de **IMDSv2** nesta instância.
> Qualquer tentativa de usar IMDSv1 (GET direto sem token) será rejeitada.

### Aguardar a instância estar pronta

```powershell
Write-Host "Aguardando instância inicializar..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID
Write-Host "Instância em estado Running!"

# Verificar status completo (running + checks OK)
aws ec2 describe-instance-status `
  --instance-ids $INSTANCE_ID `
  --query "InstanceStatuses[0].{Estado:InstanceState.Name,Check:InstanceStatus.Status}" `
  --output table
```

> Aguarde até ambos os status checks estarem `ok` antes de conectar (pode levar 2–3 minutos).

---

## Parte 5 — Conectar via Session Manager

**Opção A — Console AWS (recomendado para iniciantes):**

1. Console → **EC2 → Instances**
2. Selecione a instância `lab-ec2-imds`
3. Clique em **Connect** → aba **Session Manager** → **Connect**

**Opção B — AWS CLI (PowerShell):**

```powershell
aws ssm start-session --target $INSTANCE_ID
```

> Pré-requisito para Opção B: instale o **Session Manager Plugin** para AWS CLI.
> Download: https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html

---

## Parte 6 — Testar IMDS v2 dentro da Instância

Execute os comandos abaixo **dentro da sessão SSM** (o terminal que abriu na instância).
O shell dentro da instância é **bash**.

### 6.1 — Tentar IMDSv1 (deve falhar)

```bash
curl -s http://169.254.169.254/latest/meta-data/instance-id
```

**Resultado esperado:** sem resposta ou erro `401 Unauthorized`.
Isso confirma que IMDSv1 está bloqueado pela configuração `HttpTokens=required`.

### 6.2 — Obter token IMDSv2

```bash
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")

echo "Token obtido: ${TOKEN:0:20}..."
```

### 6.3 — Consultar metadados com o token

```bash
# Instance ID
INSTANCE_ID=$(curl -s \
  -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/instance-id)
echo "Instance ID: $INSTANCE_ID"

# Tipo da instância
INSTANCE_TYPE=$(curl -s \
  -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/instance-type)
echo "Tipo: $INSTANCE_TYPE"

# Região
AZ=$(curl -s \
  -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/placement/availability-zone)
echo "Zona de disponibilidade: $AZ"
REGION="${AZ%?}"
echo "Região: $REGION"

# IP privado
PRIVATE_IP=$(curl -s \
  -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/local-ipv4)
echo "IP privado: $PRIVATE_IP"

# IP público (pode estar vazio em subnets privadas)
PUBLIC_IP=$(curl -s \
  -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/public-ipv4)
echo "IP público: $PUBLIC_IP"

# AMI usada
AMI=$(curl -s \
  -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/ami-id)
echo "AMI: $AMI"
```

### 6.4 — Consultar credenciais IAM temporárias via IMDS

```bash
# Listar roles disponíveis na instância
ROLE_NAME=$(curl -s \
  -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/iam/security-credentials/)
echo "Role: $ROLE_NAME"

# Obter as credenciais temporárias da role
CREDS=$(curl -s \
  -H "X-aws-ec2-metadata-token: $TOKEN" \
  "http://169.254.169.254/latest/meta-data/iam/security-credentials/$ROLE_NAME")

# Visualizar formatado (requer jq instalado pelo user_data)
echo $CREDS | jq '{
  Type: .Type,
  AccessKeyId: .AccessKeyId,
  Expiracao: .Expiration,
  Token_primeiros_20: (.Token | .[0:20])
}'
```

> **Ponto-chave:** essas credenciais são **temporárias** — expiram e são rotacionadas automaticamente.
> O SDK da AWS usa exatamente essa API por baixo dos panos quando há uma IAM Role na instância.
> **Nunca coloque access keys hardcoded no código** — use IAM Role + IMDS.

### 6.5 — Listar todos os caminhos de metadados disponíveis

```bash
curl -s \
  -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/
```

### 6.6 — Identity Document (informações da instância em JSON)

```bash
curl -s \
  -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/dynamic/instance-identity/document | jq .
```

> O identity document contém: `instanceId`, `region`, `accountId`, `imageId`, `instanceType` e mais.
> É usado para validar que uma requisição vem de uma instância EC2 legítima.

---

## Parte 7 — Verificar o User Data executado

```bash
# Ver o script de user data que foi executado na inicialização
curl -s \
  -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/user-data

# Ver o log de execução do cloud-init (output do user data)
sudo cat /var/log/cloud-init-output.log | tail -30
```

---

## Parte 8 — Verificar Informações da Instância via CLI (de fora)

Saia da sessão SSM (`exit`) e execute no PowerShell local:

```powershell
# Visão geral da instância
aws ec2 describe-instances `
  --instance-ids $INSTANCE_ID `
  --query "Reservations[0].Instances[0].{
    ID:InstanceId,
    Tipo:InstanceType,
    Estado:State.Name,
    IP_Privado:PrivateIpAddress,
    IP_Publico:PublicIpAddress,
    AZ:Placement.AvailabilityZone,
    IAM_Profile:IamInstanceProfile.Arn
  }" `
  --output table
```

---

## Pontos de Verificação

- IMDSv1 sem token retorna `401 Unauthorized` quando `HttpTokens=required`
- O token IMDSv2 é obtido via `PUT` — SSRF não consegue forjar método PUT
- As credenciais IAM via IMDS têm campo `Expiration` — provando que são temporárias
- `USER_DATA` acessível em `/latest/user-data` — atenção: não coloque senhas no user data
- O agente SSM elimina a necessidade de porta 22 e key pair

---

## Limpeza

Execute no PowerShell **após sair da sessão SSM**:

```powershell
# 1. Terminar a instância
aws ec2 terminate-instances --instance-ids $INSTANCE_ID
Write-Host "Instância sendo encerrada..."

# 2. Aguardar encerramento completo
aws ec2 wait instance-terminated --instance-ids $INSTANCE_ID
Write-Host "Instância encerrada."

# 3. Remover Security Group (aguardar alguns segundos após terminate)
Start-Sleep -Seconds 10
aws ec2 delete-security-group --group-id $SG_ID
Write-Host "Security Group removido."

# 4. Remover Instance Profile e Role IAM
aws iam remove-role-from-instance-profile `
  --instance-profile-name EC2-SSM-Lab-Profile `
  --role-name EC2-SSM-Lab-Role

aws iam delete-instance-profile `
  --instance-profile-name EC2-SSM-Lab-Profile

aws iam detach-role-policy `
  --role-name EC2-SSM-Lab-Role `
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

aws iam delete-role --role-name EC2-SSM-Lab-Role

Write-Host "Limpeza concluída!"
```
