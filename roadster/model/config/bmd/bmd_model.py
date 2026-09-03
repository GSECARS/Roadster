import time

from enum import Enum
from epics import caget, caput, caput_many

from roadster.model import MapModel
from roadster.model.config import StationModel


class BMDStages(Enum):
    # Enumeration of required stages.
    sample_horizontal = "Horizontal", "13BMD:m92", "POSITIONER", "G1"
    sample_vertical = "Vertical", "13BMD:m90", "POSITIONER", "GROUP3"
    sample_focus = "Focus", "13BMD:m93", "POSITIONER", "G3"
    sample_omega = "Omega", "13BMD:m94", "OMEGA", "GROUP6"

    pinhole_horizontal = "Horizontal", "13BMD:m81"
    pinhole_vertical = "Vertical", "13BMD:m82"
    pinhole_position = "Pinhole Position", "13BMD:m27"


class BMDScalers(Enum):
    # Enumeration with all available scalers.
    empty = "None", "None"
    s2 = "IO", "13BMD:scaler1.S2"
    s3 = "DAC", "13BMD:scaler1.S3"
    s4 = "DAC/LVP PD", "13BMD:scaler1.S4"
    s5 = "LVP I/IO", "13BMD:scaler1.S5"


class BMDMiscellaneous(Enum):
    table_shutter = "Table shutter", "13BMD:filter1sendCommand"
    photodiode = "Photodiode", "13BMD:filter1sendCommand"
    xps_stop = "Stages stop", "13IDD_DAC_XPS16:allstop"
    station_stop = "Station stop", "13BMD:allstop"
    pd_count = "Photodiode count", "13BMD:scaler1.CNT"
    pd_count_time = "Photodiode count time", "13BMD:scaler1.TP"


class BMDXps(Enum):
    host = "10.54.160.211"
    username = "Administrator"
    password = "Administrator"


class BMDModel(StationModel):

    name = "13-BM-D"

    stages = BMDStages
    scalers = BMDScalers
    miscellaneous = BMDMiscellaneous
    xps = BMDXps

    def stop_all(self) -> None:
        """Implements the stop_all method for 13ID-D"""
        caput_many(
            [
                self.miscellaneous.station_stop.value[1],
                self.miscellaneous.xps_stop.value[1],
            ],
            [1, 1],
        )

    def check_station_status(self) -> bool:
        pass

    def prepare_for_scan(self, *args, **kwargs) -> bool:
        pass
