import logging
from threading import Thread
from datalad.api import Dataset


class DataladFailsafePublisher(Thread):
    def __init__(self, dataset: Dataset, path: str, drop_after: bool = False):
        Thread.__init__(self)
        self.daemon = False
        self.dataset = dataset
        self.path = path
        self.drop_after = drop_after
        self.name = "Failsafe Publisher for {}".format(path)

    def run(self):
        logger = logging.getLogger('background-thread')
        logger.info("{} initialized".format(self.name))
        while True:
            logger.info("Start publish failsafe for {}".format(self.path))
            success, error = datalad_publish(self.dataset, self.path)
            if success:
                logger.info(
                    "Publish failsafe for {} succeeded".format(self.path))
                if self.drop_after:
                    datalad_drop(self.dataset, self.path)
                break
            logger.info("Publish failsafe for {} failed".format(self.path))
        self.dataset.close()


from .utils import datalad_publish, datalad_drop
