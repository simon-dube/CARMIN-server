from threading import Thread
from datalad.api import Dataset


class DataladFailsafePublisher(Thread):
    def __init__(self, dataset: Dataset, path: str, drop_after: bool = False):
        Thread.__init__(self)
        self.daemon = True
        self.dataset = dataset
        self.path = path
        self.drop_after = drop_after

    def run(self):
        while True:
            success, error = datalad_publish(self.dataset, self.path)
            if success:
                if self.drop_after:
                    datalad_drop(self.dataset, self.path)
                break
        self.dataset.close()


from .utils import datalad_publish, datalad_drop
