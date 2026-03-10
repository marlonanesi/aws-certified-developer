import boto3
from botocore.exceptions import ClientError

BUCKET_NAME = "dva-lab1-s3-dva-presigned-<ACCOUNT_ID>"  # substitua <ACCOUNT_ID> pelo ID da sua conta AWS (12 dígitos)
OBJECT_KEY = "upload-via-put.txt"
CONTENT = b"Conteudo enviado via presigned URL PUT"

s3_client = boto3.client("s3")


def gerar_url_upload_put(bucket: str, key: str, expiracao: int = 3600) -> str:
    """
    Gera uma presigned URL para upload (PUT) de um objeto no S3.

    Args:
        bucket: Nome do bucket S3
        key: Chave de destino do objeto
        expiracao: Tempo de expiração em segundos (padrão: 3600 = 1 hora)

    Returns:
        URL pré-assinada como string
    """
    try:
        url = s3_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": bucket, "Key": key, "ContentType": "text/plain"},
            ExpiresIn=expiracao,
        )
        return url
    except ClientError as e:
        print(f"Erro ao gerar URL: {e}")
        raise


def fazer_upload_com_url(url: str, content: bytes) -> None:
    """
    Simula o comportamento de um cliente (ex: browser ou app mobile)
    fazendo upload direto ao S3 usando a presigned URL PUT.

    Args:
        url: Presigned URL gerada pelo backend
        content: Conteúdo em bytes a ser enviado
    """
    import requests

    headers = {"Content-Type": "text/plain"}
    response = requests.put(url, data=content, headers=headers)

    if response.status_code == 200:
        print("Upload realizado com sucesso!")
    else:
        print(f"Erro no upload: {response.status_code}")
        print(response.text)


if __name__ == "__main__":
    print("=== Gerando Presigned URL para Upload (PUT) ===")
    url = gerar_url_upload_put(BUCKET_NAME, OBJECT_KEY, expiracao=3600)
    print(f"URL gerada:\n{url}\n")

    print("=== Simulando upload do cliente ===")
    print("(Em produção, esta URL seria enviada ao app móvel ou browser)")
    try:
        fazer_upload_com_url(url, CONTENT)
        print(f"\nObjeto disponível em: s3://{BUCKET_NAME}/{OBJECT_KEY}")
    except ImportError:
        print("Biblioteca 'requests' não instalada. Execute: pip install requests")
        print("\nComando curl equivalente:")
        print(f'curl -X PUT -H "Content-Type: text/plain" --data "{CONTENT.decode()}" "{url}"')
