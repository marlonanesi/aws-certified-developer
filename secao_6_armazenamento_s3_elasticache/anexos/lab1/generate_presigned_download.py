import boto3
from botocore.exceptions import ClientError

BUCKET_NAME = "dva-lab1-s3-dva-presigned-<ACCOUNT_ID>"  # substitua <ACCOUNT_ID> pelo ID da sua conta AWS (12 dígitos)
OBJECT_KEY = "arquivo-teste.txt"

s3_client = boto3.client("s3")


def gerar_url_download(bucket: str, key: str, expiracao: int = 3600) -> str:
    """
    Gera uma presigned URL para download (GET) de um objeto no S3.

    Args:
        bucket: Nome do bucket S3
        key: Chave (caminho) do objeto no bucket
        expiracao: Tempo de expiração em segundos (padrão: 3600 = 1 hora)

    Returns:
        URL pré-assinada como string
    """
    try:
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expiracao,
        )
        return url
    except ClientError as e:
        print(f"Erro ao gerar URL: {e}")
        raise


if __name__ == "__main__":
    # 1. Gerar URL com expiração padrão de 1 hora
    print("=== URL de Download (1 hora) ===")
    url_1h = gerar_url_download(BUCKET_NAME, OBJECT_KEY, expiracao=3600)
    print(url_1h)
    print()

    # 2. Gerar URL com expiração curta para testar expiração
    print("=== URL de Download (10 segundos — para teste de expiração) ===")
    url_10s = gerar_url_download(BUCKET_NAME, OBJECT_KEY, expiracao=10)
    print(url_10s)
    print()
    print("Aguarde 10 segundos e tente acessar a URL acima para ver o erro de expiração.")
    print()

    # 3. Testar via requests (opcional)
    try:
        import requests
        print("=== Teste de download via requests (URL de 1h) ===")
        response = requests.get(url_1h)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Conteúdo: {response.text}")
        else:
            print(f"Erro: {response.text}")
    except ImportError:
        print("Biblioteca 'requests' não instalada. Execute: pip install requests")
