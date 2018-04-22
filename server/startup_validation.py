"""Properties Validation performs validation on the `server-config.json` file,
which contains a description of the PlatformProperties object.
"""
import os
import sys
import json
import string
import random
from typing import Dict
from .config import (SUPPORTED_PROTOCOLS, SUPPORTED_MODULES,
                     SQLITE_DEFAULT_PROD_DB_URI, DEFAULT_PROD_DB_URI)
from .resources.models.platform_properties import PlatformPropertiesSchema
from server import app
from server.database import db
from .database.models.user import User, Role
from server.resources.helpers.pipelines import export_all_pipelines
from server.common.error_codes_and_messages import PATH_EXISTS
from server.platform_properties import PLATFORM_PROPERTIES


def start_up():
    pipeline_and_data_directory_present()
    export_pipelines()
    properties_validation()
    find_or_create_admin()


def properties_validation(config_data: Dict = None) -> bool:
    """Performs validation on server_config.json file. Checks for required
    parameters and supported options."""

    if not config_data:
        config_data = PLATFORM_PROPERTIES
    platform_properties, err = PlatformPropertiesSchema().load(config_data)

    # Raise error if required property is not provided
    if err:
        raise EnvironmentError(err)

    # Raise error if unsupported protocol or module
    for protocol in platform_properties.supported_transfer_protocols:
        if protocol not in SUPPORTED_PROTOCOLS:
            err = str.format("Unsupported protocol {}", protocol)
            raise ValueError(err)
    for module in platform_properties.supported_modules:
        if module not in SUPPORTED_MODULES:
            err = str.format("Unsupported module {}", module)
            raise ValueError(err)

    # Raise error if https not in supported protocols
    if "https" not in platform_properties.supported_transfer_protocols:
        raise EnvironmentError('CARMIN 0.3 requires https support')

    # Raise error if minTimeout is greater than maxTimeout
    if (platform_properties.max_authorized_execution_timeout != 0
            and platform_properties.min_authorized_execution_timeout >
            platform_properties.max_authorized_execution_timeout):
        raise ValueError('maxTimeout must be greater than minTimeout')
    return True


def pipeline_and_data_directory_present():
    """Checks if Pipeline and Data directories were specified at launch. If not,
    raise EnvironmentError
    """
    PIPELINE_DIRECTORY = app.config['PIPELINE_DIRECTORY']
    DATA_DIRECTORY = app.config['DATA_DIRECTORY']

    if not PIPELINE_DIRECTORY:
        raise EnvironmentError(
            "ENV['PIPELINE_DIRECTORY'] must be set to Pipeline directory path")
    if not DATA_DIRECTORY:
        raise EnvironmentError(
            "ENV['DATA_DIRECTORY'] must be set to input Data directory path")

    if app.config['SQLALCHEMY_DATABASE_URI'] == SQLITE_DEFAULT_PROD_DB_URI:
        print(
            "No SQL database URI found. Reverting to default production database found at {}".
            format(DEFAULT_PROD_DB_URI),
            flush=True)

    if (not os.path.isdir(PIPELINE_DIRECTORY)
            or not os.path.isdir(DATA_DIRECTORY)):
        raise EnvironmentError(
            "Data and Pipeline directories must be valid. Make sure that the given paths are absolute."
        )


def find_or_create_admin():
    admin = db.session.query(User).filter_by(role=Role.admin).first()
    if not admin:
        admin_username = "admin"
        admin_password = generate_admin_password()
        result, error = register_user(admin_username, admin_password,
                                      Role.admin, db.session)

        if error:
            raise EnvironmentError("Could not create first admin account.")
        separator = '-' * 20
        print('{0} Admin Account {0}\nusername: {1}\npassword: {2}\n'.format(
            separator, admin_username, admin_password))


def generate_admin_password(password_length=16):
    return ''.join(
        random.SystemRandom().choice(string.ascii_letters + string.digits)
        for _ in range(password_length))


def export_pipelines():
    success, error = export_all_pipelines()

    if not success:
        raise EnvironmentError(error)


from server.resources.helpers.register import register_user
