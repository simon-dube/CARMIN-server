import signal
from typing import List
from psutil import Process, wait_procs, NoSuchProcess
from server.database.models.execution import ExecutionStatus


def kill_execution_processes(processes: List[ExecutionStatus]):
    all_gone = list()
    all_alive = list()
    for process_entry in processes:
        try:
            process = Process(process_entry.pid)
            children = process.children(recursive=True)
            children.append(process)
            print("SEND SHUTDOWN {}".format(process_entry.pid))
            for p in children:
                print("SEND SEND KILL {}".format(p.pid))
                p.send_signal(signal.SIGKILL)
            gone, alive = wait_procs(children)
            all_gone.extend(gone)
            all_alive.extend(alive)
        except NoSuchProcess:
            # The process was already killed. Let's continue
            print("ERROR {}".format(process_entry.pid))

    return all_gone, all_alive
