from subprocess import Popen


def git_annex_dropunused(dataset_path: str):
    process = Popen(['git-annex', 'dropunused', 'all'], cwd=dataset_path)
    exit_code = process.wait()
    return exit_code


def git_annex_drop_by_key(key: str, dataset_path: str):
    process = Popen(['git-annex', 'drop', '--key',
                     key], cwd=dataset_path)
    exit_code = process.wait()
    return exit_code
