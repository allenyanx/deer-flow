"""DeerTeamX KMS 加密与脱敏模块。

该模块提供基于 Fernet (AES-128-CBC) 的对称加密实现，
用于保护团队配置中的敏感字段（如 API Keys、Passwords）。
同时提供数据脱敏功能，确保日志和 API 响应中不泄露明文敏感信息。
"""

import os
import base64
import logging
from typing import Optional, Dict, Any

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class KMSService:
    """密钥管理服务 (KMS) 封装类。"""

    def __init__(self, secret_key: Optional[str] = None):
        """
        初始化 KMS 服务。
        
        Args:
            secret_key: 32-byte URL-safe base64-encoded key。如果未提供，则从环境变量 DEERTEAMX_KMS_KEY 读取。
        """
        key = secret_key or os.getenv("DEERTEAMX_KMS_KEY")
        if not key:
            # 开发环境下生成一个临时 Key（生产环境必须通过环境变量注入）
            logger.warning("DEERTEAMX_KMS_KEY not found. Generating a temporary key for development.")
            key = Fernet.generate_key().decode()
        
        if isinstance(key, str):
            key = key.encode()
            
        self.cipher = Fernet(key)
        self.sensitive_keywords = ["api_key", "secret", "password", "token"]

    def encrypt(self, plaintext: str) -> str:
        """加密字符串。"""
        if not plaintext:
            return ""
        try:
            encrypted_bytes = self.cipher.encrypt(plaintext.encode())
            return base64.urlsafe_b64encode(encrypted_bytes).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(self, ciphertext: str) -> str:
        """解密字符串。"""
        if not ciphertext:
            return ""
        try:
            decoded_bytes = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted_bytes = self.cipher.decrypt(decoded_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """递归遍历字典，对敏感字段进行脱敏处理。"""
        masked_data = {}
        for key, value in data.items():
            if any(k in key.lower() for k in self.sensitive_keywords):
                masked_data[key] = "******"
            elif isinstance(value, dict):
                masked_data[key] = self.mask_sensitive_data(value)
            else:
                masked_data[key] = value
        return masked_data


# 全局单例
kms_service = KMSService()
