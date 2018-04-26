import signal
from typing import List
from psutil import Process, wait_procs, NoSuchProcess
from server.database.models.execution_process import ExecutionProcess


def kill_all_execution_processes(execution_processes: List[ExecutionProcess]):
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


def kill_execution_processes(processes: List[ExecutionProcess]):
    all_gone = list()
    all_alive = list()
    for process_entry in processes:
        try:
            process = Process(process_entry.pid)
            children = process.children(recursive=True)
            children.append(process)
            for p in children:
                p.send_signal(signal.SIGKILL)
            gone, alive = wait_procs(children)
            all_gone.extend(gone)
            all_alive.extend(alive)
        except NoSuchProcess:
            # The process was already killed. Let's continue
            pass

    return all_gone, all_alive


def get_process_alive_count(processes: List[ExecutionProcess],
                            count_children: bool = False):
    count = 0
    for process_entry in processes:
        try:
            process = Process(process_entry.pid)
            count += 1
            if count_children:
                children = process.children(recursive=True)
                count += len(children)
        except NoSuchProcess:
            # The process was already killed. Let's continue
            pass

    return count
