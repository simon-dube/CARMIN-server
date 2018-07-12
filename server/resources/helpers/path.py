import os
import json
import tarfile
import tempfile
import zipfile
import mimetypes
import hashlib
import base64
import datalad
from typing import List
from binascii import Error
from flask import Response, make_response, send_file
from server import app
from server.common.utils import marshal
from server.resources.models.upload_data import UploadDataSchema
from server.resources.models.boolean_response import BooleanResponse
from server.resources.models.upload_data import UploadData
from server.resources.models.error_code_and_message import ErrorCodeAndMessage
from server.database.models.user import User, Role
from server.resources.models.path import Path, PathSchema
from server.resources.models.path_md5 import PathMD5
from server.common.error_codes_and_messages import (
    ErrorCodeAndMessageMarshaller, ErrorCodeAndMessageFormatter, ErrorCodeAndMessageAdditionalDetails,
    PATH_IS_DIRECTORY, INVALID_PATH, PATH_EXISTS, INVALID_MODEL_PROVIDED,
    NOT_AN_ARCHIVE, INVALID_BASE_64, UNEXPECTED_ERROR, LIST_ACTION_ON_FILE,
    MD5_ON_DIR, INVALID_ACTION)


def get_helper(action: str, requested_data_path: str, complete_path: str) -> (any, int):
    if action == 'content':
        return get_content(requested_data_path), None
    elif action == 'properties':
        path = Path.object_from_pathname(requested_data_path)
        return marshal(path), None
    elif action == 'exists':
        exists = path_exists(requested_data_path)
        return marshal(BooleanResponse(exists)), None
    elif action == 'list':
        if not os.path.isdir(requested_data_path):
            return marshal(LIST_ACTION_ON_FILE), 400
        directory_list = get_path_list(complete_path)
        return marshal(directory_list), None
    elif action == 'md5':
        if os.path.isdir(requested_data_path):
            return marshal(MD5_ON_DIR), 400
        md5 = generate_md5(requested_data_path)
        return marshal(md5), None
    else:
        return marshal(INVALID_ACTION), 400


def put_helper_application_carmin_json(data, requested_data_path: str, complete_path: str) -> (any, int):
    # Request data contains base64 encoding of file or archive
    model, error = UploadDataSchema().load(data or dict())

    if error:
        return ErrorCodeAndMessageAdditionalDetails(
            INVALID_MODEL_PROVIDED, error), 400
    if model.upload_type == "File":
        if os.path.isdir(requested_data_path):
            error = ErrorCodeAndMessageFormatter(
                PATH_IS_DIRECTORY, complete_path)
            return error, 400
        path, error = upload_file(model, requested_data_path)
        if error:
            return error, 400
        return path, 201

    if model.upload_type == "Archive":
        path, error = upload_archive(model, requested_data_path)
        if error:
            return error, 400
        return path, 201

    return None, None


def put_helper_raw_data(data, requested_data_path: str) -> (any, int):
    try:
        with open(requested_data_path, 'w') as f:
            f.write(data.decode('utf-8', errors='ignore'))
        return Path.object_from_pathname(requested_data_path), 201
    except OSError:
        return INVALID_PATH, 400


def put_helper_no_data(requested_data_path: str) -> (any, int, any):
    path, error = create_directory(requested_data_path)
    if error:
        return error, 400, None
    file_location_header = {'Location': path.platform_path}
    # string_path = json.dumps(PathSchema().dump(path).data)
    return path, 201, file_location_header


def get_content(complete_path: str) -> Response:
    """Helper function for the `content` action used in the GET method."""
    if os.path.isdir(complete_path):
        tarball = make_tarball(complete_path)
        response = send_file(
            tarball, mimetype="application/gzip", as_attachment=True)
        os.remove(tarball)
        return response
    mimetype, _ = mimetypes.guess_type(complete_path)
    response = send_file(complete_path)
    if mimetype:
        response.mimetype = mimetype
    return response


def get_path_list(relative_path_to_resource: str) -> List[Path]:
    """Helper function for the `list` action used in the GET method."""
    result_list = []
    absolute_path_to_resource = make_absolute(relative_path_to_resource)
    directory_list = os.listdir(absolute_path_to_resource)
    for f_d in directory_list:
        if not f_d.startswith('.'):
            result_list.append(
                Path.object_from_pathname(
                    os.path.join(absolute_path_to_resource, f_d)))
    return result_list


def is_safe_path(path: str, follow_symlinks: bool = True) -> bool:
    """Checks `completePath` to ensure that it lives inside the exposed /data
    directory.
    """
    base_dir = app.config['DATA_DIRECTORY']

    if follow_symlinks and not get_data_dataset():
        return os.path.realpath(path).startswith(base_dir)
    return os.path.abspath(path).startswith(base_dir)


def is_data_accessible(path: str, user: User) -> bool:
    if user.role == Role.admin:
        return True

    if not get_data_dataset():
        return os.path.realpath(path).startswith(
            get_user_data_directory(user.username))
    else:
        return os.path.abspath(path).startswith(
            get_user_data_directory(user.username))


