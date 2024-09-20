import subprocess
import base64
import logging
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SessionKeyManager:
    def __init__(self):
        self.ssh_key_path = self._find_ssh_key()
        self.logger = logging.getLogger(__name__)

    def _find_ssh_key(self):
        ssh_dir = Path.home() / ".ssh"
        key_names = ["id_ed25519", "id_ecdsa"]
        for key_name in key_names:
            key_path = ssh_dir / key_name
            if key_path.exists():
                return str(key_path)

        # If no supported key is found, prompt the user to generate an Ed25519 key
        print("* No supported SSH key found. RSA keys are no longer supported.")
        print("* Please generate an Ed25519 key using the following command:")
        print('ssh-keygen -t ed25519 -C "your_email@example.com"')
        return input("Enter the full path to your new Ed25519 private key: ")

    def _get_key_type(self):
        try:
            result = subprocess.run(
                ["ssh-keygen", "-l", "-f", self.ssh_key_path],
                capture_output=True,
                text=True,
                check=True,
            )
            output = result.stdout.lower()
            if "ecdsa" in output:
                return "ecdsa"
            elif "ed25519" in output:
                return "ed25519"
            else:
                raise ValueError(f"Unsupported key type for {self.ssh_key_path}")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to determine key type: {e}")
            raise RuntimeError(
                "Failed to determine SSH key type. Make sure the key file is valid and accessible."
            )

    def _derive_key_from_ssh_key(self):
        with open(self.ssh_key_path, "rb") as key_file:
            ssh_key_data = key_file.read()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"claudesync",  # Using a fixed salt; consider using a secure random salt in production
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(ssh_key_data))
        return key

    def encrypt_session_key(self, provider, session_key):
        self._get_key_type()
        return self._encrypt_symmetric(session_key)

    def _encrypt_symmetric(self, session_key):
        key = self._derive_key_from_ssh_key()
        f = Fernet(key)
        encrypted_session_key = f.encrypt(session_key.encode()).decode()
        return encrypted_session_key, "symmetric"

    def decrypt_session_key(self, provider, encryption_method, encrypted_session_key):
        if not encrypted_session_key or not encryption_method:
            return None

        if encryption_method == "symmetric":
            return self._decrypt_symmetric(encrypted_session_key)
        else:
            raise ValueError(f"Unknown encryption method: {encryption_method}")

    def _decrypt_symmetric(self, encrypted_session_key):
        key = self._derive_key_from_ssh_key()
        f = Fernet(key)
        return f.decrypt(encrypted_session_key.encode()).decode()
