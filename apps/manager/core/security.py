import time
import base64
import hashlib
import logging
from core.config import settings

logger = logging.getLogger("Security")

def sign_stream_link(file_id: str, client_ip: str) -> str:
    """
    Shadow Logic: Generates an Nginx Secure Link hash.
    Syncs with Nginx $remote_addr for identity verification.
    """
    expiry = int(time.time()) + (4 * 3600)
    secret = settings.SECURE_LINK_SECRET
    path = f"/stream/{file_id}"
    
    # We must match Nginx exactly: Expiry + URI + ClientIP + " " + Secret
    sign_string = f"{expiry}{path}{client_ip} {secret}"
    
    hash_obj = hashlib.md5(sign_string.encode('utf-8'))
    token = base64.urlsafe_b64encode(hash_obj.digest()).decode('utf-8').replace('=', '')

    # return f"md5={token}&expires={expiry}" # Nginx standard args
    
    logger.info(f"Signed path {path} for IP {client_ip} [Hash snippet: {token[:5]}]")
    return f"token={token}&expires={expiry}"
