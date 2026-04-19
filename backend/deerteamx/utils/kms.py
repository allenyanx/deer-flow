"""DeerTeamX Key Management Service (KMS)

Provides AES-256-GCM encryption/decryption for sensitive data storage.
Used to encrypt LLM API keys, tokens, and other secrets before storing in PostgreSQL.

Security Features:
- AES-256-GCM authenticated encryption
- Random IV (Initialization Vector) per encryption
- Base64 encoding for storage compatibility
- Master key validation and rotation support
"""

import base64
import os
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class KMSManager:
    """Key Management Service for sensitive data encryption/decryption."""
    
    def __init__(self, master_key: str):
        """Initialize KMS with master key.
        
        Args:
            master_key: AES-256 master key (min 32 bytes)
            
        Raises:
            ValueError: If master key is too short
        """
        if len(master_key) < 32:
            raise ValueError(f"Master key must be at least 32 bytes, got {len(master_key)}")
        
        # Derive 256-bit key from master key using SHA-256
        self._key = self._derive_key(master_key)
        self._aesgcm = AESGCM(self._key)
    
    @staticmethod
    def _derive_key(master_key: str) -> bytes:
        """Derive 256-bit encryption key from master key using SHA-256.
        
        Args:
            master_key: Raw master key string
            
        Returns:
            32-byte derived key
        """
        import hashlib
        return hashlib.sha256(master_key.encode('utf-8')).digest()
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext string using AES-256-GCM.
        
        Args:
            plaintext: Sensitive data to encrypt
            
        Returns:
            Base64-encoded ciphertext (IV + tag + ciphertext)
            
        Example:
            >>> kms = KMSManager("my-secure-master-key-at-least-32-chars!")
            >>> encrypted = kms.encrypt("sk-openai-123456")
            >>> print(encrypted)  # Base64 string
        """
        if not plaintext:
            raise ValueError("Plaintext cannot be empty")
        
        # Generate random 96-bit IV (recommended for GCM)
        iv = os.urandom(12)
        
        # Encrypt (returns ciphertext + 16-byte authentication tag)
        ciphertext = self._aesgcm.encrypt(iv, plaintext.encode('utf-8'), None)
        
        # Combine IV + ciphertext and encode as base64
        combined = iv + ciphertext
        return base64.b64encode(combined).decode('utf-8')
    
    def decrypt(self, ciphertext_b64: str) -> str:
        """Decrypt base64-encoded ciphertext using AES-256-GCM.
        
        Args:
            ciphertext_b64: Base64-encoded ciphertext (IV + tag + ciphertext)
            
        Returns:
            Decrypted plaintext string
            
        Raises:
            ValueError: If decryption fails (invalid key, corrupted data, etc.)
            
        Example:
            >>> kms = KMSManager("my-secure-master-key-at-least-32-chars!")
            >>> decrypted = kms.decrypt(encrypted)
            >>> print(decrypted)  # "sk-openai-123456"
        """
        if not ciphertext_b64:
            raise ValueError("Ciphertext cannot be empty")
        
        try:
            # Decode base64
            combined = base64.b64decode(ciphertext_b64)
            
            # Extract IV (first 12 bytes) and ciphertext
            iv = combined[:12]
            ciphertext = combined[12:]
            
            # Decrypt (verifies authentication tag automatically)
            plaintext = self._aesgcm.decrypt(iv, ciphertext, None)
            
            return plaintext.decode('utf-8')
            
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")
    
    def encrypt_optional(self, plaintext: Optional[str]) -> Optional[str]:
        """Encrypt optional plaintext (handles None gracefully).
        
        Args:
            plaintext: Optional sensitive data to encrypt
            
        Returns:
            Encrypted string or None if input is None
        """
        if plaintext is None:
            return None
        return self.encrypt(plaintext)
    
    def decrypt_optional(self, ciphertext_b64: Optional[str]) -> Optional[str]:
        """Decrypt optional ciphertext (handles None gracefully).
        
        Args:
            ciphertext_b64: Optional encrypted string
            
        Returns:
            Decrypted string or None if input is None
        """
        if ciphertext_b64 is None:
            return None
        return self.decrypt(ciphertext_b64)
    
    def rotate_key(self, new_master_key: str, old_ciphertexts: list[str]) -> list[str]:
        """Rotate encryption key by re-encrypting existing ciphertexts.
        
        Args:
            new_master_key: New master key for re-encryption
            old_ciphertexts: List of ciphertexts encrypted with old key
            
        Returns:
            List of re-encrypted ciphertexts using new key
            
        Note:
            This method should be called during key rotation procedures.
            Update the database with returned ciphertexts after successful rotation.
        """
        new_kms = KMSManager(new_master_key)
        reencrypted = []
        
        for old_ct in old_ciphertexts:
            # Decrypt with old key, encrypt with new key
            plaintext = self.decrypt(old_ct)
            new_ct = new_kms.encrypt(plaintext)
            reencrypted.append(new_ct)
        
        return reencrypted


# Global KMS instance (lazy initialization)
_kms_instance: Optional[KMSManager] = None


def get_kms(master_key: Optional[str] = None) -> KMSManager:
    """Get global KMS instance (singleton pattern).
    
    Args:
        master_key: Master key for initialization (required on first call)
        
    Returns:
        KMSManager instance
        
    Raises:
        RuntimeError: If called before initialization
    """
    global _kms_instance
    
    if _kms_instance is None:
        if master_key is None:
            raise RuntimeError(
                "KMS not initialized. Call get_kms(master_key=...) on first invocation."
            )
        _kms_instance = KMSManager(master_key)
    
    return _kms_instance


def reset_kms():
    """Reset global KMS instance (useful for testing)."""
    global _kms_instance
    _kms_instance = None
