import secrets

def generate_random_token(length: int = 32) -> str:
    return secrets.token_hex(length)