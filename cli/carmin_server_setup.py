"""Usage: carmin-server setup [options]

Options:
    -p <path>, --pipeline-directory <path>   Specify path for pipeline directory
    -d <path>, --data-directory <path>       Specify path for data directory
    -w <path>, --database <path>             Specify path for database
    -r <remote-name>, --remote <remote-name> Specify the datalad remote for the data directory

"""

import json
import os
from pathlib import Path
from docopt import docopt
from datalad.api import Dataset


def is_interactive(invocation_list):
    return not (invocation_list.get('--remote')
                and invocation_list.get('--database')
                and invocation_list.get('--pipeline-directory')
                and invocation_list.get('--data-directory'))


def write_to_config_file(config):
    root_dir = Path(__file__).resolve().parent.parent
    config_file = Path(root_dir, 'CONFIG.json')
    with open(config_file, 'w') as f:
        json.dump(config, f)


def print_install_banner():
    width = 50
    delimiter = '-' * width
    print('{0}\nCARMIN-Server Setup (Press CTRL-C to quit)\n{0}'.format(
        delimiter))


def datalad_select_sibling(siblings: list, step_count: int, path: str):
    siblings_names = [sibling.get('name') for sibling in siblings]
    print("\nThe data directory {} was identified as a Datalad dataset.".format(path))

    while True:
        print("The following siblings were found: {}".format(
            siblings_names))
        data_dataset_remote = input('{}. {}'.format(step_count,
                                                    ask_datalad))
        if data_dataset_remote and data_dataset_remote not in siblings_names:
            print("Invalid sibling.")
            continue
        return data_dataset_remote


def datalad_select_refresh_time(step_count: int):
    while True:
        data_dataset_remote_refresh_time = input('{}. {}'.format(step_count,
                                                                 ask_datalad_updater_refresh_rate))
        if data_dataset_remote_refresh_time:
            try:
                data_dataset_remote_refresh_time = int(
                    data_dataset_remote_refresh_time)
                if data_dataset_remote_refresh_time < 0:
                    raise ValueError("Negative refresh time")
            except ValueError:
                print("Invalid value. Must be a positive integer.")
                continue
        return str(data_dataset_remote_refresh_time)


def datalad_data_remote_query(data_path: str, step_count: int):
    dataset = None
    if data_path:
        dataset = Dataset(data_path)
    elif os.environ.get('DATA_DIRECTORY'):
        dataset = Dataset(os.environ.get('DATA_DIRECTORY'))

    if dataset and dataset.is_installed():
        data_dataset_remote, data_dataset_remote_refresh_time = '', ''
        siblings = dataset.siblings(result_renderer=None)
        if len(siblings) > 0:
            data_dataset_remote = datalad_select_sibling(
                siblings, step_count, dataset.path)
            step_count += 1

            if data_dataset_remote:
                data_dataset_remote_refresh_time = datalad_select_refresh_time(
                    step_count)
                step_count += 1
            return data_dataset_remote, data_dataset_remote_refresh_time, step_count
    return '', '', step_count


ask_pipeline = "Enter path to pipeline directory: "
ask_data = "Enter path to data directory: "
ask_database = "Enter path or URI to the database (to use the default sqlite database, leave blank): "
ask_datalad = "Enter the name of the sibling you wish to update from and publish your data to (to not publish data, leave blank): "
ask_datalad_updater_refresh_rate = "Enter the sibling refresh rate (seconds) (to use the default time, leave blank): "


def carmin_setup():
    args = docopt(__doc__)
    try:
        if is_interactive(args):
            print_install_banner()
            step_count = 1
            if not args.get('--pipeline-directory'):
                while True:
                    pipeline_path = input('{}. {}'.format(step_count,
                                                          ask_pipeline))
                    if pipeline_path and not os.path.isabs(pipeline_path):
                        print("Path must be absolute.")
                        continue
                    break

                step_count += 1
            if not args.get('--data-directory'):
                while True:
                    data_path = input('{}. {}'.format(step_count, ask_data))
                    if data_path and not os.path.isabs(data_path):
                        print("Path must be absolute.")
                        continue
                    break
                step_count += 1
            if not args.get('--database'):
                database_path = input('{}. {}'.format(step_count,
                                                      ask_database))
                step_count += 1

            if not args.get('--remote'):
                data_dataset_remote, data_dataset_remote_refresh_time, step_count = datalad_data_remote_query(
                    data_path, step_count)

            config_dict = {
                "PIPELINE_DIRECTORY": pipeline_path,
                "DATA_DIRECTORY": data_path,
                "DATABASE_URL": database_path,
                "DATA_REMOTE_SIBLING": data_dataset_remote,
                "DATA_REMOTE_SIBLING_REFRESH_TIME": data_dataset_remote_refresh_time
            }
            write_to_config_file(config_dict)
        exit("\nCARMIN-Server was successfully configured.")
    except KeyboardInterrupt:
        exit()


if __name__ == '__main__':
    carmin_setup()
