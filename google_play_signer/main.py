import json
import os
import tempfile
from multiprocessing.pool import ThreadPool
from typing import Dict

from flask import Flask
from flask_restx import Api, Resource, reqparse
from loguru import logger
from werkzeug.datastructures import FileStorage

from googleapiclient.errors import HttpError

from google_play_signer.auth import requires_authorization, build_jwt
from google_play_signer.catappult_client import upload_apk
from google_play_signer.googleplay_client import (download_universal_apk,
                                                  get_service,
                                                  get_download_ids,
                                                  get_density_ids,
                                                  get_language_ids,
                                                  extract_apk_descriptions,
                                                  download_apk,
                                                  list_generated_apks,
                                                  upload_app)
from google_play_signer.catappult_client import send_notification
from google_play_signer.config import DPI_SPLITS, LANGUAGE_SPLITS


app = Flask(__name__)
api = Api(app, version='1.0', title='Google Play Signer', 
          description='Google Play Signer API uploads bundles with the upload signature and gets the signed APK by Google Play. 🚀')
pool = ThreadPool(processes=4)


@api.route('/healthcheck')
class Healthcheck(Resource):
    def get(self):
        return "OK"


@api.route('/app/<string:cauid>/<string:package_name>/<int:version_code>')
class App(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument(
            'file', location='files', type=FileStorage, required=True)
    parser.add_argument(
            'user_credentials', location='form', type=str, required=True)
    parser.add_argument(
            'Authorization', location='headers', type=str, required=True
            )

    @api.expect(parser)
    @requires_authorization
    def post(self, cauid: str, package_name: str, version_code: int):
        args = App.parser.parse_args()
        file: FileStorage = args['file']
        aab = write_aab_tmpfs(file)
        user_credentials = json.loads(args['user_credentials'])

        pool.apply_async(
                sign_app,
                (
                    user_credentials,
                    package_name,
                    aab,
                    version_code,
                    cauid
                    )
                )
        return {'msg': 'Started aab upload'}


def write_aab_tmpfs(aab: FileStorage) -> str:
    with tempfile.NamedTemporaryFile('wb', delete=False) as file:
        file.write(aab.stream.read())
        return file.name


def sign_app(
        user_secrets: Dict[str, str],
        package_name: str,
        file_path: str,
        version_code: int,
        cauid: str,
        ):
    logger.info(f"Signing {package_name} aab with version code {version_code}")
    apptech_jwt = build_jwt()
    try:
        service = get_service(user_secrets)
        with open(file_path, 'rb') as aab:
            upload_app(service, package_name, aab)
        os.remove(file_path)
        logger.info(f'Uploaded and removed {package_name} aab')

        generated_apks = list_generated_apks(service, package_name, version_code)
        apks_descriptions = extract_apk_descriptions(generated_apks=generated_apks)
        density_ids = get_density_ids(apk_descriptions=apks_descriptions, desired_targetings=DPI_SPLITS)
        language_ids = get_language_ids(apk_descriptions=apks_descriptions, desired_targetings=LANGUAGE_SPLITS)

        download_ids = get_download_ids(generated_apks=generated_apks, split_ids=language_ids + density_ids)

        logger.info(download_ids)

        for download_id in download_ids:
            split_apk = download_apk(service, package_name, download_id, version_code)
            upload_apk(split_apk, cauid, apptech_jwt)

        universal_apk = download_universal_apk(
                service, package_name, version_code, generated_apks)
        upload_apk(universal_apk, cauid, apptech_jwt)
    except HttpError as e:
        logger.warning(
                f"Google Play Http Client error for {package_name}:"
                f" {e.status_code} - {e.error_details}")
        send_notification(
                {
                    'cauid': cauid,
                    'package_name': package_name,
                    'version_code': version_code,
                    'msg': e.error_details
                }, apptech_jwt
                )
    except Exception as e:
        logger.exception("Got error while signing and uploading app", e)