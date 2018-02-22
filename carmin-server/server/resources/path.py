import os
import shutil
import mimetypes
from typing import List
from flask_restful import Resource, request
from flask import send_file, Response
from server import app
from server.common.error_codes_and_messages import (
    ErrorCodeAndMessageMarshaller, UNAUTHORIZED, INVALID_PATH, INVALID_ACTION,
    MD5_ON_DIR, LIST_ACTION_ON_FILE, INVALID_UPLOAD_TYPE, ACTION_REQUIRED)
from .models.upload_data import UploadDataSchema
from .models.path_md5 import PathMD5Schema
from .models.boolean_response import BooleanResponse, BooleanResponseSchema
from .models.path import Path as PathModel
from .models.path import PathSchema
from .decorators import login_required, marshal_request
from .helpers.path import (is_safe_path, is_root, upload_file, upload_archive,
                           create_directory, generate_md5, make_tarball,
                           parent_dir_exists)


class Path(Resource):
    """Allow file downloading and give access to multiple information about a
    specific path. The response format and content depends on the mandatory action
    query parameter (see the parameter description).
    Basically, the `content` action downloads the raw file, and the other actions
    return various informations in JSON.
    """

    def get(self, complete_path: str = ''):
        """The @marshal_response() decorator is not used since this method can return
        a number of different Schemas or binary content. Use `return schema.dump()`
        instead, where `schema` is the Schema of the class to be returned.
        """

        data_path = app.config['DATA_DIRECTORY']

        action = request.args.get('action')
        if action:
            action = action.lower()

        full_absolute_path = os.path.normpath(
            os.path.join(data_path, complete_path))

        if not is_safe_path(full_absolute_path):
            return ErrorCodeAndMessageMarshaller(UNAUTHORIZED), 403
        if not os.path.exists(full_absolute_path) and action != 'exists':
            return ErrorCodeAndMessageMarshaller(INVALID_PATH), 401

        if not action:
            return ErrorCodeAndMessageMarshaller(ACTION_REQUIRED), 400
        if action == 'content':
            return get_content(full_absolute_path)
        elif action == 'properties':
            path = PathModel.object_from_pathname(full_absolute_path)
            return PathSchema().dump(path)
        elif action == 'exists':
            path_exists = os.path.exists(full_absolute_path)
            return BooleanResponseSchema().dump(BooleanResponse(path_exists))
        elif action == 'list':
            if not os.path.isdir(full_absolute_path):
                return ErrorCodeAndMessageMarshaller(LIST_ACTION_ON_FILE)
            directory_list = get_path_list(data_path, complete_path)
            return PathSchema(many=True).dump(directory_list)
        elif action == 'md5':
            if os.path.isdir(full_absolute_path):
                return ErrorCodeAndMessageMarshaller(MD5_ON_DIR), 400
            md5 = generate_md5(full_absolute_path)
            return PathMD5Schema().dump(md5)
        else:
            return ErrorCodeAndMessageMarshaller(INVALID_ACTION), 400

    # TODO: Uncomment once the decorator accepts allow_none param
    #  @marshal_request(UploadDataSchema())
    def put(self, complete_path: str = ''):
        data_path = app.config['DATA_DIRECTORY']
        requested_data_path = os.path.normpath(
            os.path.join(data_path, complete_path))

        if not is_safe_path(requested_data_path):
            return ErrorCodeAndMessageMarshaller(UNAUTHORIZED), 403
        if not parent_dir_exists(requested_data_path):
            return ErrorCodeAndMessageMarshaller(INVALID_PATH), 401
        upload_data = request.get_json(force=True, silent=True)

        if not upload_data:
            return create_directory(requested_data_path)

        if upload_data["type"] == "File":
            upload_data = UploadDataSchema().load(upload_data).data
            return upload_file(upload_data, requested_data_path)
        elif upload_data["type"] == "Archive":
            upload_data = UploadDataSchema().load(upload_data).data
            return upload_archive(upload_data, requested_data_path)
        else:
            return ErrorCodeAndMessageMarshaller(INVALID_UPLOAD_TYPE), 400

    def delete(self, complete_path: str = ''):
        data_path = app.config['DATA_DIRECTORY']
        requested_data_path = os.path.normpath(
            os.path.join(data_path, complete_path))

        if is_root(
                requested_data_path) or not is_safe_path(requested_data_path):
            return ErrorCodeAndMessageMarshaller(UNAUTHORIZED), 403

        if os.path.isdir(requested_data_path):
            try:
                shutil.rmtree(requested_data_path)
            except FileNotFoundError:
                return ErrorCodeAndMessageMarshaller(INVALID_PATH), 400
        else:
            try:
                os.remove(requested_data_path)
            except FileNotFoundError:
                return ErrorCodeAndMessageMarshaller(INVALID_PATH), 400
        return Response(status=204)


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


def get_path_list(platform_data_path: str,
                  relative_path_to_resource: str) -> List[Path]:
    """Helper function for the `list` action used in the GET method."""
    result_list = []
    absolute_path_to_resource = os.path.join(platform_data_path,
                                             relative_path_to_resource)
    directory_list = os.listdir(absolute_path_to_resource)
    for f_d in directory_list:
        if not f_d.startswith('.'):
            result_list.append(
                PathModel.object_from_pathname(
                    os.path.join(absolute_path_to_resource, f_d)))
    return result_list
