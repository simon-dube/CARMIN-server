import os
from server import app


def extract_execution_identifier_from_path(
        absolute_path_to_resource: str) -> str:

    rel_path = PurePath(
        os.path.relpath(absolute_path_to_resource,
                        app.config['DATA_DIRECTORY'])).as_posix()

    normalized_path = os.path.normpath(rel_path)
    split_path = normalized_path.split(os.sep)
    pass