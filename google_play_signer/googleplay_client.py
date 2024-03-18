from io import BytesIO
from typing import Dict, List, Tuple

import httplib2
from google.oauth2.service_account import Credentials
from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload
from loguru import logger
from typing import IO
from typing import Union


def upload_app(
        service: Resource,
        package_name: str,
        aab: IO[bytes]
        ):
    edit_id = create_edit(service, package_name)
    upload_aab_file(service, package_name, aab, edit_id)
    set_track(service, package_name, edit_id)
    try:
        commit_edit(service, package_name, edit_id)
    except HttpError as e:
        logger.warning(f"Http Error in commit for {package_name}")
        if e.status_code != 400:
            raise e
            return

    logger.info(f"Uploaded {package_name} aab")


def get_service(user_secrets: dict) -> Resource:
    credentials = Credentials.from_service_account_info(
            user_secrets,
            scopes=['https://www.googleapis.com/auth/androidpublisher']
            )
    http = httplib2.Http(timeout=120)
    authed_http = AuthorizedHttp(credentials, http)
    return build('androidpublisher', 'v3', http=authed_http)


def download_standalone_apks(
        service: Resource,
        package_name: str,
        version_code: int,
        generated_apks: Dict[str, dict]
        ) -> List[Tuple[int, BytesIO]]:
    return [
            (
                s['variantId'],
                download_apk(
                    service, package_name, s['downloadId'], version_code)
            ) for s in generated_apks['generatedStandaloneApks']
            ]


def download_universal_apk(
        service: Resource,
        package_name: str,
        version_code: int,
        generated_apks: Dict[str, dict]
        ) -> BytesIO:
    return download_apk(
            service,
            package_name,
            generated_apks['generatedUniversalApk']['downloadId'],
            version_code)


def extract_apk_descriptions(generated_apks: List[Dict]) -> List[Dict]:
    """Returns the apk_descriptions set (describes the function of each split) from the generated_apks"""
    apk_descriptions = []
    try:
        for variant in generated_apks['targetingInfo']['variant']:
                for apk_set in variant.get('apkSet'):
                    apk_descriptions.extend(apk_set.get('apkDescription', []))
    except:
        pass
    return apk_descriptions


def get_density_ids(apk_descriptions: List[Dict], desired_targetings: List[str]) -> List[str]: 
    """Returns the split_ids that target one of the desired_targetings"""
    filtered_list = []
    for apk_description in apk_descriptions:
        try:
            targeting = apk_description.get('targeting')
            screen_density = targeting['screenDensityTargeting']['value'][0]
            if screen_density['densityAlias'] in desired_targetings:
                filtered_list.append(apk_description['splitApkMetadata']['splitId'])
        except:
            continue
    return filtered_list


def get_language_ids(apk_descriptions: List[Dict], desired_targetings: List[str]) -> List[str]: 
    """Returns the split_ids that target one of the desired_targetings"""
    filtered_list = []
    for apk_description in apk_descriptions:
        try:
            targeting = apk_description.get('targeting')
            language_targeting = targeting.get('languageTargeting', {})
            language_iso_code = language_targeting.get('value', [])[0]
            if language_iso_code in desired_targetings:
                filtered_list.append(apk_description['splitApkMetadata']['splitId'])
        except:
            continue
    return filtered_list


def get_download_ids(generated_apks: List[dict], split_ids: List[str]) -> List[str]:
    """Returns the download_ids that correspond to the split_ids"""
    return [apk['downloadId'] for apk in generated_apks.get('generatedSplitApks', [])
            if apk.get('splitId') in split_ids]


def download_splits(
        service: Resource,
        package_name: str,
        version_code: int,
        generated_apks: Dict[str, Union[list[dict], dict]]
        ) -> Dict[int, List[Tuple[str, BytesIO]]]:
    generated_splits: list[dict] = generated_apks['generatedSlitApks']
    variant_ids = set(split['variantId'] for split in generated_splits)
    apks = [
            [split for split in generated_splits
             if split['variantId'] == variant
             ] for variant in variant_ids]
    splits = {}
    for variant in apks:
        variant_id = variant[0]["variantId"]
        try:
            variant_apks = []
            for split in variant:
                apk = download_apk(
                        service, package_name, split['downloadId'], version_code
                        )
                name = split.get('splitId', 'base')
                variant_apks.append((name, apk))
            splits[variant_id] = variant_apks
        except Exception as e:
            logger.error(f'Could not download variant {variant_id}', e)

    return splits


def commit_edit(
        service: Resource,
        package_name: str,
        edit_id: int
        ):
    service.edits().commit(
            packageName=package_name,
            editId=edit_id
            ).execute()


def upload_aab_file(
        service: Resource,
        package_name: str,
        aab: IO[bytes],
        edit_id: int
        ):
    media = MediaIoBaseUpload(aab, mimetype='application/octet-stream')
    service.edits().bundles().upload(
            editId=edit_id,
            packageName=package_name,
            media_body=media
            ).execute()


def list_generated_apks(
        service: Resource,
        package_name: str,
        version_code: int
        ):
    generated_apks = service.generatedapks().list(
            packageName=package_name,
            versionCode=version_code
            )
    data = generated_apks.execute()
    return data['generatedApks'][0]


def download_apk(
        service: Resource,
        package_name: str,
        download_id: str,
        version_code: int
        ) -> BytesIO:
    return service.generatedapks().download(
            packageName=package_name,
            versionCode=version_code,
            downloadId=download_id,
            alt='media',
            ).execute()


def create_edit(service: Resource, package_name: str) -> int:
    edit_request = service.edits().insert(packageName=package_name)
    edit_response = edit_request.execute()
    return edit_response['id']


def set_track(service: Resource, package_name: str, edit_id: int):
    service.edits().tracks().update(
            editId=edit_id,
            packageName=package_name,
            track='internal'
            ).execute()
