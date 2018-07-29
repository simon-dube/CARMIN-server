import logging
from time import time
from threading import Thread
from server import app
from datalad.api import Dataset
from server.resources.models.error_code_and_message import ErrorCodeAndMessage
from .utils import get_data_dataset, datalad_update, datalad_publish


class DataladAutoUpdaterPublisher(Thread):
    def __init__(self, dataset: Dataset, interval_sec: int):
        Thread.__init__(self)
        self.daemon = True
        self.dataset = dataset
        self.interval_sec = interval_sec
        self.last_interval = time()
        self.kill_received = False
        self.name = "Dataset ({}) Updater-Publisher".format(dataset.path)

    def run(self):
        logger = logging.getLogger('background-thread')
        logger.info("%s initialized", self.name)

        while not self.kill_received:
            if self.time_exceeded():
                self.update()
                self.publish()
                self.last_interval = time()

        self.dataset.close()
        logger.info("%s terminated", self.name)

    def update(self):
        logger = logging.getLogger('background-thread')
        logger.info("Start %s update...", self.name)
        while not self.kill_received:
            success, error = datalad_update(self.dataset)
            if success:
                logger.info("%s update complete", self.name)
                return
            logger.info("%s update failed. Retrying...", self.name)

    def publish(self):
        logger = logging.getLogger('background-thread')
        logger.info("Start %s publish...", self.name)
        while not self.kill_received:
            success, error = datalad_publish(self.dataset)
            if success:
                logger.info("%s publish complete", self.name)
                return
            logger.info("%s publish failed. Retrying...", self.name)

    def force_update(self) -> (bool, ErrorCodeAndMessage):
        success, error = datalad_update(self.dataset)
        self.last_interval = time()
        return success, error

    def time_exceeded(self):
        return time() - self.last_interval >= self.interval_sec

    def kill(self):
        self.kill_received = True


class DataladAutoUpdaterManager():
    def __init__(self, dataset: Dataset, interval_sec: int):
        self.dataset = dataset
        self.interval_sec = interval_sec
        self.updater = DataladAutoUpdaterPublisher(dataset, interval_sec)

    def start(self):
        self.updater.start()

    def is_running(self):
        return self.updater and self.updater.isAlive()

    def restart(self):
        self.kill()
        self.updater = DataladAutoUpdaterPublisher(
            self.dataset, self.interval_sec)
        self.start()

    def force_update(self):
        return self.updater.force_update()

    def kill(self):
        if self.is_running():
            self.updater.kill()


DATALAD_AUTO_UPDATE_MANAGER = None
if get_data_dataset():
    DATALAD_AUTO_UPDATE_MANAGER = DataladAutoUpdaterManager(
        get_data_dataset(), 5)
