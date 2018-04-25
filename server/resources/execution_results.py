from flask_restful import Resource
from server.database import db
from server.database.queries.executions import get_execution
from server.database.models.execution import Execution as ExecutionDB, ExecutionStatus
from server.resources.models.execution import EXECUTION_COMPLETED_STATUSES
from server.resources.decorators import login_required, marshal_response
from server.common.error_codes_and_messages import (
    ErrorCodeAndMessageFormatter, EXECUTION_NOT_FOUND, UNAUTHORIZED,
    CANNOT_GET_RESULT_NOT_COMPLETED_EXECUTION)
from server.resources.helpers.execution_results import get_output_files
from server.resources.models.path import PathSchema


class ExecutionResults(Resource):
    @login_required
    @marshal_response(PathSchema(many=True))
    def get(self, user, execution_identifier):
        execution_db = get_execution(execution_identifier, db.session)
        if not execution_db:
            return ErrorCodeAndMessageFormatter(EXECUTION_NOT_FOUND,
                                                execution_identifier)
        if execution_db.creator_username != user.username:
            return UNAUTHORIZED

        if execution_db.status not in EXECUTION_COMPLETED_STATUSES:
            return ErrorCodeAndMessageFormatter(
                CANNOT_GET_RESULT_NOT_COMPLETED_EXECUTION, execution_db.status)

        # We now know the execution has completed and can retrieve the output files
        output_files = get_output_files(user.username, execution_identifier)
        return output_files
