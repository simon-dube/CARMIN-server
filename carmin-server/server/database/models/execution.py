import enum
import uuid
import time
from flask_restful import fields
from sqlalchemy import Column, String, Enum, Integer, ForeignKey
from server import db
from server.resources.models.execution import ExecutionStatus


def execution_uuid() -> str:
    return str(uuid.uuid4())


current_milli_time = lambda: int(round(time.time() * 1000))


class Execution(db.Model):
    """Execution

    Args:
        identifier (str):
        name (str):
        pipeline_identifier (str):
        timeout (int):
        status (ExecutionStatus):
        study_identifier (str):
        error_code (int):
        start_date (int):
        end_date (int):
        creator_username (str):

    Attributes:
        identifier (str):
        name (str):
        pipeline_identifier (str):
        timeout (int):
        status (ExecutionStatus):
        study_identifier (str):
        error_code (int):
        start_date (int):
        end_date (int):
        creator_username (str):        
    """

    identifier = Column(String, primary_key=True, default=execution_uuid)
    name = Column(String, nullable=False)
    pipeline_identifier = Column(String, nullable=False)
    timeout = Column(Integer)
    status = Column(Enum(ExecutionStatus), nullable=False)
    study_identifier = Column(String)
    error_code = Column(Integer)
    start_date = Column(Integer)
    end_date = Column(Integer)
    creator_username = Column(
        String, ForeignKey("user.username"), nullable=False)
    created_at = Column(Integer, default=current_milli_time)
    last_update = Column(Integer, onupdate=current_milli_time)
