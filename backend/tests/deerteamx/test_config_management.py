"""Unit tests for DeerTeamX configuration management."""

import sys
from pathlib import Path

# Ensure backend root is in Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from deerteamx.config.settings import DeerTeamXSettings
from deerteamx.utils.kms import KMSManager, get_kms, reset_kms


class TestDeerTeamXSettings:
    """Test configuration settings validation."""
    
    def test_default_settings(self):
        """Test default settings are valid."""
        settings = DeerTeamXSettings()
        assert settings.APP_NAME == "DeerTeamX"
        assert settings.APP_ENV == "development"
        assert settings.DEBUG is False
        assert len(settings.JWT_SECRET_KEY) >= 32
    
    def test_invalid_app_env(self):
        """Test APP_ENV validation."""
        with pytest.raises(ValueError, match="APP_ENV must be one of"):
            DeerTeamXSettings(APP_ENV="invalid")
    
    def test_valid_app_env_values(self):
        """Test valid APP_ENV values."""
        for env in ["development", "staging", "production"]:
            settings = DeerTeamXSettings(APP_ENV=env)
            assert settings.APP_ENV == env
    
    def test_invalid_database_url(self):
        """Test DATABASE_URL format validation."""
        with pytest.raises(ValueError, match="DATABASE_URL must start with"):
            DeerTeamXSettings(DATABASE_URL="mysql://localhost/db")
    
    def test_valid_database_urls(self):
        """Test valid DATABASE_URL formats."""
        for url in [
            "postgresql://user:pass@localhost/db",
            "postgresql+asyncpg://user:pass@localhost/db"
        ]:
            settings = DeerTeamXSettings(DATABASE_URL=url)
            assert settings.DATABASE_URL == url
    
    def test_invalid_redis_url(self):
        """Test REDIS_URL format validation."""
        with pytest.raises(ValueError, match="REDIS_URL must start with"):
            DeerTeamXSettings(REDIS_URL="memcached://localhost")
    
    def test_jwt_secret_key_min_length(self):
        """Test JWT_SECRET_KEY minimum length."""
        with pytest.raises(ValueError):
            DeerTeamXSettings(JWT_SECRET_KEY="short")
        
        # Valid key (32 chars)
        settings = DeerTeamXSettings(JWT_SECRET_KEY="a" * 32)
        assert len(settings.JWT_SECRET_KEY) == 32
    
    def test_encryption_master_key_min_length(self):
        """Test ENCRYPTION_MASTER_KEY minimum length."""
        with pytest.raises(ValueError):
            DeerTeamXSettings(ENCRYPTION_MASTER_KEY="short")
        
        # Valid key (32 chars)
        settings = DeerTeamXSettings(ENCRYPTION_MASTER_KEY="b" * 32)
        assert len(settings.ENCRYPTION_MASTER_KEY) == 32
    
    def test_bcrypt_rounds_range(self):
        """Test BCRYPT_ROUNDS range validation."""
        with pytest.raises(ValueError):
            DeerTeamXSettings(BCRYPT_ROUNDS=5)  # Too low
        
        with pytest.raises(ValueError):
            DeerTeamXSettings(BCRYPT_ROUNDS=15)  # Too high
        
        # Valid value
        settings = DeerTeamXSettings(BCRYPT_ROUNDS=12)
        assert settings.BCRYPT_ROUNDS == 12
    
    def test_cors_origins_parsing(self):
        """Test CORS_ORIGINS list parsing."""
        settings = DeerTeamXSettings(
            CORS_ORIGINS="http://localhost:3000,https://example.com"
        )
        assert settings.cors_origins_list == [
            "http://localhost:3000",
            "https://example.com"
        ]
    
    def test_validate_all_production_warnings(self):
        """Test production environment warnings."""
        settings = DeerTeamXSettings(
            APP_ENV="production",
            JWT_SECRET_KEY="change-this-to-a-random-string-min-32-chars",
            ENCRYPTION_MASTER_KEY="aes-256-gcm-master-key-here-min-32-chars"
        )
        
        warnings = settings.validate_all()
        assert any("JWT_SECRET_KEY" in w for w in warnings)
        assert any("ENCRYPTION_MASTER_KEY" in w in warnings)
    
    def test_feature_flags_defaults(self):
        """Test feature flag default values."""
        settings = DeerTeamXSettings()
        assert settings.FEATURE_LONG_TERM_MEMORY is True
        assert settings.FEATURE_CONSENSUS_MODE is True
        assert settings.FEATURE_HUMAN_FEEDBACK is True
        assert settings.FEATURE_STATE_PERSISTENCE is True
        assert settings.FEATURE_CLI_EXECUTION is False


