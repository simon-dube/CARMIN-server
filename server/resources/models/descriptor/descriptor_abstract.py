from abc import ABC, abstractmethod
from server.resources.models.descriptor.supported_descriptors import SUPPORTED_DESCRIPTORS


class Descriptor(ABC):
    @classmethod
    @abstractmethod
    def export(cls, input_descriptor_path, output_descriptor_path):
        pass

    @classmethod
    @abstractmethod
    def execute(cls, descriptor, input_data):
        pass


class DescriptorFactory():
    def create_descriptor(self, typ):
        target_class = typ.capitalize()
        return SUPPORTED_DESCRIPTORS[typ]()
