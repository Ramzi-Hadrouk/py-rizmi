"""Central application configuration."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Key paths ---
KEYS_DIR = BASE_DIR / "keys"
PRIVATE_KEY_PATH = KEYS_DIR / "private_key.pem"
PUBLIC_KEY_PATH = KEYS_DIR / "public_key.pem"

# --- License defaults ---
DEFAULT_EXPIRATION_DAYS = 365
DEFAULT_GRACE_DAYS = 14
DEFAULT_MAX_CLIENTS = 10
DEFAULT_MODE = "offline"

# --- JWT ---
JWT_ALGORITHM = "RS256"
