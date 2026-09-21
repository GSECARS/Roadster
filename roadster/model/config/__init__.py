from roadster.model.config.station_model import StationModel
from roadster.model.config.idd import IDDModel
from roadster.model.config.bmd.bmd_model import BMDModel
from roadster.model.config.bmc.bmc_model import BMCModel


from enum import Enum, auto


class Stations(Enum):
    IDD = auto()
    BMD = auto()
    BMC = auto()
