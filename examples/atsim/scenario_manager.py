import yaml

from manuever_object import ManueverObject
from surfaceship import SurfaceShip
from torpedo import Torpedo

class ScenarioManager:
    def __init__(self, _path):
        self.scenario_path = _path

        # Read YAML file
        with open(_path, 'r') as f:
            yaml_data = yaml.safe_load(f)
            self.surface_ships = [SurfaceShip(f"blue_ship_{idx}", ManueverObject(**d["ManueverObject"])) for idx, d in enumerate(yaml_data['SurfaceShip'])]
            self.torpedoes = [Torpedo(f"red_torpedo_{idx}", ManueverObject(**d["ManueverObject"])) for idx, d in enumerate(yaml_data['Torpedo'])]

    def get_surface_ships(self):
        return self.surface_ships

    def get_torpedoes(self):
        return self.torpedoes