import logging
from time import time
from threading import Thread
from server import app
from datalad.api import Dataset
from server.resources.models.error_code_and_message import ErrorCodeAndMessage
from .utils import (get_data_dataset, datalad_update,
                    datalad_publish, datalad_save)
from server.database import db
from server.database.queries.executions import get_users_with_running_executions
from server.resources.helpers.path import get_user_data_directory
from .cache_manager import cache_clear


class InvalidSibling(Exception):
    pass


class DataladAutoUpdaterPublisher(Thread):
    def __init__(self, dataset: Dataset, sibling: str, interval_sec: int):
        if sibling:
            result = self.validate_sibling(dataset, sibling)
            if not result:
                raise InvalidSibling("Remote sibling '{}' is not valid for dataset {}. Please make sure to provide a valid sibling.".format(
                    data_sibling, data_dataset.path))

        Thread.__init__(self)
        self.daemon = True
        self.dataset = dataset
        self.sibling = sibling
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
                cache_clear(self.dataset)
                self.last_interval = time()

        self.dataset.close()
        logger.info("%s terminated", self.name)

    def update(self):
        logger = logging.getLogger('background-thread')
        logger.info("Start %s update...", self.name)
        while not self.kill_received:
            success, error = datalad_update(self.dataset, sibling=self.sibling)
            if success:
                logger.info("%s update complete", self.name)
                return
            logger.info("%s update failed. Retrying...", self.name)

    def publish(self):
        logger = logging.getLogger('background-thread')
        logger.info("Start %s publish...", self.name)
        while not self.kill_received:
            success, error = datalad_publish(
                self.dataset, sibling=self.sibling)
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

    def validate_sibling(self, dataset: Dataset, sibling: str):
        if not dataset or not dataset.is_installed():
            return False

        for s in dataset.siblings(result_renderer=None):
            if s.get('name') == sibling:
                return True
        return False


class DataladAutoUpdaterManager():
    def __init__(self, dataset: Dataset, sibling: str, interval_sec: int):
        self.dataset = dataset
        self.sibling = sibling
        self.interval_sec = interval_sec
        self.updater = DataladAutoUpdaterPublisher(
            dataset, sibling, interval_sec)

    def start(self):
        self.updater.start()

    def is_running(self):
        return self.updater and self.updater.isAlive()

    def restart(self):
        self.kill()
        self.updater = DataladAutoUpdaterPublisher(
            self.dataset, self.sibling, self.interval_sec)
        self.start()

    def force_update(self):
        return self.updater.force_update()

    def kill(self):
        if self.is_running():
            self.updater.kill()

    def safety_save(self):
        users = get_users_with_running_executions(db.session)

        for user in users:
            user_folder = get_user_data_directory(user)
            result = datalad_save(self.dataset, user_folder)
            if not result:
                return False
        return True

    def dataset_path(self):
        return '' if not self.dataset else self.dataset.path


DATALAD_AUTO_UPDATE_MANAGER = None
data_dataset = get_data_dataset()
if data_dataset:
    data_sibling = app.config.get("DATA_REMOTE_SIBLING")
    try:
        DATALAD_AUTO_UPDATE_MANAGER = DataladAutoUpdaterManager(
            data_dataset, data_sibling, app.config.get("DATA_REMOTE_SIBLING_REFRESH_TIME"))
    finally:
        data_dataset.close()
