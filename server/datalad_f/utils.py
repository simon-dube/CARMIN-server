import os
import json
from typing import Callable
import logging
from datalad.api import Dataset
from datalad.support.exceptions import IncompleteResultsError
from server import app
from server.common.error_codes_and_messages import (
    ErrorCodeAndMessageFormatter, DATASET_CANT_GET, DATASET_CANT_DROP,
    DATASET_CANT_SAVE, DATASET_CANT_PUBLISH, DATASET_NOT_INSTALLED,
    DATA_DATASET_SIBLING_UNSPECIFIED, DATASET_CANT_REMOVE, DATASET_CANT_UNLOCK, DATA_DATASET_SIBLING_CANT_UPDATE)
from server.resources.models.error_code_and_message import ErrorCodeAndMessage


def get_data_dataset() -> Dataset:
    directory = app.config.get("DATA_DIRECTORY")
    if not directory:
        return None
    dataset = Dataset(directory)
    return dataset if dataset.is_installed() else None


def is_dataset_and_path_valid(dataset: Dataset, path: str) -> any:
    if not dataset.is_installed():
        logger = logging.getLogger('server-error')
        logger.error(ErrorCodeAndMessageFormatter(
            DATASET_NOT_INSTALLED, dataset.path).error_message)
        return False

    if not path_exists(path):
        return False
    return True


def datalad_operation(dataset: Dataset, path: str, operation: Callable, error: ErrorCodeAndMessage, sibling: str = None):
    if path and not is_dataset_and_path_valid(dataset, path):
        return False

    try:
        result = operation()
        return True if not result else result
    except IncompleteResultsError as ire:
        logger = logging.getLogger('server-error')
        if error:
            if not path:
                path = dataset.path
            logger.error(ErrorCodeAndMessageFormatter(
                error, path, sibling).error_message)
        logger.exception(ire)
        return False


def datalad_get(dataset: Dataset, path: str) -> any:
    return datalad_operation(dataset, path, lambda: dataset.get(path=path), DATASET_CANT_GET)


def datalad_save(dataset: Dataset, path: str = None) -> any:
    return datalad_operation(dataset, path, lambda: dataset.save(path=path), DATASET_CANT_SAVE)


def datalad_publish(dataset: Dataset, path: str = None, sibling: str = None) -> (any, ErrorCodeAndMessage):
    if not sibling:
        sibling = app.config.get("DATA_REMOTE_SIBLING")
    if not sibling:
        return None, DATA_DATASET_SIBLING_UNSPECIFIED

    success = datalad_operation(dataset, path,
                                lambda: dataset.publish(
                                    path=path, to=sibling, transfer_data="all"),
                                DATASET_CANT_PUBLISH, sibling)
    return success, None


def datalad_remove(dataset: Dataset, path: str) -> any:
    return datalad_operation(dataset, path, lambda: dataset.remove(path=path), DATASET_CANT_REMOVE)


def datalad_unlock(dataset: Dataset, path: str) -> any:
    return datalad_operation(dataset, path, lambda: dataset.unlock(path=path), DATASET_CANT_UNLOCK)


def datalad_update(dataset: Dataset, path: str=None, sibling: str=None) -> (any, ErrorCodeAndMessage):
    if not sibling:
        sibling = app.config.get("DATA_REMOTE_SIBLING")
    if not sibling:
        return None, DATA_DATASET_SIBLING_UNSPECIFIED

    return datalad_operation(dataset, path,
                             lambda: dataset.update(
                                 path=path, sibling=sibling, merge=True, on_failure="stop"),
                             DATA_DATASET_SIBLING_CANT_UPDATE, sibling), None


def datalad_get_unlock_if_exists(dataset: Dataset, path: str) -> any:
    if dataset and path_exists(path) and not os.path.isdir(path):
        success = datalad_get(dataset, path)
        return datalad_unlock(dataset, path) if success else success

    return True


def datalad_get_unlock_inputs(dataset: Dataset, modified_inputs_path: str) -> any:
    with open(modified_inputs_path) as inputs_file:
        inputs = json.load(inputs_file)

    files_gotten = list()
    for key in inputs:
        path = inputs[key]
        success = datalad_get(dataset, path)
        if not success:
            # We relock all files that were previously successfully gotten
            for file_gotten in files_gotten:
                datalad_save(dataset, path)
            return False
        files_gotten.append(files_gotten)
        success = datalad_unlock(dataset, path)
    return True


def get_annex_objects_path(dataset: Dataset):
    return os.path.join(dataset.path, '.git', 'annex', 'objects')


def get_datalad_last_symlink_or_path(path: str, dataset: Dataset) -> str:
    cur_path = path
    while os.path.islink(cur_path):
        path = cur_path
        cur_path = os.path.normpath(os.path.join(
            os.path.dirname(path), os.readlink(path)))

    if dataset and not cur_path.startswith(get_annex_objects_path(dataset)):
        path = cur_path
    return path


from server.resources.helpers.path import path_exists