def is_safe_for_get(requested_path: str, user: User) -> bool:
    return (is_safe_path(requested_path)
            and is_data_accessible(requested_path, user))


def is_safe_for_put(requested_path: str, user: User) -> bool:
    return (is_safe_path(requested_path)
            and is_data_accessible(requested_path, user)
            and not is_execution_dir(requested_path, user.username)
            and parent_dir_exists(requested_path))


def is_safe_for_delete(requested_path: str, user: User) -> bool:
    return (is_safe_for_put(requested_path, user)
            and not requested_path == get_user_data_directory(user.username))


def is_execution_dir(path: str, username: str) -> bool:
    user_execution_dir = os.path.join(
        get_user_data_directory(username), EXECUTIONS_DIRNAME)

    return os.path.realpath(path).startswith(user_execution_dir)


def get_user_data_directory(username: str) -> str:
    return os.path.join(app.config['DATA_DIRECTORY'], username)


def make_absolute(relative_path: str) -> str:
    data_path = app.config['DATA_DIRECTORY']

    return os.path.normpath(os.path.join(data_path, relative_path))


def upload_file(upload_data: UploadData,
                requested_file_path: str) -> (Path, ErrorCodeAndMessage):
    try:
        raw_content = base64.decodebytes(upload_data.base64_content.encode())
    except Error as e:
        return None, ErrorCodeAndMessageFormatter(INVALID_BASE_64, e)
    try:
        with open(requested_file_path, 'wb') as f:
            f.write(raw_content)
    except OSError:
        return None, UNEXPECTED_ERROR
    path = Path.object_from_pathname(requested_file_path)
    return path, None


def upload_archive(upload_data: UploadData,
                   requested_dir_path: str) -> (Path, ErrorCodeAndMessage):
    try:
        raw_content = base64.decodebytes(upload_data.base64_content.encode())
    except Error as e:
        return None, ErrorCodeAndMessageFormatter(INVALID_BASE_64, e)
    file_name = '{}.zip'.format(requested_dir_path)

    try:
        with open(file_name, 'wb') as f:
            f.write(raw_content)
    except OSError:
        return None, UNEXPECTED_ERROR
    try:
        with zipfile.ZipFile(file_name, mode='r') as zf:
            zf.extractall(path=requested_dir_path)
    except zipfile.BadZipFile as e:
        try:
            os.remove(file_name)
        except:
            pass
        return None, ErrorCodeAndMessageFormatter(NOT_AN_ARCHIVE, e)
    os.remove(file_name)
    path = Path.object_from_pathname(requested_dir_path)
    return path, None


def create_directory(requested_data_path: str, path_required: bool = True
                     ) -> (Path, ErrorCodeAndMessage):
    try:
        os.mkdir(requested_data_path)
        # path_required allows callers to use this helper function outside of request calls as Path.object_from_pathname uses the Flask request
        if path_required:
            return Path.object_from_pathname(requested_data_path), None
        else:
            return None, None
    except FileExistsError:
        return None, PATH_EXISTS


def generate_md5(data_path: str) -> PathMD5:
    hash_md5 = hashlib.md5()
    with open(data_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return PathMD5(hash_md5.hexdigest())


def make_tarball(data_path: str) -> tarfile:
    temp_file = os.path.join(tempfile.gettempdir(),
                             os.path.basename(data_path)) + ".tar.gz"
    with tarfile.open(temp_file, mode='w:gz') as archive:
        archive.add(data_path, arcname=os.path.basename(data_path))
    return temp_file


def parent_dir_exists(requested_data_path: str) -> bool:
    parent_directory = os.path.abspath(
        os.path.join(requested_data_path, os.pardir))
    return path_exists(parent_directory)


def platform_path_exists(url_root: str, platform_path: str) -> (bool, str):
    path_url = '{}path/'.format(url_root)

    if isinstance(platform_path, list):
        for path in platform_path:
            exists = path_exists(
                os.path.join(app.config['DATA_DIRECTORY'],
                             path[len(path_url):]))
            if not exists:
                return False, path
        return True, None
    return path_exists(
        os.path.join(app.config['DATA_DIRECTORY'],
                     platform_path[len(path_url):])), platform_path


def path_from_data_dir(url_root: str, platform_path: str) -> str:
    path_url = '{}path/'.format(url_root)
    return os.path.join(app.config['DATA_DIRECTORY'],
                        platform_path[len(path_url):])


def path_exists(complete_path: str) -> bool:
    dataset = get_data_dataset()
    if not dataset:
        return os.path.exists(complete_path)

    # We are using a dataset
    # As symlinks may very probably be broken as we don't hold all the data,
    # we will simply look at if a symlink, a file (if the file is not saved) or a folder
    # exists at this path.
    return os.path.exists(complete_path) or os.path.islink(complete_path)


from .executions import EXECUTIONS_DIRNAME
from server.common.datalad import get_data_dataset
