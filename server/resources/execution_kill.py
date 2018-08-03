import os
from flask_restful import Resource
from server.common.error_codes_and_messages import (
    ErrorCodeAndMessageFormatter, ErrorCodeAndMessageAdditionalDetails,
    EXECUTION_NOT_FOUND, UNAUTHORIZED, UNEXPECTED_ERROR,
    CANNOT_KILL_NOT_RUNNING_EXECUTION, CANNOT_KILL_FINISHING_EXECUTION)
from server.database import db
from server.database.models.user import Role
from server.database.queries.executions import get_execution, get_execution_processes
from server.database.models.execution import Execution, ExecutionStatus, current_milli_time
from server.resources.decorators import login_required, marshal_response
from server.resources.helpers.execution_kill import kill_all_execution_processes
from server.resources.helpers.executions import (
    get_absolute_path_inputs_path, get_user_data_directory, get_execution_carmin_files_dir)
from server.datalad_f.utils import (
    get_data_dataset, datalad_remove, datalad_save)


class ExecutionKill(Resource):
    @login_required
    @marshal_response()
    def put(self, user, execution_identifier):
        execution_db = get_execution(execution_identifier, db.session)
        if not execution_db:
            return ErrorCodeAndMessageFormatter(EXECUTION_NOT_FOUND,
                                                execution_identifier)
        if user.role != Role.admin and execution_db.creator_username != user.username:
            return UNAUTHORIZED

        if execution_db.status != ExecutionStatus.Running:
            return ErrorCodeAndMessageFormatter(
                CANNOT_KILL_NOT_RUNNING_EXECUTION, execution_db.status.name)

        # Look at its running processes
        execution_processes = get_execution_processes(execution_identifier,
                                                      db.session)

        if not execution_processes:  # Most probably due to the execution being in termination process
            return CANNOT_KILL_FINISHING_EXECUTION

        kill_all_execution_processes(execution_processes)

        # Mark the execution as "Killed" and delete the execution processes
        execution_db.status = ExecutionStatus.Killed
        execution_db.end_date = current_milli_time()
        for execution_process in execution_processes:
            db.session.delete(execution_process)
        db.session.commit()

        modified_inputs_path = get_absolute_path_inputs_path(
            user.username, execution_identifier)
        dataset = get_data_dataset()
        if dataset:
            # Delete temporary absolute input paths files
            datalad_remove(dataset, modified_inputs_path)

            # Save new files in the user folder
            user_data_dir = get_user_data_directory(user.username)
            datalad_save(dataset, user_data_dir)
            execution_carmin_files_dir = get_execution_carmin_files_dir(
                user.username, execution_identifier)
            datalad_save(dataset, execution_carmin_files_dir)
            dataset.close()
        else:
            # Delete temporary absolute input paths files
            os.remove(modified_inputs_path)
