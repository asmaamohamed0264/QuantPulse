"""
Encryption utilities for sensitive data storage
"""
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional
import os

class DataEncryption:
    """
    Encryption class for sensitive data like API keys and credentials
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption with provided key or generate from secret
        """
        if encryption_key:
            # Use provided key to derive encryption key
            self.fernet = self._create_fernet_from_key(encryption_key)
        else:
            # Generate a new key (for first-time setup)
            key = Fernet.generate_key()
            self.fernet = Fernet(key)
    
    def _create_fernet_from_key(self, key: str) -> Fernet:
        """Create Fernet instance from string key"""
        # Use PBKDF2 to derive a proper encryption key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'quantpulse_salt',  # In production, use a random salt per user
            iterations=100000,
        )
        key_bytes = base64.urlsafe_b64encode(kdf.derive(key.encode()))
        return Fernet(key_bytes)
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt string data and return base64 encoded result
        """
        if not data:
            return ""
        
        try:
            encrypted_data = self.fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            raise ValueError(f"Encryption failed: {str(e)}")
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt base64 encoded data and return original string
        """
        if not encrypted_data:
            return ""
        
        try:
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.fernet.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")
    
    def is_encrypted(self, data: str) -> bool:
        """
        Check if data appears to be encrypted (base64 format)
        """
        if not data:
            return False
        
        try:
            # Try to decode as base64
            decoded = base64.urlsafe_b64decode(data)
            # Check if it looks like Fernet encrypted data
            return len(decoded) >= 32  # Fernet adds at least 32 bytes overhead
        except:
            return False


# Global encryption instance
_encryption_instance: Optional[DataEncryption] = None

def get_encryption_instance(encryption_key: str) -> DataEncryption:
    """Get or create global encryption instance"""
    global _encryption_instance
    if _encryption_instance is None:
        _encryption_instance = DataEncryption(encryption_key)
    return _encryption_instance

def encrypt_credential(credential: str, encryption_key: str) -> str:
    """Utility function to encrypt a credential"""
    if not credential:
        return ""
    
    encryption = get_encryption_instance(encryption_key)
    return encryption.encrypt(credential)

def decrypt_credential(encrypted_credential: str, encryption_key: str) -> str:
    """Utility function to decrypt a credential"""
    if not encrypted_credential:
        return ""
    
    encryption = get_encryption_instance(encryption_key)
    return encryption.decrypt(encrypted_credential)

def migrate_credentials_to_encrypted(db_session, encryption_key: str):
    """
    Utility to migrate existing plaintext credentials to encrypted format
    """
    from app.models.broker_account import BrokerAccount
    
    encryption = get_encryption_instance(encryption_key)
    
    # Get all broker accounts with plaintext credentials
    broker_accounts = db_session.query(BrokerAccount).all()
    
    for account in broker_accounts:
        updated = False
        
        # Encrypt API key if it's not already encrypted
        if account.api_key and not encryption.is_encrypted(account.api_key):
            account.api_key = encryption.encrypt(account.api_key)
            updated = True
        
        # Encrypt API secret if it's not already encrypted
        if account.api_secret and not encryption.is_encrypted(account.api_secret):
            account.api_secret = encryption.encrypt(account.api_secret)
            updated = True
        
        # Encrypt additional credentials if they exist
        if hasattr(account, 'additional_credentials') and account.additional_credentials:
            if not encryption.is_encrypted(account.additional_credentials):
                account.additional_credentials = encryption.encrypt(account.additional_credentials)
                updated = True
        
        if updated:
            db_session.add(account)
    
    db_session.commit()
    return f"Migrated credentials for {len(broker_accounts)} broker accounts"


class SecureCredentialManager:
    """
    Manager for handling encrypted credentials with automatic encryption/decryption
    """
    
    def __init__(self, encryption_key: str):
        self.encryption = DataEncryption(encryption_key)
    
    def store_credential(self, credential: str) -> str:
        """Store credential in encrypted format"""
        return self.encryption.encrypt(credential)
    
    def retrieve_credential(self, encrypted_credential: str) -> str:
        """Retrieve and decrypt credential"""
        return self.encryption.decrypt(encrypted_credential)
    
    def update_credential(self, old_encrypted: str, new_plaintext: str) -> str:
        """Update an encrypted credential with new value"""
        # Simply encrypt the new value
        return self.encryption.encrypt(new_plaintext)
    
    def is_valid_credential(self, encrypted_credential: str) -> bool:
        """Check if encrypted credential can be decrypted"""
        try:
            decrypted = self.encryption.decrypt(encrypted_credential)
            return bool(decrypted)
        except:
            return False