from flask_restful import Resource, request
from sqlalchemy.exc import IntegrityError
from server.database import db
from server.database.models.execution import Execution, ExecutionStatus
from server.common.error_codes_and_messages import UNEXPECTED_ERROR
from server.resources.helpers.pipelines import (
    get_original_descriptor_path_and_type)
from server.resources.helpers.executions import (
    write_inputs_to_file, create_execution_directory, get_execution_as_model,
    validate_request_model, filter_executions, delete_execution_directory,
    copy_descriptor_to_execution_dir)
from server.database.queries.executions import (get_all_executions_for_user,
                                                get_execution)
from .models.execution import ExecutionSchema
from .decorators import unmarshal_request, marshal_response, login_required


class Executions(Resource):
    @login_required
    @marshal_response(ExecutionSchema(many=True))
    def get(self, user):
        offset = request.args.get('offset')
        limit = request.args.get('limit')
        user_executions = get_all_executions_for_user(user.username,
                                                      db.session)
        for i, execution in enumerate(user_executions):
            exe, error = get_execution_as_model(user.username, execution)
            if error:
                return error
            user_executions[i] = exe

        user_executions, error = filter_executions(user_executions, offset,
                                                   limit)
        if error:
            return error

        return user_executions

    @login_required
    @unmarshal_request(ExecutionSchema())
    @marshal_response(ExecutionSchema())
    def post(self, model, user):
        _, error = validate_request_model(model, request.url_root)
        if error:
            return error

        try:
            # Get the descriptor path and type
            (descriptor_path,
             descriptor_type), error = get_original_descriptor_path_and_type(
                 model.pipeline_identifier)
            if error:
                return error

            # Insert new execution to DB
            new_execution = Execution(
                name=model.name,
                pipeline_identifier=model.pipeline_identifier,
                descriptor=descriptor_type,
                timeout=model.timeout,
                status=ExecutionStatus.Initializing,
                study_identifier=model.study_identifier,
                creator_username=user.username)
            db.session.add(new_execution)
            db.session.commit()

            # Execution directory creation
            (execution_path,
             carmin_files_path), error = create_execution_directory(
                 new_execution, user)
            if error:
                db.session.rollback()
                return error

            # Writing inputs to inputs file in execution directory
            error = write_inputs_to_file(model, carmin_files_path)
            if error:
                delete_execution_directory(execution_path)
                db.session.rollback()
                return error

            # Copying pipeline descriptor to execution folder
            error = copy_descriptor_to_execution_dir(carmin_files_path,
                                                     descriptor_path)
            if error:
                delete_execution_directory(execution_path)
                db.session.rollback()
                return UNEXPECTED_ERROR

            # Get execution from DB (for safe measure)
            execution_db = get_execution(new_execution.identifier, db.session)
            if not execution_db:
                return UNEXPECTED_ERROR

            # Get execution back as a model from the DB for response
            execution, error = get_execution_as_model(user.username,
                                                      execution_db)
            if error:
                return UNEXPECTED_ERROR
            return execution
        except IntegrityError:
            db.session.rollback()
