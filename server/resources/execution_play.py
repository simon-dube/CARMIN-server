from flask_restful import Resource, request
from jsonschema import ValidationError
from server.database import db
from server.database.queries.executions import get_execution
from server.resources.decorators import login_required, marshal_response
from server.database.models.execution import Execution, ExecutionStatus
from server.common.error_codes_and_messages import (
    ErrorCodeAndMessageFormatter, ErrorCodeAndMessageAdditionalDetails,
    EXECUTION_NOT_FOUND, UNAUTHORIZED, UNEXPECTED_ERROR, INVALID_INVOCATION,
    CANNOT_REPLAY_EXECUTION)
from server.resources.helpers.executions import (
    get_execution_as_model, create_absolute_path_inputs, get_descriptor_path)
from server.resources.helpers.execution import start_execution
from server.resources.models.descriptor.descriptor_abstract import Descriptor


class ExecutionPlay(Resource):
    @login_required
    @marshal_response()
    def put(self, user, execution_identifier):
        execution_db = get_execution(execution_identifier, db.session)
        if not execution_db:
            return ErrorCodeAndMessageFormatter(EXECUTION_NOT_FOUND,
                                                execution_identifier)
        if execution_db.creator_username != user.username:
            return UNAUTHORIZED

        if execution_db.status != ExecutionStatus.Initializing:
            return ErrorCodeAndMessageFormatter(CANNOT_REPLAY_EXECUTION,
                                                execution_db.status)

        execution, error = get_execution_as_model(user.username, execution_db)
        if error:
            return UNEXPECTED_ERROR

        # Get the descriptor path
        descriptor_path = get_descriptor_path(user.username,
                                              execution.identifier)

        # Get appriopriate descriptor object
        descriptor = Descriptor.descriptor_factory_from_type(
            execution_db.descriptor)

        # Create a version of the inputs file with correct links
        modified_inputs_path, error = create_absolute_path_inputs(
            user.username, execution.identifier, execution.pipeline_identifier,
            request.url_root)
        if error:
            return UNEXPECTED_ERROR

        # We are ready to start the execution
        # First, let's validate it using invocation
        success, error = descriptor.validate(descriptor_path,
                                             modified_inputs_path)
        if not success:
            execution_db.status = ExecutionStatus.InitializationFailed
            db.session.commit()
            return ErrorCodeAndMessageAdditionalDetails(
                INVALID_INVOCATION, error.message)

        # The execution is valid and we are now ready to start it
        start_execution(user, execution, descriptor, modified_inputs_path)
        pass
