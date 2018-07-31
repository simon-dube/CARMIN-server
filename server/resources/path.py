import os
import json
import shutil
from flask_restful import Resource, request
from flask import Response, make_response
from server.datalad_f.utils import (
    get_data_dataset, datalad_get,
    datalad_save, datalad_remove, datalad_get_unlock_if_exists, datalad_unlock)
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
                           delete_helper_local, get_user_data_directory)


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

        # Datalad get content
        dataset = get_data_dataset()
        success_unlock = None
        if dataset and action != 'exists':
            success = datalad_get(dataset, requested_data_path)
            # In this case, we will create an archive to send back to the user.
            # As we do not want to follow any symlink (as a user may have uploaded one manually),
            # instead of derefenrencing the files for the archive (follow symlinks to archive the actual file)
            # we will instead unlock the related files for the time of the archive creation
            if action == "content" and os.path.isdir(requested_data_path):
                success_unlock = datalad_unlock(dataset, requested_data_path)
                if not success_unlock:
                    datalad_save(dataset, requested_data_path)
            if not success:
                return marshal(UNEXPECTED_ERROR), 500

        content, code = get_helper(
            action, requested_data_path, complete_path)

        # If we unlocked some files for an archive result, we save them back.
        if dataset and success_unlock and isinstance(success_unlock, list):
            for file_unlocked in success_unlock:
                datalad_save(dataset, file_unlocked["path"])

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

        # If using datalad, will get and unlock the files if they exist
        dataset = get_data_dataset()
        success = datalad_get_unlock_if_exists(dataset, requested_data_path)
        # TODO: Validate what type of error we want here (datalad info hidden?)
        if not success:
            return marshal(UNEXPECTED_ERROR), 500

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
            if not isinstance(content, ErrorCodeAndMessage):
                # If using datalad, save content and publish
                if dataset and data:
                    success = datalad_save(dataset, requested_data_path)
                    if not success:
                        return marshal(UNEXPECTED_ERROR), 500
                    # TODO: Send WARNING if success is false
                    # TODO: Send ERROR if error is not None
                    if success:
                        dataset.close()

            return marshal(content), code, custom_header

        return marshal(INVALID_REQUEST), 400

    @login_required
    @datalad_update
    def delete(self, user, complete_path: str=''):
        requested_data_path = make_absolute(complete_path)

        if not is_safe_for_delete(requested_data_path, user):
            return marshal(UNAUTHORIZED), 403

        if not path_exists(requested_data_path):
            return marshal(PATH_DOES_NOT_EXIST), 400

        dataset = get_data_dataset()

        content, code = None, None
        if dataset:
            success = datalad_remove(dataset, requested_data_path)
            if not success:
                return marshal(UNEXPECTED_ERROR), 500
            # TODO: Send WARNING if success is false
            # TODO: Send ERROR if error is not None
            if success:
                dataset.close()
        else:
            content, code = delete_helper_local(requested_data_path)

        return (marshal(content), code) if content and code else Response(status=204)
