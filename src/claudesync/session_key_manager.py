import os
import subprocess
import tempfile
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
        key_names = ["id_ed25519", "id_rsa", "id_ecdsa"]
        for key_name in key_names:
            key_path = ssh_dir / key_name
            if key_path.exists():
                return str(key_path)
        return input("Enter the full path to your SSH private key: ")

    def _get_key_type(self):
        try:
            result = subprocess.run(
                ["ssh-keygen", "-l", "-f", self.ssh_key_path],
                capture_output=True,
                text=True,
                check=True,
            )
            output = result.stdout.lower()
            if "rsa" in output:
                return "rsa"
            elif "ecdsa" in output:
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
        key_type = self._get_key_type()

        if key_type == "rsa":
            return self._encrypt_rsa(session_key)
        else:  # For ed25519 and ecdsa
            return self._encrypt_symmetric(session_key)

    def _encrypt_rsa(self, session_key):
        temp_file_path = None
        pub_key_file_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
                temp_file.write(session_key)
                temp_file_path = temp_file.name

            result = subprocess.run(
                ["ssh-keygen", "-f", self.ssh_key_path, "-e", "-m", "PKCS8"],
                capture_output=True,
                text=True,
                check=True,
            )
            public_key = result.stdout

            with tempfile.NamedTemporaryFile(mode="w+", delete=False) as pub_key_file:
                pub_key_file.write(public_key)
                pub_key_file_path = pub_key_file.name

            encrypted_output = subprocess.run(
                [
                    "openssl",
                    "pkeyutl",
                    "-encrypt",
                    "-pubin",
                    "-inkey",
                    pub_key_file_path,
                    "-in",
                    temp_file_path,
                    "-pkeyopt",
                    "rsa_padding_mode:oaep",
                    "-pkeyopt",
                    "rsa_oaep_md:sha256",
                ],
                capture_output=True,
                check=True,
            )

            encrypted_session_key = base64.b64encode(encrypted_output.stdout).decode(
                "utf-8"
            )

            return encrypted_session_key, "rsa"
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Encryption failed: {e}")
            raise RuntimeError(
                "Failed to encrypt session key. Check if openssl and ssh-keygen are installed and the SSH key is valid."
            )
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            if pub_key_file_path and os.path.exists(pub_key_file_path):
                os.unlink(pub_key_file_path)

    def _encrypt_symmetric(self, session_key):
        key = self._derive_key_from_ssh_key()
        f = Fernet(key)
        encrypted_session_key = f.encrypt(session_key.encode()).decode()
        return encrypted_session_key, "symmetric"

    def decrypt_session_key(self, provider, encryption_method, encrypted_session_key):
        if not encrypted_session_key or not encryption_method:
            return None

        if encryption_method == "rsa":
            return self._decrypt_rsa(encrypted_session_key)
        elif encryption_method == "symmetric":
            return self._decrypt_symmetric(encrypted_session_key)
        else:
            raise ValueError(f"Unknown encryption method: {encryption_method}")

    def _decrypt_rsa(self, encrypted_session_key):
        temp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb+", delete=False) as temp_file:
                temp_file.write(base64.b64decode(encrypted_session_key))
                temp_file_path = temp_file.name

            decrypted_output = subprocess.run(
                [
                    "openssl",
                    "pkeyutl",
                    "-decrypt",
                    "-inkey",
                    self.ssh_key_path,
                    "-in",
                    temp_file_path,
                    "-pkeyopt",
                    "rsa_padding_mode:oaep",
                    "-pkeyopt",
                    "rsa_oaep_md:sha256",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            return decrypted_output.stdout.strip()

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Decryption failed: {e}")
            raise RuntimeError(
                "Failed to decrypt session key. Make sure the SSH key is valid and matches the one used for encryption."
            )
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def _decrypt_symmetric(self, encrypted_session_key):
        key = self._derive_key_from_ssh_key()
        f = Fernet(key)
        return f.decrypt(encrypted_session_key.encode()).decode()
