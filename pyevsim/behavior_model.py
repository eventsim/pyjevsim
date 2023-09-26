from collections import OrderedDict
from .definition import CoreModel, ModelType

class BehaviorModel(CoreModel):
    def __init__(self, _name=""):
        super(BehaviorModel, self).__init__(_name, ModelType.BEHAVIORAL)
        self._states = {}

        self.external_transition_map_tuple = {}
        self.external_transition_map_state = {}
        self.internal_transition_map_tuple = {}
        self.internal_transition_map_state = {}

    def insert_state(self, name, deadline="inf"):
        # TODO: Exception Handling
        # TA < 0
        # Duplicated State
        self._states[name] = float(deadline)

    def update_state(self, name, deadline="inf"):
        # TODO: Exception Handling
        # TA < 0
        self._states[name] = float(deadline)

    def retrieve_states(self):
        return self._states

    def find_state(self, name):
        return name in self._states

    def insert_external_transition(self, pre_state, event, post_state):
        self.external_transition_map_tuple[(pre_state, event)] = post_state
        if pre_state in self.external_transition_map_state:
            self.external_transition_map_state[pre_state].append(event, post_state)
        else:
            self.external_transition_map_state[pre_state] = [(event, post_state)]

    def retrieve_external_transition(self, pre_state):
        return self.external_transition_map_state[pre_state]

    def retrieve_next_external_state(self, pre_state, event):
        return self.external_transition_map_tuple[(pre_state, event)]

    def find_external_transition(self, pre_state):
        return pre_state in self.external_transition_map_state

    def insert_internal_transition(self, pre_state, event, post_state):
        self.internal_transition_map_tuple[(pre_state, event)] = post_state
        if pre_state in self.internal_transition_map_state:
            self.internal_transition_map_state[pre_state].append(event, post_state)
        else:
            self.internal_transition_map_state[pre_state] = [(event, post_state)]

    def retrieve_internal_transition(self, pre_state):
        return self.internal_transition_map_state[pre_state]

    def retrieve_next_internal_state(self, pre_state, event):
        return self.internal_transition_map_tuple[(pre_state, event)]

    def find_internal_transition(self, pre_state):
        return pre_state in self.internal_transition_map_state

    def serialize(self):
        json_obj = OrderedDict()
        json_obj["name"] = self._name
        json_obj["states"] = self._states
        json_obj["input_ports"] = self.retrieve_input_ports()
        json_obj["output_ports"] = self.retrieve_output_ports()
        json_obj["external_trans"] = self.external_transition_map_state
        json_obj["internal_trans"] = self.internal_transition_map_state
        return json_obj

    def deserialize(self, json):
        self._name = json["name"]
        for k, v in json["states"].items():
            self.insert_state(k, v)

        # Handle In ports
        for port in json["input_ports"]:
            self.insert_input_port(port)

        # Handle out ports
        for port in json["output_ports"]:
            self.insert_output_port(port)

        # Handle External Transition
        for k, v in json["external_trans"].items():
            for ns in v:
                self.insert_external_transition(k, ns[0], ns[1])

        # Handle Internal Transition
        for k, v in json["internal_trans"].items():
            for ns in v:
                self.insert_internal_transition(k, ns[0], ns[1])
