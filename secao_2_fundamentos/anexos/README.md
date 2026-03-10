# Aula Prática - AWS SDK (Boto3)

## 📋 Objetivo
Demonstrar o uso do SDK da AWS (Boto3) em Python para listar buckets S3 usando:
- **Alto Nível (Resource API)**: Orientado a objetos
- **Baixo Nível (Client API)**: Acesso direto às APIs da AWS

## 🛠️ Passo a Passo

### 1️⃣ Instalar as dependências
```bash
pip install -r requirements.txt
```

### 2️⃣ Configurar o arquivo .env
Abra o arquivo `.env` e preencha com suas credenciais AWS:

```env
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
```

**Como obter suas credenciais:**
1. Faça login no Console AWS
2. Acesse IAM → Usuários
3. Selecione seu usuário
4. Vá em "Credenciais de segurança"
5. Clique em "Criar chave de acesso"
6. Copie o Access Key ID e Secret Access Key

⚠️ **IMPORTANTE:** 
- Mantenha suas credenciais em segurança
- Nunca compartilhe ou faça commit do arquivo `.env`
- Use permissões mínimas necessárias (princípio do menor privilégio)

### 3️⃣ Executar o script
```bash
python aula_sdk_aws.py
```

## 📚 O que o script faz

O script demonstra duas formas de usar o Boto3:

### Resource API (Alto Nível)
```python
s3_resource = boto3.resource('s3')
for bucket in s3_resource.buckets.all():
    print(bucket.name)
```
✅ Mais simples e pythônico

### Client API (Baixo Nível)
```python
s3_client = boto3.client('s3')
response = s3_client.list_buckets()
```
✅ Acesso completo a todas as operações da AWS
```

## 📖 Referências
- [Documentação Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Guia IAM AWS](https://docs.aws.amazon.com/IAM/latest/UserGuide/)
