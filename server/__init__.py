import sys
from server.server_helper import create_app
from server.api import declare_api

app = create_app()

from server.logging.setup import log_response, log_exception
from server.resources.post_processors import *
from server.datalad_f.auto_updater import DATALAD_AUTO_UPDATE_MANAGER


def main():
    declare_api(app)
    start_up()

    if len(sys.argv) > 1:
        port = sys.argv[1]
        try:
            port = int(port)
        except ValueError:
            print("Invalid port number. Port must be an integer.")
            exit(1)
    else:
        port = 8080

    # Datalad auto-updater
    if DATALAD_AUTO_UPDATE_MANAGER:
        result = DATALAD_AUTO_UPDATE_MANAGER.safety_save()
        if not result:
            DATALAD_AUTO_UPDATE_MANAGER.kill()
            print("Could not save some content of the data dataset at {}. Content may be out of sync.".format(
                DATALAD_AUTO_UPDATE_MANAGER.dataset_path))
            exit(1)
        DATALAD_AUTO_UPDATE_MANAGER.start()

    try:
        app.run(host='0.0.0.0', port=port)
    finally:
        if DATALAD_AUTO_UPDATE_MANAGER:
            DATALAD_AUTO_UPDATE_MANAGER.kill()


from server.startup_validation import start_up
