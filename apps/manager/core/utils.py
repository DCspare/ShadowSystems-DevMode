import string
import random

def generate_short_id(length: int = 7) -> str:
    """
    Shadow Logic: Generates a URL-friendly unique identifier (Base62).
    Used as 'short_id' in the library schema.
    """
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))
