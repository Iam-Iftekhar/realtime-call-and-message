import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

from app.core.config import settings
from app.core.exceptions import AuthenticationError

# RFC 9106 Recommended Parameters: memory_cost=65536 KiB (64MB), time_cost=3, parallelism=4
pwd_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hash plaintext password using Argon2id."""
    return pwd_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against Argon2id hash."""
    try:
        return pwd_hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def generate_secure_token(nbytes: int = 32) -> str:
    """Generate cryptographically secure URL-safe random string."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """Compute SHA-256 hash of a token for secure database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# --- JWT Implementation (HMAC-SHA256) ---

def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _base64url_decode(data_str: str) -> bytes:
    padding = "=" * (4 - (len(data_str) % 4)) if len(data_str) % 4 != 0 else ""
    return base64.urlsafe_b64decode((data_str + padding).encode("utf-8"))


def create_access_token(
    subject: str,
    device_id: str,
    session_id: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    header = {"alg": settings.ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": subject,
        "dev": device_id,
        "sid": session_id,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "iss": "spectra-auth",
    }
    if extra_claims:
        payload.update(extra_claims)

    encoded_header = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")

    signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    encoded_signature = _base64url_encode(signature)

    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """Verify and decode a signed JWT access token."""
    parts = token.split(".")
    if len(parts) != 3:
        raise AuthenticationError(detail="Malformed JWT token structure")

    encoded_header, encoded_payload, encoded_signature = parts
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")

    expected_signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    provided_signature = _base64url_decode(encoded_signature)
    if not hmac.compare_digest(expected_signature, provided_signature):
        raise AuthenticationError(detail="Invalid JWT signature")

    try:
        payload = json.loads(_base64url_decode(encoded_payload).decode("utf-8"))
    except Exception as e:
        raise AuthenticationError(detail=f"Invalid JWT payload JSON: {str(e)}")

    now_ts = int(datetime.now(timezone.utc).timestamp())
    exp = payload.get("exp")
    if exp is None or now_ts > exp:
        raise AuthenticationError(detail="JWT token has expired", code="AUTH_TOKEN_EXPIRED")

    return payload


# --- Coturn TURN Ephemeral Credentials (RFC 7635) ---

def generate_coturn_credentials(user_id: str, ttl_seconds: Optional[int] = None) -> Dict[str, Any]:
    """Generate ephemeral STUN/TURN credentials using HMAC-SHA1 shared secret (RFC 7635)."""
    ttl = ttl_seconds or settings.COTURN_CREDENTIAL_TTL_SECONDS
    expiry_timestamp = int(time.time()) + ttl
    username = f"{expiry_timestamp}:{user_id}"

    # HMAC-SHA1 password computation
    key = settings.COTURN_STATIC_SECRET.encode("utf-8")
    mac = hmac.new(key, username.encode("utf-8"), hashlib.sha1)
    password = base64.b64encode(mac.digest()).decode("utf-8")

    host = settings.COTURN_HOST
    udp_port = settings.COTURN_UDP_PORT
    tls_port = settings.COTURN_TLS_PORT

    return {
        "ice_servers": [
            {
                "urls": f"stun:{host}:{udp_port}",
            },
            {
                "urls": [
                    f"turn:{host}:{udp_port}?transport=udp",
                    f"turn:{host}:{udp_port}?transport=tcp",
                    f"turns:{host}:{tls_port}?transport=tcp",
                ],
                "username": username,
                "credential": password,
            },
        ],
        "ttl": ttl,
        "expires_at": expiry_timestamp,
    }


# --- Ed25519 Cryptographic Signature Verification ---

def verify_ed25519_signature(public_key_b64: str, message_bytes: bytes, signature_b64: str) -> bool:
    """Verify an Ed25519 signature over message bytes using a base64-encoded public key."""
    try:
        pub_bytes = base64.b64decode(public_key_b64)
        sig_bytes = base64.b64decode(signature_b64)
        if len(pub_bytes) != 32:
            return False
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
        public_key.verify(sig_bytes, message_bytes)
        return True
    except (InvalidSignature, ValueError, Exception):
        return False
