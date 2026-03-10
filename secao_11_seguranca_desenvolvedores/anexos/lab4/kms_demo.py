"""
kms_demo.py – Demonstração de operações KMS: encrypt/decrypt direto e Envelope Encryption

Pré-requisitos:
  pip install boto3 cryptography

Uso:
  python kms_demo.py                   # executa todos os exemplos
  python kms_demo.py --action direct   # somente encrypt/decrypt direto
  python kms_demo.py --action envelope # somente Envelope Encryption
"""

import argparse
import base64
import hashlib
import os

import boto3
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_ALIAS = "alias/lab4-cmk"
REGION = "us-east-1"  # ajuste para sua região


def get_kms_client():
    return boto3.client("kms", region_name=REGION)


# ──────────────────────────────────────────────
# Parte 1: Encrypt / Decrypt direto (≤ 4 KB)
# ──────────────────────────────────────────────

def demo_direct_encrypt_decrypt():
    print("\n=== Encrypt / Decrypt direto (≤ 4 KB) ===")
    kms = get_kms_client()

    plaintext = b"Dado sensivel: senha_db_prod_abc123!"

    # Criptografar
    response = kms.encrypt(KeyId=KEY_ALIAS, Plaintext=plaintext)
    ciphertext = response["CiphertextBlob"]
    print(f"Criptografado (base64): {base64.b64encode(ciphertext).decode()[:60]}...")

    # Descriptografar
    response = kms.decrypt(CiphertextBlob=ciphertext)
    recovered = response["Plaintext"]
    print(f"Descriptografado: {recovered.decode()}")
    assert recovered == plaintext, "Erro: dado recuperado não bate com o original!"
    print("✓ Dados conferem.\n")


# ──────────────────────────────────────────────
# Parte 2: Envelope Encryption (dados > 4 KB)
# ──────────────────────────────────────────────

def demo_envelope_encryption():
    print("\n=== Envelope Encryption (dados de tamanho arbitrário) ===")
    kms = get_kms_client()

    # Simular dado grande (> 4 KB)
    large_data = b"Registro confidencial de cliente. " * 200
    print(f"Tamanho do dado original: {len(large_data)} bytes")

    # ── ENCRYPT ──

    # 1. Gerar Data Key via KMS (plaintext + cifrada)
    response = kms.generate_data_key(KeyId=KEY_ALIAS, KeySpec="AES_256")
    data_key_plaintext = response["Plaintext"]       # usar agora, descartar logo após
    data_key_encrypted = response["CiphertextBlob"]  # armazenar junto aos dados

    # 2. Criptografar os dados localmente com a Data Key (AES-256-GCM)
    aes_key = hashlib.sha256(data_key_plaintext).digest()
    nonce = os.urandom(12)
    aesgcm = AESGCM(aes_key)
    encrypted_data = aesgcm.encrypt(nonce, large_data, None)

    # 3. "Esquecer" a Data Key plaintext (na prática: não persisti-la)
    del data_key_plaintext

    print(f"Data Key cifrada (base64): {base64.b64encode(data_key_encrypted).decode()[:50]}...")
    print(f"Dados cifrados: {len(encrypted_data)} bytes")

    # O que armazenar: encrypted_data + nonce + data_key_encrypted

    # ── DECRYPT ──

    # 1. Recuperar a Data Key plaintext via KMS
    response = kms.decrypt(CiphertextBlob=data_key_encrypted)
    data_key_recovered = response["Plaintext"]

    # 2. Descriptografar os dados localmente
    aes_key_recovered = hashlib.sha256(data_key_recovered).digest()
    aesgcm_dec = AESGCM(aes_key_recovered)
    decrypted_data = aesgcm_dec.decrypt(nonce, encrypted_data, None)

    print(f"Dados recuperados: {len(decrypted_data)} bytes")
    assert decrypted_data == large_data, "Erro: dado recuperado não bate com o original!"
    print("✓ Dados conferem. Apenas 2 chamadas KMS para qualquer volume de dados.\n")


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Demonstração de operações KMS")
    parser.add_argument(
        "--action",
        choices=["direct", "envelope", "all"],
        default="all",
        help="Ação a executar (padrão: all)",
    )
    args = parser.parse_args()

    if args.action in ("direct", "all"):
        demo_direct_encrypt_decrypt()
    if args.action in ("envelope", "all"):
        demo_envelope_encryption()


if __name__ == "__main__":
    main()
