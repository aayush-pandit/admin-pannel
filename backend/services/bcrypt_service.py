# File: backend/services/bcrypt_service.py
import hashlib
import os

class BcryptService:
    @staticmethod
    def hash_password(password: str) -> str:
        # Generate a random 16-byte salt
        salt = os.urandom(16)
        # Use PBKDF2 with HMAC-SHA256, 100,000 iterations (Secure & standard)
        db_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        # Store salt and hash together as a hex string
        return f"{salt.hex()}:{db_hash.hex()}"

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        try:
            salt_hex, hash_hex = hashed_password.split(":")
            salt = bytes.fromhex(salt_hex)
            original_hash = bytes.fromhex(hash_hex)
            # Re-hash the plain password with the stored salt
            new_hash = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, 100000)
            return new_hash == original_hash
        except Exception:
            return False