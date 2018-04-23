from flask_restful import Resource
from server.common.error_codes_and_messages import (
    ErrorCodeAndMessageFormatter, ErrorCodeAndMessageAdditionalDetails,
    EXECUTION_NOT_FOUND, UNAUTHORIZED, UNEXPECTED_ERROR,
    CANNOT_KILL_NOT_RUNNING_EXECUTION, CANNOT_KILL_FINISHING_EXECUTION)
from server.database import db
from server.database.queries.executions import get_execution, get_execution_processes
from server.database.models.execution import Execution, ExecutionStatus
from server.resources.decorators import login_required, marshal_response
from server.resources.helpers.execution_kill import kill_execution_processes


class ExecutionKill(Resource):
    @login_required
    @marshal_response()
    def put(self, user, execution_identifier):
        execution_db = get_execution(execution_identifier, db.session)
        if not execution_db:
            return ErrorCodeAndMessageFormatter(EXECUTION_NOT_FOUND,
                                                execution_identifier)
        if execution_db.creator_username != user.username:
            return UNAUTHORIZED

        if execution_db.status != ExecutionStatus.Running:
            return ErrorCodeAndMessageFormatter(
                CANNOT_KILL_NOT_RUNNING_EXECUTION, execution_db.status)

        # Look at its running processes
        execution_processes = get_execution_processes(execution_identifier,
                                                      db.session)

        if not execution_processes:  # Most probably due to the execution being in termination process
            return CANNOT_KILL_FINISHING_EXECUTION

        actual_execution_processes = [
            e for e in execution_processes if e.is_execution
        ]
        execution_parent_processes = [
            e for e in execution_processes if not e.is_execution
        ]

        gone_parent, alive_parent = kill_execution_processes(
            execution_parent_processes)
        gone_process, alive_process = kill_execution_processes(
            actual_execution_processes)

        # Mark the execution as "Killed" and delete the execution processes
        for execution_process in execution_processes:
            db.session.delete(execution_process)
        execution_db.status = ExecutionStatus.Killed
        db.session.commit()

        pass
