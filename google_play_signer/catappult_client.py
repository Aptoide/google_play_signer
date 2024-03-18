from io import BytesIO
from google_play_signer.config import CATAPPULT_UPLOADER,\
        CATAPPULT_NOTIFICATIONS
import requests
from loguru import logger


def upload_apk(apk: BytesIO, cauid: str, token: str):
    url = CATAPPULT_UPLOADER.format(cauid)
    headers = {'Authorization': f'Bearer {token}'}
    files = {'files[0]': ('universal.apk', apk)}
    data = {'forceSignature': "true"}
    r = requests.post(url, headers=headers, files=files, data=data)
    if r.status_code != 200:
        logger.error(f"Error uploading to catappult {cauid} apk:\n"
                     f"{r.status_code} - {r.text}")
        return
    logger.info(f"Uploaded app to catappult for cauid: {cauid}")


def send_notification(data: dict, token: str):
    headers = {'Authorization': f'Bearer {token}'}
    requests.post(CATAPPULT_NOTIFICATIONS, data=data, headers=headers)
