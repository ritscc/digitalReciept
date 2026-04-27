import base64
import csv
import json
import os
from datetime import datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

KEYS_DIR = "keys"
OUTPUT_JSON = "receipts_output.json"


def ensure_keys_dir():
    os.makedirs(KEYS_DIR, exist_ok=True)


def generate_keys(keyname: str):
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    priv_path = os.path.join(KEYS_DIR, keyname)
    pub_path = os.path.join(KEYS_DIR, f"{keyname}.pub")

    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    with open(priv_path, "wb") as f:
        f.write(priv_pem)

    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    with open(pub_path, "wb") as f:
        f.write(pub_pem)

    print(f"[Success] Keys generated: {priv_path}, {pub_path}")


def load_private_key(keyname: str) -> ed25519.Ed25519PrivateKey:
    path = os.path.join(KEYS_DIR, keyname)
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def load_public_key(keyname: str) -> ed25519.Ed25519PublicKey:
    path = os.path.join(KEYS_DIR, f"{keyname}.pub")
    with open(path, "rb") as f:
        return serialization.load_pem_public_key(f.read())


def create_signed_receipt(
    private_key, date: str, amount: int, recipient: str, issuer: str
):
    receipt = {"date": date, "amount": amount, "recipient": recipient, "issuer": issuer}
    json_data = json.dumps(receipt, separators=(",", ":"), ensure_ascii=False)
    receipt_b64 = base64.b64encode(json_data.encode("utf-8")).decode("utf-8")

    signature = private_key.sign(receipt_b64.encode("utf-8"))
    signature_b64 = base64.b64encode(signature).decode("utf-8")

    return receipt_b64, signature_b64


def cmd_generate():
    keyname = input("Enter new key name (e.g., rcc_2026): ").strip()
    if not keyname:
        print("Key name cannot be empty.")
        return
    if os.path.exists(os.path.join(KEYS_DIR, keyname)):
        print("Key already exists.")
        return
    generate_keys(keyname)


def cmd_sign_single():
    keyname = input("Enter key name to use for signing: ").strip()
    try:
        private_key = load_private_key(keyname)
    except FileNotFoundError:
        print(f"Private key '{keyname}' not found in {KEYS_DIR}/.")
        return

    print("\n--- Enter Receipt Details ---")
    date = input("Date (e.g., 2026-05-01): ").strip()
    amount = input("Amount (e.g., 5000): ").strip()
    recipient = input("Recipient: ").strip()
    issuer = input("Issuer: ").strip()

    amount_val = int(amount) if amount.isdigit() else amount
    receipt_b64, signature_b64 = create_signed_receipt(
        private_key, date, amount_val, recipient, issuer
    )

    print("\n[Result] Copy the following data:")
    print("--- 領収書データ ---")
    print(receipt_b64)
    print("--- Ed25519 署名 ---")
    print(signature_b64)


def cmd_sign_batch():
    filename = input("Enter CSV file name (default: nameList.txt): ").strip()
    if not filename:
        filename = "nameList.txt"

    if not os.path.exists(filename):
        print(f"File '{filename}' not found.")
        return

    keyname = input("Enter key name to use for signing: ").strip()
    try:
        private_key = load_private_key(keyname)
    except FileNotFoundError:
        print(f"Private key '{keyname}' not found in {KEYS_DIR}/.")
        return

    date = datetime.now().strftime("%Y-%m-%d")
    issuer = input("Enter Issuer Name (e.g., RCC President): ").strip()

    output_data = {
        "email_meta": {
            "subject": "【RCC】部費受領のお知らせと電子領収書",
            "body_template": "{recipient} 様\n\n部費を受領しました。\n以下の通り、電子領収書を発行します。\n\n[受領内容]\n受領日: {date}\n金額: {amount}円\n発行者: {issuer}\n\n--- 領収書データ(検証用) ---\n{receipt_b64}\n\n--- Ed25519 署名 ---\n{signature_b64}\n\n※ 領収書の検証は公式Discordの公開鍵と検証ツールを使用してください。\n",
        },
        "contents": [],
    }

    success_count = 0
    with open(filename, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 3:
                continue

            recipient = row[0].strip()
            email = row[1].strip()
            status = row[2].strip()

            if status == "1":
                amount = 1000
            elif status == "0":
                amount = 2000
            else:
                print(f"Skipping invalid status for {recipient}: {status}")
                continue

            receipt_b64, signature_b64 = create_signed_receipt(
                private_key, date, amount, recipient, issuer
            )

            output_data["contents"].append(
                {
                    "email": email,
                    "recipient": recipient,
                    "date": date,
                    "amount": amount,
                    "issuer": issuer,
                    "receipt_b64": receipt_b64,
                    "signature_b64": signature_b64,
                }
            )
            success_count += 1

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n[Success] Batch processed {success_count} receipts.")
    print(f"Output saved to {OUTPUT_JSON}")


def cmd_validate():
    print("Enter key name (e.g., rcc_2026) OR paste the Public Key PEM directly:")
    first_line = input("> ").strip()

    try:
        if first_line.startswith("-----BEGIN"):
            lines = [first_line]
            while True:
                line = input().strip()
                if not line:
                    continue
                lines.append(line)
                if line.startswith("-----END"):
                    break
            pem_data = "\n".join(lines)
            public_key = serialization.load_pem_public_key(pem_data.encode("utf-8"))
        else:
            keyname = first_line
            public_key = load_public_key(keyname)
    except FileNotFoundError:
        print(f"\n[Error] Public key '{first_line}.pub' not found in {KEYS_DIR}/.")
        return
    except ValueError:
        print("\n[Error] Invalid PEM format.")
        return
    except Exception as e:
        print(f"\n[Error] Failed to load public key: {e}")
        return

    receipt_b64 = input("\nEnter Base64 Receipt Data: ").strip()
    signature_b64 = input("Enter Base64 Signature: ").strip()

    try:
        signature = base64.b64decode(signature_b64)
        public_key.verify(signature, receipt_b64.encode("utf-8"))

        receipt_json = base64.b64decode(receipt_b64).decode("utf-8")
        receipt_data = json.loads(receipt_json)

        print("\n[Success] Signature is VALID.")
        print("Receipt Content:")
        for k, v in receipt_data.items():
            print(f"  {k}: {v}")
    except InvalidSignature:
        print("\n[Error] Signature is INVALID. Data may be tampered or wrong key used.")
    except Exception as e:
        print(f"\n[Error] Validation failed: {e}")


def main():
    ensure_keys_dir()
    while True:
        print("\n=== RCC Receipt Manager ===")
        print("1. Generate Keypair")
        print("2. Sign Single Receipt")
        print("3. Batch Sign from CSV (e.g., nameList.txt)")
        print("4. Validate Receipt")
        print("5. Exit")
        choice = input("Select action (1-5): ").strip()

        if choice == "1":
            cmd_generate()
        elif choice == "2":
            cmd_sign_single()
        elif choice == "3":
            cmd_sign_batch()
        elif choice == "4":
            cmd_validate()
        elif choice == "5":
            break
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
