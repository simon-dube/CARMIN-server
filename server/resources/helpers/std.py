from flask import Response
from server.database import db
from server.common.utils import marshal
from server.common.error_codes_and_messages import (
    ErrorCodeAndMessageFormatter, EXECUTION_NOT_FOUND, UNAUTHORIZED, UNEXPECTED_ERROR)
from server.database.queries.executions import get_execution
from server.resources.helpers.executions import (
    get_execution_as_model, get_std_file, STDERR_FILENAME, is_safe_for_get, std_file_path)
from server.resources.decorators import login_required
from server.datalad_f.utils import (
    get_data_dataset, datalad_get)


def std_file_resource(user, execution_identifier, path_to_file):
    execution_db = get_execution(execution_identifier, db.session)
    if not execution_db:
        error = ErrorCodeAndMessageFormatter(EXECUTION_NOT_FOUND,
                                             execution_identifier)
        return marshal(error), 400

    if not is_safe_for_get(user, execution_db):
        return marshal(UNAUTHORIZED), 400

    execution, error = get_execution_as_model(execution_db.creator_username,
                                              execution_db)
    if error:
        return marshal(error), 400

    # If using Datalad, first get the file
    dataset = get_data_dataset()
    if dataset:
        success = datalad_get(dataset, std_file_path(
            user.username, execution_identifier, path_to_file))
        dataset.close()
        if not success:
            return marshal(UNEXPECTED_ERROR), 400

    std, error = get_std_file(user.username, execution_identifier,
                              path_to_file)
    if error:
        return marshal(error), 400

    return Response(std, mimetype='text/plain')
