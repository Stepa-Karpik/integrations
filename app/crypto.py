import base64
import hashlib
import os
from cryptography.fernet import Fernet


def _fernet() -> Fernet:
    raw = os.getenv('INTEGRATIONS_ENCRYPTION_KEY', 'dev-integrations-key').encode()
    key = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    return Fernet(key)


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()
