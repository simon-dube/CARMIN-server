from datalad.api import Dataset
from server import app


def get_data_dataset() -> Dataset:
    dataset = Dataset(app.config.get("DATA_DIRECTORY"))
    return dataset if dataset.is_installed() else None
