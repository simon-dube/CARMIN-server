from server.resources.models.pipeline import Pipeline, PipelineParameter
from server.resources.models.error_code_and_message import ErrorCodeAndMessage

NameStudyOne = "study_one"
NameStudyTwo = "study_two"

PropNameOne = "prop_one"
PropNameTwo = "prop_two"

PropValueOne = "prop_value_one"
PropValueTwo = "prop_value_two"
PropValueThree = "prop_value_three"

PipelineParamOne = PipelineParameter(
    identifier="PipelineParam1",
    name="PipelineParam1",
    parameter_type="File",
    is_optional=False,
    is_returned_value=True,
    description="PipelineParam1 Description")

PipelineParamTwo = PipelineParameter(
    identifier="PipelineParam2",
    name="PipelineParam2",
    parameter_type="String",
    is_optional=False,
    is_returned_value=True,
    description="PipelineParam2 Description")

PipelineParamThree = PipelineParameter(
    identifier="file_input",
    name="file_input",
    parameter_type="File",
    is_optional=False,
    is_returned_value=False,
    description="PipelineParamThree description")

PipelineOne = Pipeline(
    identifier="one",
    name="one_name",
    version="version-1",
    description="One description",
    can_execute=True,
    parameters=list([PipelineParamOne]),
    properties={PropNameOne: PropValueOne},
    error_codes_and_messages=list([ErrorCodeAndMessage(1000, "Test message")]))

PipelineTwo = Pipeline(
    identifier="two",
    name="two_name",
    version="version-1",
    description="Two description",
    can_execute=False,
    parameters=list([PipelineParamOne, PipelineParamTwo]),
    properties={PropNameTwo: PropValueOne},
    error_codes_and_messages=list([ErrorCodeAndMessage(1000, "Test message")]))

PipelineThree = Pipeline(
    identifier="three",
    name="three_name",
    version="version-3",
    description="Three description",
    can_execute=True,
    parameters=list([PipelineParamOne, PipelineParamTwo]),
    properties={
        PropNameOne: PropValueTwo,
        PropNameTwo: PropValueThree
    },
    error_codes_and_messages=list(
        [ErrorCodeAndMessage(2000, "Pipeline three error code and message")]))

PIPELINE_FOUR = Pipeline(
    identifier="pipeline1",
    name="pipeline1",
    version="4.0.0",
    description="test pipeline",
    can_execute=True,
    parameters=list([PipelineParamThree]),
    properties={
        PropNameOne: PropValueTwo,
        PropNameTwo: PropValueThree
    },
    error_codes_and_messages=list(
        [ErrorCodeAndMessage(2000, "Pipeline four error code and message")]))

BOUTIQUES_ORIGINAL = {
    "command-line":
    "sleep 30 && echo \"Welcome to CARMIN-Server, $(cat [INPUT_FILE]).\" &> [OUTPUT_FILE]",
    "container-image": {
        "image": "alpine",
        "type": "docker"
    },
    "description":
    "A simple script to test output files",
    "error-codes": [{
        "code": 2,
        "description": "File does not exist."
    }],
    "inputs": [{
        "id": "file_input",
        "name": "Input file",
        "optional": False,
        "type": "File",
        "value-key": "[INPUT_FILE]"
    }],
    "invocation-schema": {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "additionalProperties": False,
        "dependencies": {},
        "description": "Invocation schema for output.",
        "properties": {
            "input_file": {
                "type": "string"
            }
        },
        "required": ["input_file"],
        "title": "output.invocationSchema",
        "type": "object"
    },
    "name":
    "output",
    "output-files": [{
        "id":
        "output_file",
        "name":
        "Output file",
        "path-template":
        "./greeting.txt",
        "path-template-stripped-extensions":
        [".txt", ".mnc", ".cpp", ".m", ".j"],
        "value-key":
        "[OUTPUT_FILE]"
    }],
    "schema-version":
    "0.5",
    "tool-version":
    "1.0"
}

BOUTIQUES_CONVERTED = {
    "identifier":
    "pipeline1",
    "name":
    "output",
    "version":
    "1.0",
    "description":
    "A simple script to test output files",
    "canExecute":
    True,
    "parameters": [{
        "name": "Input file",
        "id": "file_input",
        "type": "File",
        "isOptional": False,
        "isReturnedValue": False
    }, {
        "name": "Output file",
        "id": "output_file",
        "type": "File",
        "isOptional": False,
        "isReturnedValue": True
    }],
    "properties": {
        "boutiques": True
    },
    "errorCodesAndMessages": [{
        "errorCode": 2,
        "errorMessage": "File does not exist."
    }]
}
