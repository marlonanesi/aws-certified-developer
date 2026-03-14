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
TOKEN = ""


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
