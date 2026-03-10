"""
Aula prática - AWS SDK (Boto3)
Demonstração de operações com S3 usando alto nível (Resource) e baixo nível (Client)
"""

import os
from dotenv import load_dotenv
import boto3

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Obtém as credenciais do arquivo .env
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')  # Região padrão


def listar_buckets_alto_nivel():
    """
    Método de ALTO NÍVEL - Resource API
    - Mais pythônico e orientado a objetos
    - Abstrações de alto nível sobre os recursos da AWS
    - Mais fácil de usar para operações comuns
    """
    print("\n" + "="*60)
    print("MÉTODO ALTO NÍVEL - Resource API (s3.Bucket)")
    print("="*60)
    
    # Cria uma sessão do boto3
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )
    
    # Cria o recurso S3 (alto nível)
    s3_resource = session.resource('s3')
    
    # Lista todos os buckets
    print("\nBuckets encontrados:")
    print("-" * 60)
    
    bucket_count = 0
    for bucket in s3_resource.buckets.all():
        bucket_count += 1
        print(f"{bucket_count}. Nome: {bucket.name}")
        print(f"   Criado em: {bucket.creation_date}")
        print()
    
    if bucket_count == 0:
        print("Nenhum bucket encontrado.")
    else:
        print(f"\nTotal de buckets: {bucket_count}")


def listar_buckets_baixo_nivel():
    """
    Método de BAIXO NÍVEL - Client API
    - Mapeamento 1:1 com as APIs HTTP da AWS
    - Mais controle e acesso a todas as operações da API
    - Retorna dicionários Python com as respostas da API
    """
    print("\n" + "="*60)
    print("MÉTODO BAIXO NÍVEL - Client API (s3.list_buckets)")
    print("="*60)
    
    # Cria uma sessão do boto3
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )
    
    # Cria o cliente S3 (baixo nível)
    s3_client = session.client('s3')
    
    # Lista todos os buckets usando o método list_buckets()
    response = s3_client.list_buckets()
    
    # A resposta é um dicionário Python
    print("\nEstrutura da resposta (baixo nível):")
    print(f"Tipo: {type(response)}")
    print(f"Chaves disponíveis: {list(response.keys())}")
    
    print("\nBuckets encontrados:")
    print("-" * 60)
    
    buckets = response.get('Buckets', [])
    
    if buckets:
        for idx, bucket in enumerate(buckets, 1):
            print(f"{idx}. Nome: {bucket['Name']}")
            print(f"   Criado em: {bucket['CreationDate']}")
            print()
        
        print(f"\nTotal de buckets: {len(buckets)}")
    else:
        print("Nenhum bucket encontrado.")
    
    # Informações adicionais do Owner (disponível na resposta)
    if 'Owner' in response:
        print("\nInformações do proprietário:")
        print(f"Display Name: {response['Owner'].get('DisplayName', 'N/A')}")
        print(f"ID: {response['Owner'].get('ID', 'N/A')}")


def comparacao_resource_vs_client():
    """
    Demonstra as diferenças entre Resource (alto nível) e Client (baixo nível)
    """
    print("\n" + "="*60)
    print("COMPARAÇÃO: Resource vs Client")
    print("="*60)
    
    print("""
    RESOURCE API (Alto Nível):
    ✓ Orientado a objetos
    ✓ Mais pythônico e intuitivo
    ✓ Abstrações que facilitam operações comuns
    ✓ Menos código para tarefas simples
    ✗ Nem todas as operações da AWS estão disponíveis
    
    CLIENT API (Baixo Nível):
    ✓ Acesso completo a todas as APIs da AWS
    ✓ Mapeamento 1:1 com as APIs HTTP
    ✓ Mais controle sobre as requisições
    ✓ Melhor para operações avançadas
    ✗ Mais verboso
    ✗ Trabalha com dicionários em vez de objetos
    
    RECOMENDAÇÃO:
    - Use Resource quando possível (mais simples)
    - Use Client quando precisar de operações específicas não disponíveis no Resource
    - Você pode usar ambos no mesmo projeto!
    """)


def main():
    """
    Função principal que executa as demonstrações
    """
    print("\n" + "="*60)
    print("AWS SDK - Boto3 - Demonstração S3")
    print("="*60)
    
    # Verifica se as credenciais foram carregadas
    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        print("\n⚠️  ATENÇÃO: Credenciais AWS não encontradas!")
        print("Configure o arquivo .env com suas credenciais:")
        print("  - AWS_ACCESS_KEY_ID=sua_access_key")
        print("  - AWS_SECRET_ACCESS_KEY=sua_secret_key")
        print("  - AWS_REGION=us-east-1 (opcional)")
        return
    
    print(f"\n✓ Credenciais carregadas com sucesso!")
    print(f"✓ Região: {AWS_REGION}")
    
    try:
        # Demonstração 1: Alto Nível (Resource)
        listar_buckets_alto_nivel()
        
        # Demonstração 2: Baixo Nível (Client)
        listar_buckets_baixo_nivel()
        
        # Comparação entre os dois métodos
        comparacao_resource_vs_client()
        
    except Exception as e:
        print(f"\n❌ Erro ao executar operações: {str(e)}")
        print("\nVerifique:")
        print("1. Se as credenciais estão corretas")
        print("2. Se o usuário IAM tem permissões de S3")
        print("3. Se a conexão com a AWS está funcionando")


if __name__ == "__main__":
    main()
