import boto3
from botocore.exceptions import ClientError

BUCKET_NAME = "dva-lab1-s3-dva-presigned-<ACCOUNT_ID>"  # substitua <ACCOUNT_ID> pelo ID da sua conta AWS (12 dígitos)
OBJECT_KEY = "dva-c02.png"
ARQUIVO_LOCAL = "dva-c02.png"

s3_client = boto3.client("s3")


def gerar_presigned_post(
    bucket: str,
    key: str,
    content_type: str = "image/jpeg",
    tamanho_min: int = 1,
    tamanho_max: int = 10 * 1024 * 1024,  # 10 MB
    expiracao: int = 3600,
) -> dict:
    """
    Gera um formulário POST pré-assinado para upload no S3.

    Diferente do PUT, o POST permite impor condições (tamanho mínimo/máximo,
    content-type) que são validadas pelo S3 — ideal para formulários web.

    Args:
        bucket: Nome do bucket S3
        key: Chave de destino do objeto
        content_type: Tipo MIME permitido
        tamanho_min: Tamanho mínimo do arquivo em bytes
        tamanho_max: Tamanho máximo do arquivo em bytes
        expiracao: Tempo de expiração em segundos

    Returns:
        Dicionário com 'url' (endpoint) e 'fields' (campos do formulário)
    """
    try:
        response = s3_client.generate_presigned_post(
            Bucket=bucket,
            Key=key,
            Fields={"Content-Type": content_type},
            Conditions=[
                {"Content-Type": content_type},
                ["content-length-range", tamanho_min, tamanho_max],
            ],
            ExpiresIn=expiracao,
        )
        return response
    except ClientError as e:
        print(f"Erro ao gerar formulário POST: {e}")
        raise


def fazer_upload_post(presigned_post: dict, arquivo_path: str) -> None:
    """
    Simula upload usando o formulário POST pré-assinado.
    Em produção, os campos do formulário seriam enviados ao browser/app.

    Args:
        presigned_post: Resultado de generate_presigned_post
        arquivo_path: Caminho local do arquivo a ser enviado
    """
    import requests

    url = presigned_post["url"]
    fields = presigned_post["fields"]

    with open(arquivo_path, "rb") as f:
        files = {"file": (arquivo_path, f)}
        response = requests.post(url, data=fields, files=files)

    # S3 retorna 204 para POST com sucesso (sem body de resposta)
    if response.status_code == 204:
        print("Upload via POST realizado com sucesso (HTTP 204)!")
    else:
        print(f"Erro: {response.status_code}")
        print(response.text)


if __name__ == "__main__":
    print("=== Gerando Presigned POST para Upload Condicional ===")
    presigned = gerar_presigned_post(
        bucket=BUCKET_NAME,
        key=OBJECT_KEY,
        content_type="image/png",
        tamanho_max=5 * 1024 * 1024,  # 5 MB máximo
    )

    print("URL do endpoint:")
    print(presigned["url"])
    print("\nCampos do formulário (enviar junto com o arquivo):")
    for campo, valor in presigned["fields"].items():
        print(f"  {campo}: {valor}")

    print("\n--- Exemplo de uso em HTML ---")
    print(f'<form action="{presigned["url"]}" method="post" enctype="multipart/form-data">')
    for campo, valor in presigned["fields"].items():
        print(f'  <input type="hidden" name="{campo}" value="{valor}">')
    print('  <input type="file" name="file">')
    print('  <input type="submit" value="Upload">')
    print("</form>")

    print("\n--- Realizando upload da imagem dva-c02.png ---")
    fazer_upload_post(presigned, ARQUIVO_LOCAL)

    print("\n--- Diferenças entre PUT e POST ---")
    print("PUT:  URL simples, sem condições, ideal para apps server-to-server")
    print("POST: Formulário com condições (tamanho, tipo), ideal para browsers/formulários web")
