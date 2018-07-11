import copy
import sys
from typing import List
from server.resources.models.error_code_and_message import ErrorCodeAndMessage, ErrorCodeAndMessageSchema


def ErrorCodeAndMessageMarshaller(error_code_and_message: ErrorCodeAndMessage):
    return ErrorCodeAndMessageSchema().dump(error_code_and_message).data


def ErrorCodeAndMessageAdditionalDetails(
        error_code_and_message: ErrorCodeAndMessage, additional_details):
    error_code_and_message_result = copy.deepcopy(error_code_and_message)
    error_code_and_message_result.error_detail = copy.deepcopy(
        additional_details)
    return error_code_and_message_result


def ErrorCodeAndMessageFormatter(error_code_and_message: ErrorCodeAndMessage,
                                 *args):
    error_code_and_message_result = copy.deepcopy(error_code_and_message)
    error_code_and_message_result.error_message = error_code_and_message_result.error_message.format(
        *args)
    return error_code_and_message_result


def errors_as_list() -> List:
    errors = [
        getattr(sys.modules[__name__], e) for e in dir(sys.modules[__name__])
    ]
    return list(filter(lambda v: isinstance(v, ErrorCodeAndMessage), errors))


GENERIC_ERROR = ErrorCodeAndMessage(0,
                                    "Something went wrong. Please try again.")
UNEXPECTED_ERROR = ErrorCodeAndMessage(
    1, "An unexpected error occured. Please contact the system administrator.")
INVALID_REQUEST = ErrorCodeAndMessage(2, "Invalid Request.")
INVALID_MODEL_PROVIDED = ErrorCodeAndMessage(10, "Invalid model provided")
MODEL_DUMPING_ERROR = ErrorCodeAndMessage(
    15, "Server error while dumping model of type {}")
MISSING_API_KEY = ErrorCodeAndMessage(20, "Missing HTTP header field apiKey")
INVALID_API_KEY = ErrorCodeAndMessage(25, "Invalid apiKey")
INVALID_USERNAME_OR_PASSWORD = ErrorCodeAndMessage(
    30, "Invalid username/password.")
MISSING_PIPELINE_PROPERTY = ErrorCodeAndMessage(
    35, "'property' must be specified to use the 'propertyValue' argument")
USERNAME_ALREADY_EXISTS = ErrorCodeAndMessage(40,
                                              "Username '{}' already exists")
USER_DOES_NOT_EXIST = ErrorCodeAndMessage(41, "Username '{}' does not exist")
UNAUTHORIZED = ErrorCodeAndMessage(45, "Unauthorized access")
INVALID_PATH = ErrorCodeAndMessage(50, "Invalid pathname")
PATH_EXISTS = ErrorCodeAndMessage(55, "File/directory already exists")
PATH_DOES_NOT_EXIST = ErrorCodeAndMessage(56, "File/directory does not exist")
INVALID_ACTION = ErrorCodeAndMessage(60, "Invalid action")
MD5_ON_DIR = ErrorCodeAndMessage(
    65, "Invalid input: cannot generate md5 from directory")
LIST_ACTION_ON_FILE = ErrorCodeAndMessage(
    70, "Invalid input: cannot use list action on a file")
PATH_IS_DIRECTORY = ErrorCodeAndMessage(75,
                                        "Invalid path: '{}' is a directory.")
INVALID_UPLOAD_TYPE = ErrorCodeAndMessage(80,
                                          "'type' must be 'File' or 'Archive'")
ACTION_REQUIRED = ErrorCodeAndMessage(85, "'action' cannot be blank")
NOT_AN_ARCHIVE = ErrorCodeAndMessage(90, 'Invalid zip: {}')
INVALID_BASE_64 = ErrorCodeAndMessage(95, 'Invalid base64: {}')
EXECUTION_IDENTIFIER_MUST_NOT_BE_SET = ErrorCodeAndMessage(
    100,
    "'executionIdentifier' must not be set. It will be assigned by the system upon execution initialization."
)
EXECUTION_NOT_FOUND = ErrorCodeAndMessage(105, "Execution '{}' not found.")
INVALID_INPUT_FILE = ErrorCodeAndMessage(110,
                                         "Input file '{}' does not exist.")
INVALID_PIPELINE_IDENTIFIER = ErrorCodeAndMessage(
    115, "Invalid 'pipelineIdentifier'")
INVALID_QUERY_PARAMETER = ErrorCodeAndMessage(
    120, "Invalid value '{}' for query parameter '{}'.")
CANNOT_MODIFY_PARAMETER = ErrorCodeAndMessage(
    125, "'{}' cannot be modified on an existing Execution.")
INVOCATION_INITIALIZATION_FAILED = ErrorCodeAndMessage(
    130,
    "The execution was created with identifier '{}', but its initialization failed during the invocation validation."
)
CANNOT_REPLAY_EXECUTION = ErrorCodeAndMessage(
    135, "An execution cannot be replayed. Current status: '{}'")
INVALID_EXECUTION_TIMEOUT = ErrorCodeAndMessage(
    140, "Invalid execution timeout. Must be between {} and {} seconds.")
CANNOT_KILL_NOT_RUNNING_EXECUTION = ErrorCodeAndMessage(
    145, "Cannot kill a non running execution. Current status: '{}'")
CANNOT_KILL_FINISHING_EXECUTION = ErrorCodeAndMessage(
    150,
    "The execution processes are not running, thus the execution is most probably finishing and cannot be killed."
)
CANNOT_GET_RESULT_NOT_COMPLETED_EXECUTION = ErrorCodeAndMessage(
    155,
    "The execution is not done yet, thus results cannot be queried. Current status: '{}'. Please try again later."
)
CORRUPTED_EXECUTION = ErrorCodeAndMessage(
    160,
    "There is an unrecoverable problem with this execution. Please create a new execution."
)
UNSUPPORTED_DESCRIPTOR_TYPE = ErrorCodeAndMessage(
    165, "The descriptor type '{}' is not supported.")
DATA_DATASET_SIBLING_UNSPECIFIED = ErrorCodeAndMessage(
    170, "The data dataset has no sibling specified.")
DATA_DATASET_SIBLING_CANT_UPDATE = ErrorCodeAndMessage(
    175, "The data dataset was not able to update from sibling '{}'.")
DATASET_CANT_GET = ErrorCodeAndMessage(
    180, "Dataset could not get data from valid path '{}'.")
DATASET_NOT_INSTALLED = ErrorCodeAndMessage(
    185, "Attempted to performed action on uninstalled dataset at '{}'.")
DATASET_CANT_DROP = ErrorCodeAndMessage(
    190, "Dataset could not drop data from valid path '{}'.")
DATASET_CANT_SAVE = ErrorCodeAndMessage(
    195, "Dataset could not save data from valid path '{}'.")
DATASET_CANT_PUBLISH = ErrorCodeAndMessage(
    200, "Dataset could not publish data from valid path '{}'.")
PAGE_NOT_FOUND = ErrorCodeAndMessage(404, "Page Not Found")
