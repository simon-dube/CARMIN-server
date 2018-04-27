import sys
import os
# from subprocess import Popen, TimeoutExpired
from multiprocessing import Pool, current_process, Process
from server.platform_properties import PLATFORM_PROPERTIES
from server.database.models.user import User
from server.database.models.execution import ExecutionStatus, current_milli_time
from server.database.queries.executions import get_execution
from server.resources.models.execution import Execution
from server.database import db
from server.database.models.execution_process import ExecutionProcess
from server.resources.helpers.path import get_user_data_directory
from server.resources.helpers.executions import (
    get_execution_dir, get_descriptor_path, std_file_path, STDOUT_FILENAME,
    STDERR_FILENAME)
from server.resources.helpers.execution_kill import kill_execution_processes
from server.resources.models.descriptor.descriptor_abstract import Descriptor


def start_execution(user: User, execution: Execution, descriptor: Descriptor,
                    inputs_path: str):
    # Launch the execution process
    pool = Pool(processes=1)
    pool.apply_async(
        func=execution_process,
        kwds={
            "user": user,
            "execution": execution,
            "descriptor": descriptor,
            "inputs_path": inputs_path
        })
    pool.close()


def execution_process(user: User, execution: Execution, descriptor: Descriptor,
                      inputs_path: str):

    # 1 Write the current execution pid to database
    execution_process = ExecutionProcess(
        execution_identifier=execution.identifier,
        pid=current_process().pid,
        is_execution=False)
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
    descriptor_path = get_descriptor_path(user.username, execution.identifier)
    timeout = execution.timeout
    if timeout is None:
        timeout = PLATFORM_PROPERTIES.get("defaultExecutionTimeout")
    if not timeout:
        timeout = None

    with open(
            std_file_path(user.username, execution.identifier,
                          STDOUT_FILENAME),
            'w') as file_stdout, open(
                std_file_path(user.username, execution.identifier,
                              STDERR_FILENAME), 'w') as file_stderr:
        try:
            process = Process(
                target=descriptor.execute,
                kwargs={
                    "user_data_dir": user_data_dir,
                    "descriptor": descriptor_path,
                    "input_data": inputs_path,
                    "workdir": execution_dir,
                    "stdout": file_stdout,
                    "stderr": file_stderr
                })
            process.start()
            # process = Popen(
            #     (user_data_dir, descriptor_path, inputs_path),
            #     stdout=file_stdout,
            #     stderr=file_stderr,
            #     cwd=execution_dir)

            print(process.pid, flush=True)
            # Insert Popen process in DB
            execution_process_popen = ExecutionProcess(
                execution_identifier=execution.identifier,
                pid=process.pid,
                is_execution=True)
            db.session.add(execution_process_popen)
            db.session.commit()

            process.join(timeout=timeout)
        except TimeoutError as timeout_error:  # Timeout
            if execution_process_popen:
                kill_execution_processes([execution_process_popen])
            file_stderr.writelines(
                "Execution timed out after {} seconds".format(timeout))
            ExecutionFailed(execution_db)
        except Exception:  # Any other execution issue
            ExecutionFailed(execution_db)
            if execution_process_popen:
                kill_execution_processes([execution_process_popen])
        else:
            # 4 Execution completed - Writing to database
            print(returncode, flush=True)
            print(process.returncode, flush=True)
            execution_db.status = ExecutionStatus.Finished if returncode == 0 else ExecutionStatus.ExecutionFailed
            db.session.commit()
        finally:
            # Delete Execution processes from the database
            db.session.delete(execution_process)
            if execution_process_popen:
                db.session.delete(execution_process_popen)
            # Insert endtime
            execution_db.end_date = current_milli_time()
            db.session.commit()

            # Delete temporary absolute input paths files
            os.remove(inputs_path)


def ExecutionFailed(execution_db):
    execution_db.status = ExecutionStatus.ExecutionFailed
    db.session.commit()
