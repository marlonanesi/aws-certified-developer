"""
decode_jwt.py – Inspeção manual do payload de um JWT (sem validação de assinatura)

Cole o token JWT na variável TOKEN antes de executar.
Não instala dependências externas — usa apenas stdlib.
"""

import base64
import json
import sys
import datetime

# Cole aqui o IdToken ou AccessToken obtido via AWS CLI / Cognito
TOKEN = "eyJraWQiOiI2T2NLNGU3UVhmV20rcE84QUNsdGlIOFFFZjVKXC82MzJrY1NPTUQrY1RxRT0iLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIxMzRjMWE2YS0yMDkxLTcwYzktYWQyMC1kZGU1MTQ2ZTY0OTUiLCJjb2duaXRvOmdyb3VwcyI6WyJhZG1pbnMiXSwiZW1haWxfdmVyaWZpZWQiOnRydWUsImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC5zYS1lYXN0LTEuYW1hem9uYXdzLmNvbVwvc2EtZWFzdC0xX2lWUjFQVkFJbyIsImNvZ25pdG86dXNlcm5hbWUiOiIxMzRjMWE2YS0yMDkxLTcwYzktYWQyMC1kZGU1MTQ2ZTY0OTUiLCJvcmlnaW5fanRpIjoiOTkwODE2MTAtNzcyNC00OWZkLWJiMmMtZDZjNjIzMDAwNzA0IiwiYXVkIjoiMTVodGIxaTcxaHBlODFvYjVqN2M2ZGNwa3AiLCJldmVudF9pZCI6ImFkZWE1OTBmLWQ0Y2UtNDVmMC05ODAyLWMyZmNkNDgxOTYyNiIsInRva2VuX3VzZSI6ImlkIiwiYXV0aF90aW1lIjoxNzczMzQ0NDk4LCJleHAiOjE3NzMzNDgwOTgsImlhdCI6MTc3MzM0NDQ5OCwianRpIjoiYzU5MWEzOWUtNWYzNC00Njg2LThlYTYtOGRjMTBkZGM3YzczIiwiZW1haWwiOiJ0ZXN0dXNlckBleGVtcGxvLmNvbSJ9.sypd3VaL7P4EmHvZ_vOcPoEGA_ugEJBsGw2QMW72rloZTHzTTVjLOha9Z4fOcAPG115QzlM7mZbgo6xAL1Y-JMsajhx0wf7KtMiT-kY_E_ySEcNUWIAVB_KO2sINoU_UbOkWBUTxgLDIAqo2avGZQiMi6RlrOaRXweFY9ay1tov7QNp6KDrAYk1nSI5VURa_KT3I5P6W3CYGoqOCO3ee4rP10PxOWauWwReB8OVtBNzi2BFpNc_lUQAH0P9u95qD08StzOKlqMWJksXqUKPQRvNRKQhinK1mob0MJRhpNfVZDBGK_rA4kN3vfWWYd2yWOv1QEuKQVFwSDZs-_8mINw"


def decode_payload(token: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Formato JWT inválido (esperado: header.payload.signature)")
    payload_b64 = parts[1]
    # JWT usa base64url sem padding — adicionar padding necessário
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding
    decoded = base64.urlsafe_b64decode(payload_b64)
    return json.loads(decoded)


def format_claim(key: str, value) -> str:
    if key in ("exp", "iat", "auth_time", "nbf"):
        try:
            dt = datetime.datetime.fromtimestamp(int(value), tz=datetime.timezone.utc)
            return f"{value}  ({dt.strftime('%Y-%m-%d %H:%M:%S UTC')})"
        except Exception:
            pass
    return str(value)


def main():
    token = TOKEN.strip()
    if token.startswith("<"):
        print("Erro: substitua <COLE_O_TOKEN_AQUI> pelo token JWT antes de executar.")
        sys.exit(1)

    try:
        payload = decode_payload(token)
    except Exception as e:
        print(f"Erro ao decodificar token: {e}")
        sys.exit(1)

    print("=" * 60)
    print("JWT PAYLOAD")
    print("=" * 60)
    for key, value in payload.items():
        print(f"  {key:30s} {format_claim(key, value)}")
    print("=" * 60)
    print()
    print("Payload JSON completo:")
    print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    main()
