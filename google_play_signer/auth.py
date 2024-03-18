from flask import request
import requests
from jose import JWTError, jwt
from loguru import logger
from werkzeug.exceptions import BadRequest, Unauthorized

from google_play_signer.config import (JWT_KEYS, APPTECH_PRIVATE_KEY,
                                       APPTECH_ISSUER)
from datetime import datetime
from google_play_signer.config import CATAPPULT_VERIFY_TOKEN


def requires_authorization(func):
    def f(*args, **kwargs):
        auth = request.headers['Authorization']
        auth = auth.split(' ')
        if len(auth) != 2 or auth[0] != 'Bearer':
            raise BadRequest("Authorizations must be in form Bearer Token")

        token = auth[1]
        if catappult_authorization(token):
            return func(*args, **kwargs)

        if not jwt_authorization(token):
            raise Unauthorized()
        return func(*args, **kwargs)
    return f


def jwt_authorization(token: str) -> bool:
    try:
        iss = jwt.decode(
                token, "", options={'verify_signature': False}
                ).get('iss', '')
    except JWTError:
        raise BadRequest("Not a valid JWT format")

    key = JWT_KEYS.get(iss)
    if not key:
        raise Unauthorized("Issuer is not accepted")

    try:
        jwt.decode(token, key)
    except JWTError:
        return False
    return True


def catappult_authorization(token: str) -> bool:
    headers = {'Authorization': f"Bearer {token}"}
    r = requests.get(
            CATAPPULT_VERIFY_TOKEN, headers=headers
            )
    if r.status_code not in [200, 401]:
        logger.warning(f"Catappult api/session returned {r.status_code}")
    return r.status_code == 200


def build_jwt() -> str:
    iat = int(datetime.utcnow().timestamp())
    payload = {
            'iss': APPTECH_ISSUER,
            'iat': iat,
            'exp': iat + 7200,
            'version': 1
            }
    return jwt.encode(payload, APPTECH_PRIVATE_KEY, algorithm='RS512')
