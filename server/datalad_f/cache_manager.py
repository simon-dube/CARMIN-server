import os
try:
    from os import scandir, walk
except ImportError:
    from scandir import scandir, walk
import logging
from subprocess import Popen
from cache_config import MAX_CACHE_SIZE, CACHE_CLEAR_TO
from datalad.api import Dataset
from server.datalad_f.utils import datalad_drop, get_annex_objects_path


def cache_clear(dataset: Dataset):
    if MAX_CACHE_SIZE <= 0:
        return

    # 1) Drop unused files to free space that should not be occupied in the first place
    process = Popen(['git-annex', 'dropunused'], cwd=dataset.path)
    exit_code = process.wait()
    # 2) If the total objects size is still greater than the cache size, we will drop
    # the least recently used files until we reach the CACHE_CLEAR_TO size.
    objects_path = get_annex_objects_path(dataset)
    size = 0
    all_files = list()
    for dirpath, _, filenames in os.walk(objects_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            all_files.append(fp)
            size += os.path.getsize(fp)

    if size > MAX_CACHE_SIZE:
        logger = logging.getLogger('background-thread')
        logger.info("Cache clear initialized for dataset at %s", dataset.path)
        ordered_files = sorted(all_files, key=os.path.getatime)
        original_size = size
        index = 0
        while size > CACHE_CLEAR_TO and index < len(ordered_files):
            cur_file = ordered_files[index]
            cur_file_size = os.path.getsize(cur_file)
            process = Popen(['git-annex', 'drop', '--key',
                             os.path.basename(cur_file)], cwd=dataset.path)
            exit_code = process.wait()
            if exit_code == 0:
                size -= cur_file_size
            index = index + 1

        freed_bytes = original_size - size
        logger.info(
            "Cache clear completed for dataset at %s. Freed %s bytes.", dataset.path, "{:n}".format(freed_bytes))
