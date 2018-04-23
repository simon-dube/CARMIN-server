import sys
import os
from subprocess import Popen, TimeoutExpired
from multiprocessing import Pool, current_process
from server.platform_properties import PLATFORM_PROPERTIES
from server.database.models.user import User
from server.database.models.execution import ExecutionStatus, current_milli_time
from server.database.queries.executions import get_execution
from server.resources.models.execution import Execution
from server.database import db
from server.database.models.execution_process import ExecutionProcess
from server.resources.helpers.path import get_user_data_directory
from server.resources.helpers.executions import get_execution_dir


def start_execution(user: User, execution: Execution, descriptor_path: str,
                    inputs_path: str):
    # Launch the execution process
    pool = Pool()
    pool.apply_async(
        func=execution_process,
        kwds={
            "user": user,
            "execution": execution,
            "descriptor_path": descriptor_path,
            "inputs_path": inputs_path
        })
    pool.close()


def execution_process(user: User, execution: Execution, descriptor_path: str,
                      inputs_path: str):

    # 1 Write the current execution pid to database
    execution_process = ExecutionProcess(
        execution_identifier=execution.identifier, pid=current_process().pid)
    db.session.add(execution_process)
    db.session.commit()

    # 2 Change the execution status in the database
    execution_db = get_execution(execution.identifier, db.session)
    execution_db.status = ExecutionStatus.Running
    execution_db.start_date = current_milli_time()
    db.session.commit()

    # 3 Launch the bosh execution
    user_data_dir = get_user_data_directory(user.username)
    execution_dir = get_execution_dir(user.username, execution.identifier)
    timeout = execution.timeout
    if timeout is None:
        timeout = PLATFORM_PROPERTIES.get("defaultExecutionTimeout")
    if not timeout:
        timeout = None

    with open(os.path.join(
            execution_dir, "stdout.txt"), 'w') as file_stdout, open(
                os.path.join(execution_dir, "stderr.txt"), 'w') as file_stderr:
        try:
            process = Popen(
                [
                    "bosh", "exec", "launch",
                    "-v{0}:{0}".format(user_data_dir), descriptor_path,
                    inputs_path
                ],
                stdout=file_stdout,
                stderr=file_stderr,
                cwd=execution_dir)

            process.wait(timeout=timeout)

        except TimeoutExpired as timeout_expired:
            process.kill()
            file_stderr.writelines(
                "Execution timed out after {} seconds".format(
                    timeout_expired.timeout))
            return
        except Exception:
            execution_db.status = ExecutionStatus.ExecutionFailed
            db.session.delete(execution_process)
            db.session.commit()
            process.kill()
            return
        finally:
            os.remove(
                inputs_path)  # Delete the temporary absolute input paths file

    # 4 Execution completed - Writing to database
    execution_db.status = ExecutionStatus.Finished
    db.session.delete(execution_process)
    db.session.commit()
