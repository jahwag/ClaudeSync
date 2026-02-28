import subprocess
import base64
import logging
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SessionKeyManager:
    def __init__(self, ssh_key_path=None):
        self.logger = logging.getLogger(__name__)
        # Allow config-provided ssh_key_path to guide key discovery
        self.ssh_key_path = self._find_ssh_key(ssh_key_path)

    def _find_ssh_key(self, configured_path=None):
        """
        Locate an SSH private key for session encryption.
        Priority:
          1. If configured_path points to a specific file, check it first
          2. If configured_path is a directory, search it alongside ~/.ssh
          3. Fall back to ~/.ssh with default key names
          4. Prompt the user as a last resort
        """
        default_ssh_dir = Path.home() / ".ssh"
        key_names = ["id_ed25519", "id_ecdsa"]
        search_dirs = [default_ssh_dir]

        if configured_path:
            configured = Path(configured_path)

            if configured.is_file():
                # Config points directly to a key file — use it immediately
                return str(configured)

            if configured.is_dir():
                # Config is a directory — search it in addition to ~/.ssh
                if configured != default_ssh_dir:
                    search_dirs.insert(0, configured)
            else:
                # Path doesn't exist — warn and fall through to defaults
                self.logger.warning(
                    "Configured ssh_key_path not found: %s", configured_path
                )

        # Search all candidate directories for supported key names
        for search_dir in search_dirs:
            for key_name in key_names:
                key_path = search_dir / key_name
                if key_path.exists():
                    return str(key_path)

        # If no supported key is found, prompt the user to generate an Ed25519 key
        self.logger.warning(
            "* No supported SSH key found. RSA keys are no longer supported."
        )
        self.logger.warning(
            "* Please generate an Ed25519 key using the following command:"
        )
        self.logger.warning('  ssh-keygen -t ed25519 -C "your_email@example.com"')
        self.logger.warning(
            "* If you have NOT specified a custom ssh_key_path in config,"
        )
        self.logger.warning("* have created a key, and are still seeing this message,")
        self.logger.warning(
            "  be sure to name your key 'id_ed25519' or 'id_ecdsa' so it's found automatically."
        )
        self.logger.warning(
            "* Or set ssh_key_path with the full key name in your .claudesync/config.local.json"
        )
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
