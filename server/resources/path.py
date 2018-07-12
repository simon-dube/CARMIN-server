import os
import json
import shutil
from flask_restful import Resource, request
from flask import Response, make_response
from server.common.datalad import (
    get_data_dataset, datalad_get, datalad_drop,
    datalad_save_and_publish, datalad_remove_and_publish)
from server.common.utils import marshal
from server.common.error_codes_and_messages import (
    ErrorCodeAndMessageFormatter, ErrorCodeAndMessageAdditionalDetails,
    INVALID_MODEL_PROVIDED, UNAUTHORIZED, INVALID_PATH, INVALID_ACTION,
    MD5_ON_DIR, LIST_ACTION_ON_FILE, ACTION_REQUIRED, UNEXPECTED_ERROR,
    PATH_IS_DIRECTORY, INVALID_REQUEST, PATH_DOES_NOT_EXIST)
from .models.error_code_and_message import ErrorCodeAndMessage
from .decorators import login_required, unmarshal_request, datalad_update
from .helpers.path import (is_safe_for_delete, upload_file, upload_archive,
                           create_directory, is_safe_for_put,
                           is_safe_for_get, make_absolute,
                           path_exists, get_helper,
                           put_helper_application_carmin_json,
                           put_helper_raw_data, put_helper_no_data,
                           delete_helper_local)


class Path(Resource):
    """Allow file downloading and give access to multiple information about a
    specific path. The response format and content depends on the mandatory action
    query parameter (see the parameter description).
    Basically, the `content` action downloads the raw file, and the other actions
    return various informations in JSON.
    """

    @login_required
    @datalad_update
    def get(self, user, complete_path: str = ''):
        """The @marshal_response() decorator is not used since this method can return
        a number of different Schemas or binary content. Use `response(Model)`
        instead, where `Model` is the object to be returned.
        """

        action = request.args.get('action', default='', type=str).lower()
        requested_data_path = make_absolute(complete_path)

        if not is_safe_for_get(requested_data_path, user):
            return marshal(INVALID_PATH), 401

        if not path_exists(requested_data_path) and action != 'exists':
            return marshal(PATH_DOES_NOT_EXIST), 401

        if not action:
            return marshal(ACTION_REQUIRED), 400

        # Datalad overhead
        dataset = get_data_dataset()
        if dataset:
            succes = datalad_get(dataset, requested_data_path)
            if not succes:
                return marshal(UNEXPECTED_ERROR), 500
        # END Datalad overhead

        content, code = get_helper(
            action, requested_data_path, complete_path)

        # Datalad overhead
        if dataset:
            succes = datalad_drop(dataset, requested_data_path)
            # if not succes:
            #     return marshal(UNEXPECTED_ERROR)
        # END Datalad overhead

        if not isinstance(content, Response):
            content = marshal(content)
        if code:
            return content, code
        return content

    @login_required
    @datalad_update
    def put(self, user, complete_path: str=''):
        data = request.data
        requested_data_path = make_absolute(complete_path)

        if not is_safe_for_put(requested_data_path, user):
            return marshal(INVALID_PATH), 401

        content, code, custom_header = None, None, None
        if request.headers.get(
                'Content-Type',
                default='').lower() == 'application/carmin+json':
            # Request data contains base64 encoding of file or archive
            data = request.get_json(force=True, silent=True)
            content, code = put_helper_application_carmin_json(
                data, requested_data_path, complete_path)

        elif data:
            # Content-Type is not 'application/carmin+json',
            # request data is taken as raw text
            content, code = put_helper_raw_data(data, requested_data_path)
        elif not data:
            content, code, custom_header = put_helper_no_data(
                requested_data_path)

        if content:
            # Datalad overhead
            if not isinstance(content, ErrorCodeAndMessage):
                dataset = get_data_dataset()
                if dataset:
                    succes = datalad_save_and_publish(
                        dataset, requested_data_path)
                    if not succes:
                        return marshal(UNEXPECTED_ERROR), 500
                    datalad_drop(dataset, requested_data_path)

            return marshal(content), code, custom_header

        return marshal(INVALID_REQUEST), 400

    @login_required
    def delete(self, user, complete_path: str=''):
        requested_data_path = make_absolute(complete_path)

        if not is_safe_for_delete(requested_data_path, user):
            return marshal(UNAUTHORIZED), 403

        if not path_exists(requested_data_path):
            return marshal(PATH_DOES_NOT_EXIST), 400

        dataset = get_data_dataset()

        content, code = None, None
        if not dataset:
            content, code = delete_helper_local(requested_data_path)
        else:
            success, error = datalad_remove_and_publish(
                dataset, requested_data_path)
            if not success:
                return marshal(UNEXPECTED_ERROR), 500

        return (marshal(content), code) if content and code else Response(status=204)
