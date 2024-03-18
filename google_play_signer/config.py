from jose import jwk
from pathlib import Path
import os
from loguru import logger

_path = Path(__file__).parent.resolve()


def load_pem_key(key: str) -> jwk.Key:
    return jwk.construct(key, 'RS512')
    

DPI_SPLITS = [
    "XXHDPI",
    "HDPI",
    "XXXHDPI",
    "MDPI",
    "XHDPI"
]

# Language splits are in ISO 639 standard
LANGUAGE_SPLITS = [
    "pt", # pt_BR
    "ru", # ru_RU
    "en", # en_US
    "in", # hi_IN
    "es", # es_ES
    "hi" # id_ID
]

CATAPPULT_ISSUER = 'catappult.io'
APPTECH_ISSUER = 'apptech.aptoide.com'

# --- Environment Variables --- 

UPLOADER_ENV = "UPLOADER"
CATTAPULT_WS_ENV = "CATTAPULT_WS"


# Dev Keys

CATTAPULT_ISSUER_PUBKEY_DEV_ENV = "CATTAPULT_ISSUER_PUBKEY_DEV"
CATTAPULT_ISSUER_PUBKEY_DEV = os.getenv(CATTAPULT_ISSUER_PUBKEY_DEV_ENV)

APPTECH_ISSUER_PUBKEY_DEV_ENV = "APPTECH_ISSER_PUBKEY_DEV"
APPTECH_ISSUER_PUBKEY_DEV = os.getenv(APPTECH_ISSUER_PUBKEY_DEV_ENV)

# Normal Keys

CATTAPULT_ISSUER_PUBKEY_ENV = "CATTAPULT_ISSUER_PUBKEY"
CATTAPULT_ISSUER_PUBKEY = os.getenv(CATTAPULT_ISSUER_PUBKEY_ENV)

APPTECH_ISSUER_PRIVKEY_ENV = "APPTECH_ISSER_PRIVKEY"
APPTECH_ISSUER_PRIVKEY = os.getenv(APPTECH_ISSUER_PRIVKEY_ENV)

APPTECH_ISSUER_PUBKEY_ENV = "APPTECH_ISSER_PUBKEY"
APPTECH_ISSUER_PUBKEY = os.getenv(APPTECH_ISSUER_PUBKEY_ENV)

logger.info(
        f"Starting in Environment: {os.getenv('ENVIRONMENT', 'PRODUCTION')}")

if os.getenv('ENVIRONMENT') == 'DEVELOPMENT':
    JWT_KEYS = {
            CATAPPULT_ISSUER: load_pem_key(CATTAPULT_ISSUER_PUBKEY_DEV),
            APPTECH_ISSUER: load_pem_key(APPTECH_ISSUER_PUBKEY_DEV)
            }
    APPTECH_PRIVATE_KEY = load_pem_key(APPTECH_ISSUER_PRIVKEY)
    UPLOADER = os.getenv(UPLOADER_ENV)
    CATAPPULT_WS = os.getenv(CATTAPULT_WS_ENV)
else:
    JWT_KEYS = {
            CATAPPULT_ISSUER: load_pem_key(CATTAPULT_ISSUER_PUBKEY),
            APPTECH_ISSUER: load_pem_key(APPTECH_ISSUER_PUBKEY)
            }
    APPTECH_PRIVATE_KEY = load_pem_key(APPTECH_ISSUER_PRIVKEY)
    UPLOADER = os.getenv(UPLOADER_ENV)
    CATAPPULT_WS = os.getenv(CATTAPULT_WS_ENV)


CATAPPULT_UPLOADER = UPLOADER + "api?accountUid={}"
CATAPPULT_NOTIFICATIONS = CATAPPULT_WS + "api/utils/applications/aabExtractor/notifications"
CATAPPULT_VERIFY_TOKEN = CATAPPULT_WS + "api/session/"