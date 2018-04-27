from abc import ABC, abstractmethod
import os


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
    def execute(cls, user_data_dir, descriptor, input_data, workdir, stdout,
                stderr):
        pass

    @classmethod
    def descriptor_factory_from_type(cls, typ):
        from server.resources.models.descriptor.supported_descriptors import SUPPORTED_DESCRIPTORS
        return SUPPORTED_DESCRIPTORS.get(typ.lower())()

    @classmethod
    def descriptor_factory_from_path(cls, path_to_descriptor):
        parent_dir = os.path.dirname(path_to_descriptor)
        return Descriptor.descriptor_factory_from_type(
            os.path.basename(parent_dir))
