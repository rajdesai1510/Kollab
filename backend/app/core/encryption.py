"""
Nexus — Encryption Manager (Class-based)
------------------------------------------------
Provides symmetric encryption / decryption for sensitive data stored in MongoDB.

Used for:
  - Instagram OAuth access tokens (stored encrypted in `users` collection)

Algorithm: Fernet (AES-128-CBC + HMAC-SHA256) via Python `cryptography` library.
Keys are 32-byte URL-safe base64-encoded strings generated with Fernet.generate_key().

Usage:
    from app.core.encryption import encryption_manager

    encrypted = encryption_manager.encrypt("raw_instagram_token")
    original  = encryption_manager.decrypt(encrypted)
"""

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings
from app.core.logger import logger


# ─────────────────────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────────────────────

class EncryptionError(Exception):
    """Raised when encryption fails (e.g., key misconfigured)."""
    pass


class DecryptionError(Exception):
    """Raised when decryption fails (e.g., tampered data, wrong key)."""
    pass


# ─────────────────────────────────────────────────────────────
# Encryption Manager Class
# ─────────────────────────────────────────────────────────────

class EncryptionManager:
    """
    Symmetric encryption using Fernet (AES-128 + HMAC).

    The encryption key is loaded from the ENCRYPTION_KEY environment
    variable and must be a valid Fernet key (32 URL-safe base64 bytes).

    Generate a new key with:
        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    """

    def __init__(self) -> None:
        self._fernet: Fernet | None = None

    def _get_fernet(self) -> Fernet:
        """
        Lazily initialise the Fernet instance.

        Lazy initialisation ensures the ENCRYPTION_KEY is read after
        the settings are loaded (important in test environments where
        keys may be overridden).
        """
        if self._fernet is None:
            try:
                key = settings.ENCRYPTION_KEY.encode()
                self._fernet = Fernet(key)
            except Exception as exc:
                raise EncryptionError(
                    f"Failed to initialise Fernet cipher. "
                    f"Ensure ENCRYPTION_KEY is a valid Fernet key. Error: {exc}"
                )
        return self._fernet

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.

        Returns a URL-safe base64-encoded ciphertext string
        safe for storage in MongoDB.

        Args:
            plaintext: The raw string to encrypt (e.g., an Instagram access token)

        Returns:
            Encrypted string (Fernet token as str)

        Raises:
            EncryptionError: If encryption fails
        """
        try:
            fernet = self._get_fernet()
            ciphertext = fernet.encrypt(plaintext.encode("utf-8"))
            return ciphertext.decode("utf-8")
        except EncryptionError:
            raise
        except Exception as exc:
            logger.error(f"Encryption failed: {exc}")
            raise EncryptionError(f"Encryption failed: {exc}")

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a Fernet-encrypted ciphertext string.

        Args:
            ciphertext: The encrypted string previously produced by encrypt()

        Returns:
            The original plaintext string

        Raises:
            DecryptionError: If the token is invalid or has been tampered with
        """
        try:
            fernet = self._get_fernet()
            plaintext = fernet.decrypt(ciphertext.encode("utf-8"))
            return plaintext.decode("utf-8")
        except InvalidToken:
            logger.warning("Decryption failed — invalid or tampered token.")
            raise DecryptionError(
                "Decryption failed. The token may be tampered with or the key has changed."
            )
        except Exception as exc:
            logger.error(f"Decryption error: {exc}")
            raise DecryptionError(f"Decryption failed: {exc}")

    def encrypt_if_present(self, value: str | None) -> str | None:
        """Encrypt a value only if it is not None. Convenience wrapper."""
        return self.encrypt(value) if value is not None else None

    def decrypt_if_present(self, value: str | None) -> str | None:
        """Decrypt a value only if it is not None. Convenience wrapper."""
        return self.decrypt(value) if value is not None else None


# ─────────────────────────────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────────────────────────────
encryption_manager = EncryptionManager()
