from .definition import CoreModel, ModelType
from collections import OrderedDict

class StructuralModel(CoreModel):
    def __init__(self, _name=""):
        super(StructuralModel, self).__init__(_name, ModelType.STRUCTURAL)

        self._models = []

        self.external_input_coupling_map = {}
        self.external_output_coupling_map = {}
        self.internal_coupling_map = {}

    def insert_model(self, model):
        self._models.append(model)

    def retrieve_models(self):
        return self._models

    def insert_external_input_coupling(self, src_port, internal_model, dst_port):
        if (self, src_port) not in self.external_input_coupling_map:
            self.external_input_coupling_map[(self, src_port)] = [(internal_model, dst_port)]
        else:
            self.external_input_coupling_map[(self, src_port)].append((internal_model, dst_port))

    def insert_external_output_coupling(self, internal_model, src_port, dst_port):
        self.external_output_coupling_map[(internal_model, src_port)] = (self, dst_port)
        pass

    def insert_internal_coupling(self, src_model, src_port, dst_model, dst_port):
        if (src_model, src_port) not in self.internal_coupling_map:
            self.internal_coupling_map[(src_model, src_port)] = [(dst_model, dst_port)]
        else:
            self.internal_coupling_map[(src_model, src_port)].append((dst_model, dst_port))
        pass

    def retrieve_external_input_coupling(self):
        return self.external_input_coupling_map

    def retrieve_external_output_coupling(self):
        return self.external_output_coupling_map

    def retrieve_internal_coupling(self):
        return self.internal_coupling_map

    def get_create_time(self):
        return 0
