from abc import ABC, abstractmethod
from server.resources.models.descriptor.supported_descriptors import SUPPORTED_DESCRIPTORS


class Descriptor(ABC):
    @classmethod
    @abstractmethod
    def validate(cls, descriptor, input_data):
        pass

    @classmethod
    @abstractmethod
    def export(cls, input_descriptor_path, output_descriptor_path):
        pass

    @classmethod
    @abstractmethod
    def execute(cls, user_data_dir, descriptor, input_data):
        pass


def create_descriptor(self, typ):
    return SUPPORTED_DESCRIPTORS.get(typ.lower())()
