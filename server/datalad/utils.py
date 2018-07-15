import os
from typing import Callable
import logging
from datalad.api import Dataset
from datalad.support.exceptions import IncompleteResultsError
from server import app
from server.common.error_codes_and_messages import (
    ErrorCodeAndMessageFormatter, DATASET_CANT_GET, DATASET_CANT_DROP,
    DATASET_CANT_SAVE, DATASET_CANT_PUBLISH, DATASET_NOT_INSTALLED,
    DATA_DATASET_SIBLING_UNSPECIFIED, DATASET_CANT_REMOVE, DATASET_CANT_UNLOCK)
from server.resources.models.error_code_and_message import ErrorCodeAndMessage


def get_data_dataset() -> Dataset:
    dataset = Dataset(app.config.get("DATA_DIRECTORY"))
    return dataset if dataset.is_installed() else None


def is_dataset_and_path_valid(dataset: Dataset, path: str) -> bool:
    if not dataset.is_installed():
        logger = logging.getLogger('server-error')
        logger.error(ErrorCodeAndMessageFormatter(
            DATASET_NOT_INSTALLED, dataset.path).error_message)
        return False

    if not path_exists(path):
        return False
    return True


def datalad_operation(dataset: Dataset, path: str, operation: Callable, error: ErrorCodeAndMessage):
    if not is_dataset_and_path_valid(dataset, path):
        return False

    try:
        operation()
        return True
    except IncompleteResultsError as ire:
        logger = logging.getLogger('server-error')
        logger.error(ErrorCodeAndMessageFormatter(
            error, path).error_message)
        logger.exception(ire)
        return False


def datalad_get(dataset: Dataset, path: str) -> bool:
    return datalad_operation(dataset, path, lambda: dataset.get(path=path), DATASET_CANT_GET)


def datalad_drop(dataset: Dataset, path: str) -> bool:
    return datalad_operation(dataset, path, lambda: dataset.drop(path=path), DATASET_CANT_DROP)


def datalad_save(dataset: Dataset, path: str):
    return datalad_operation(dataset, path, lambda: dataset.save(path=path), DATASET_CANT_SAVE)


def datalad_publish(dataset: Dataset, path: str, sibling: str=None) -> (bool, ErrorCodeAndMessage):
    if not sibling:
        sibling = app.config.get("DATA_REMOTE_SIBLING")
    if not sibling:
        return None, DATA_DATASET_SIBLING_UNSPECIFIED

    return datalad_operation(dataset, path,
                             lambda: dataset.publish(
                                 path=path, to=sibling),
                             DATASET_CANT_PUBLISH), None


def datalad_save_and_publish(dataset: Dataset, path: str) -> (bool, ErrorCodeAndMessage):
    success = datalad_save(dataset, path)
    if not success:
        return False, None
    return datalad_publish(dataset, path)


def datalad_remove(dataset: Dataset, path: str) -> bool:
    return datalad_operation(dataset, path, lambda: dataset.remove(path=path), DATASET_CANT_REMOVE)


def datalad_remove_and_publish(dataset: Dataset, path: str) -> (bool, ErrorCodeAndMessage):
    success = datalad_remove(dataset, path)
    if not success:
        return False, None
    return datalad_publish(dataset, None)


def datalad_unlock(dataset: Dataset, path: str) -> bool:
    return datalad_operation(dataset, path, lambda: dataset.unlock(path=path), DATASET_CANT_UNLOCK)


from server.resources.helpers.path import path_exists
