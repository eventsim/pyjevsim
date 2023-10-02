'''
 Author: Changbeom Choi (@cbchoi)
 Copyright (c) 2014-2020 Handong Global University
 Copyright (c) 2014-2020 Hanbat National University
 License: MIT.  The full license text is available at:
  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE
'''

from .structural_executor import StructuralExecutor
from .definition import Infinite

class StructuralModelExecutor(StructuralExecutor):
    def __init__(self, itime=Infinite, dtime=Infinite, ename="default", structural_model = None):
        pass
        
'''
    def flattening(self, _model, _del_model, _del_coupling):
        # handle external output coupling
        for k, v in _model.retrieve_external_output_coupling().items():
            if v in self.port_map:
                for coupling in self.port_map[v]:
                    self._coupling_relation(k, coupling)
                    _del_coupling.append((v,coupling))

        # handle external input coupling
        for k, v in _model.retrieve_external_input_coupling().items():
            port_key_lst = []
            for sk, sv in self.port_map.items():
                if k in sv:
                    port_key_lst.append(sk)
                    _del_coupling.append((sk, k))
            for key in port_key_lst:
                self.port_map[key].extend(v)

        # handle internal coupling
        for k, v, in _model.retrieve_internal_coupling().items():
            for dst in v:
                self._coupling_relation(k, dst)

        # manage model hierarchical 
        for m in _model.retrieve_models():
            if m.get_type() == ModelType.STRUCTURAL:
                self.flattening(m, _del_model, _del_coupling)
            else:
                self.register_entity(m)

        for k, model_lst in self.waiting_obj_map.items():
            if _model in model_lst:
                _del_model.append((k, _model))

    def _coupling_relation(self, _src, dst):
        if _src:
            src = self.product_port_map[_src]
        else:
            src = None

        if dst:
            dst = self.product_port_map[dst]
        else:
            dst = None

        if src in self.port_map:
            self.port_map[src].append(dst)
        else:
            self.port_map[src] = [dst]
'''
