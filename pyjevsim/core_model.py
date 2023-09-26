from system_object import SystemObject

class CoreModel(SystemObject):  
    def __init__(self, _name):
        super(CoreModel, self).__init__()
        # Model Type
        self._name = _name
        
        # Input Ports Declaration
        self.external_input_ports = []
        # Output Ports Declaration
        self.external_output_ports = []

    def set_name(self, _name):
        self._name = _name

    def get_name(self):
        return self._name
    
    # 2023.09.26 added by Jaiyun Lee 
    def get_unique_name(self):
        pass

    def insert_input_port(self, port):
        setattr(self, port, port)
        self.external_input_ports.append(port)

    def retrieve_input_ports(self):
        return self.external_input_ports

    def insert_output_port(self, port):
        setattr(self, port, port)
        self.external_output_ports.append(port)

    def retrieve_output_ports(self):
        return self.external_output_ports