class TestKMSManager:
    """Test KMS encryption/decryption."""
    
    @pytest.fixture(autouse=True)
    def reset_kms_instance(self):
        """Reset KMS singleton between tests."""
        reset_kms()
        yield
        reset_kms()
    
    def test_encrypt_decrypt_roundtrip(self):
        """Test encryption and decryption roundtrip."""
        kms = KMSManager("test-master-key-at-least-32-characters!")
        
        plaintext = "secret-api-key-12345"
        encrypted = kms.encrypt(plaintext)
        decrypted = kms.decrypt(encrypted)
        
        assert decrypted == plaintext
        assert encrypted != plaintext  # Ensure encryption occurred
    
    def test_encryption_produces_different_ciphertexts(self):
        """Test that encrypting same plaintext produces different ciphertexts."""
        kms = KMSManager("test-master-key-at-least-32-characters!")
        
        plaintext = "same-secret"
        encrypted1 = kms.encrypt(plaintext)
        encrypted2 = kms.encrypt(plaintext)
        
        assert encrypted1 != encrypted2  # Different IV each time
        
        # But both decrypt to same plaintext
        assert kms.decrypt(encrypted1) == plaintext
        assert kms.decrypt(encrypted2) == plaintext
    
    def test_decrypt_invalid_ciphertext(self):
        """Test decryption of invalid ciphertext raises error."""
        kms = KMSManager("test-master-key-at-least-32-characters!")
        
        with pytest.raises(ValueError, match="Decryption failed"):
            kms.decrypt("invalid-base64!!!")
    
    def test_decrypt_with_wrong_key(self):
        """Test decryption with wrong key fails."""
        kms1 = KMSManager("key-one-at-least-32-characters-long!!")
        kms2 = KMSManager("key-two-at-least-32-characters-long!!")
        
        plaintext = "secret-data"
        encrypted = kms1.encrypt(plaintext)
        
        with pytest.raises(ValueError, match="Decryption failed"):
            kms2.decrypt(encrypted)
    
    def test_encrypt_empty_plaintext(self):
        """Test encryption of empty string raises error."""
        kms = KMSManager("test-master-key-at-least-32-characters!")
        
        with pytest.raises(ValueError, match="Plaintext cannot be empty"):
            kms.encrypt("")
    
    def test_decrypt_empty_ciphertext(self):
        """Test decryption of empty string raises error."""
        kms = KMSManager("test-master-key-at-least-32-characters!")
        
        with pytest.raises(ValueError, match="Ciphertext cannot be empty"):
            kms.decrypt("")
    
    def test_encrypt_optional_with_none(self):
        """Test encrypt_optional handles None gracefully."""
        kms = KMSManager("test-master-key-at-least-32-characters!")
        
        result = kms.encrypt_optional(None)
        assert result is None
    
    def test_decrypt_optional_with_none(self):
        """Test decrypt_optional handles None gracefully."""
        kms = KMSManager("test-master-key-at-least-32-characters!")
        
        result = kms.decrypt_optional(None)
        assert result is None
    
    def test_key_rotation(self):
        """Test key rotation re-encrypts data correctly."""
        old_key = "old-master-key-at-least-32-characters!"
        new_key = "new-master-key-at-least-32-characters!"
        
        old_kms = KMSManager(old_key)
        new_kms = KMSManager(new_key)
        
        # Encrypt with old key
        plaintexts = ["secret1", "secret2", "secret3"]
        old_ciphertexts = [old_kms.encrypt(p) for p in plaintexts]
        
        # Rotate keys
        new_ciphertexts = old_kms.rotate_key(new_key, old_ciphertexts)
        
        # Verify new ciphertexts decrypt with new key
        for i, new_ct in enumerate(new_ciphertexts):
            decrypted = new_kms.decrypt(new_ct)
            assert decrypted == plaintexts[i]
        
        # Verify old ciphertexts cannot be decrypted with new key
        for old_ct in old_ciphertexts:
            with pytest.raises(ValueError):
                new_kms.decrypt(old_ct)
    
    def test_global_kms_singleton(self):
        """Test global KMS instance is singleton."""
        master_key = "global-test-key-at-least-32-characters!"
        
        kms1 = get_kms(master_key)
        kms2 = get_kms()  # Should return same instance
        
        assert kms1 is kms2
    
    def test_global_kms_not_initialized(self):
        """Test get_kms without initialization raises error."""
        reset_kms()
        
        with pytest.raises(RuntimeError, match="KMS not initialized"):
            get_kms()
    
    def test_master_key_too_short(self):
        """Test KMS initialization with short key raises error."""
        with pytest.raises(ValueError, match="Master key must be at least 32 bytes"):
            KMSManager("short")


class TestConfigurationIntegration:
    """Integration tests for configuration system."""
    
    def test_settings_with_env_vars(self, monkeypatch):
        """Test settings load from environment variables."""
        monkeypatch.setenv("APP_ENV", "staging")
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("JWT_SECRET_KEY", "env-var-key-at-least-32-chars!!")
        
        # Clear cache to force reload
        from deerteamx.config.settings import get_settings
        get_settings.cache_clear()
        
        settings = get_settings()
        assert settings.APP_ENV == "staging"
        assert settings.DEBUG is True
        assert settings.JWT_SECRET_KEY == "env-var-key-at-least-32-chars!!"
    
    def test_kms_integration_with_settings(self):
        """Test KMS works with settings master key."""
        from deerteamx.config.settings import get_settings
        
        settings = get_settings()
        reset_kms()
        
        kms = get_kms(settings.ENCRYPTION_MASTER_KEY)
        
        # Should work without errors
        encrypted = kms.encrypt("test-secret")
        decrypted = kms.decrypt(encrypted)
        assert decrypted == "test-secret"
