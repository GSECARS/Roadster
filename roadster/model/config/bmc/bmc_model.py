import time
from enum import Enum
from typing import List, Optional

from epics import caget, caput, caput_many

from roadster.model import MapModel, TrajectoryLine
from roadster.model.config import StationModel


class BMCStages(Enum):
    # Enumeration of required stages.
    sample_horizontal = "Horizontal", "13BMC:m46"
    sample_vertical = "Vertical", "13BMC:m45"
    sample_focus = "Focus", "13BMC:m44"
    sample_omega = "Phi", "13BMC:m33"

    pinhole_horizontal = "Horizontal", "13BMC:m71"
    pinhole_vertical = "Vertical", "13BMC:m72"
    pinhole_position = "Pinhole Position", "13BMC:m73"


class BMCScalers(Enum):
    # Enumeration with all available scalers.
    empty = "None", "None"
    s2 = "I0", "13BMC:scaler1.S2"
    s3 = "I1", "13BMC:scaler1.S3"
    s4 = "I2", "13BMC:scaler1.S4"
    s5 = "I3", "13BMC:scaler1.S5"
    s6 = "I4", "13BMC:scaler1.S6"

    s2_calc = "I0 Calc", "13BMC:scaler1_cts1.B"
    s3_calc = "I1 Calc", "13BMC:scaler1_cts1.C"
    s4_calc = "I2 Calc", "13BMC:scaler1_cts1.D"
    s5_calc = "I3 Calc", "13BMC:scaler1_cts2.A"
    s6_calc = "I4 Calc", "13BMC:scaler1_cts2.B"


class BMCMiscellaneous(Enum):
    table_shutter = "Table shutter", "13BMC:BenchAtten1"  # 0: Close, 1: Open
    station_stop = "Station stop", "13BMC:allstop"
    xps_stop = "XPS stop", "13BMC_GPD_XPS:allstop"
    pd_count = "Photodiode count", "13BMC:scaler1.CNT"
    pd_count_time = "Photodiode count time", "13BMC:scaler1.TP"
    pd_count_type = "Scaler count type", "13BMC:scaler1.CONT"
    current = "Ring current", "S:SRcurrentAI"


# class IDDDirectories(Enum):
#    save_location = "data/"


class BMCModel(StationModel):
    name = "13-BM-C"
    base_dir = "T:/dac_user/2026/BMC_2026-3/"

    stages = BMCStages
    scalers = BMCScalers
    miscellaneous = BMCMiscellaneous

    _expert_pwd = "Pilatus2"

    def stop_all(self) -> None:
        """Implements the stop_all method for 13ID-D"""
        caput_many(
            [
                self.miscellaneous.station_stop.value[1],
                self.miscellaneous.xps_stop.value[1],
            ],
            [1, 1],
        )
    def prepare_for_scan(
        self, target_stage, scan: MapModel, expert: Optional[bool] = False
    ) -> bool:
        """
        Implements the prepare_for_scan method for 13ID-D.
        :param target_stage: The stage that is used for scanning.
        :param scan: The MapModel of the scan.
        :param expert: Expert mode bypasses limits and collision checks.
        :return: In case of errors it returns False.
        """
        # Reset abort status
        object.__setattr__(self, "trj_aborted", False)

        if not expert:
            # Check for errors
            if not self._check_station_status(target_stage=target_stage, scan=scan):
                return False

        # Move to position
        self._move_to_position(target_stage, scan.lines[0])

        return True

    def prepare_shutter(self):
        # Open shutter
        caput(self.miscellaneous.table_shutter.value[1], 1)
        time.sleep(0.5)

    def prepare_for_auto_centering(
        self, positions: List[float], expert: Optional[bool] = False
    ) -> bool:
        """
        Implements the prepare_for_auto_centering method for 13ID-D.
        :param positions: A list with the starting position for each scan.
        :param expert: Expert mode bypasses limits and collision checks.
        :return: In case of errors it returns False.
        """
        # Reset abort status
        object.__setattr__(self, "trj_aborted", False)

        if not expert:
            # Check 13ID-D mirrors
            if not self._check_mirrors():
                return False

            # Check 13ID-D microscope
            if not self._check_microscope():
                return False

            # Check stage limits
            low_limit = caget(self.stages.sample_omega.value[1] + ".LLM")
            high_limit = caget(self.stages.sample_omega.value[1] + ".HLM")

            for position in positions:
                if position < low_limit or position > high_limit:
                    return False

        # Move to the first position on the list
        caput(self.stages.sample_omega.value[1], positions[0], wait=True)

        return True

    def restore_station(
        self,
        target_stage: str,
        center: float,
        centering: Optional[bool] = False,
        revert_position: Optional[bool] = True,
    ) -> None:
        # Close shutter
        caput(self.miscellaneous.table_shutter.value[1], 0)

        if revert_position:
            # Move stage back to position
            caput(target_stage, center, wait=True)

    def _check_station_status(self, target_stage, scan: MapModel) -> bool:
        """
        Implements the check_station_status method for the 13 ID-D required checks.
        :param target_stage: The stage that is used for scanning.
        :param scan: The MapModel of the scan.
        :return: In case of errors it returns False.
        """

        # Check for stage limits based on map positions
        if not self._check_stage_limits(target_stage, scan.lines):
            return False

        return True

    def check_beam_hutch_status(self) -> bool:
        """Implements the check_beam_status method for the 13-ID-D station."""

        # Check for beam.
        if caget(self.miscellaneous.current.value[1]) < 10:
            return False

        return True

    def _check_mirrors(self) -> bool:
        pass

    def _check_microscope(self) -> bool:
        pass

    def _move_to_position(self, target_stage, line: TrajectoryLine) -> None:
        """
        Moves the target stage to the starting position of the scan,
        the photodiode to the IN position and opens the table shutter.
        :param target_stage: The stage that is used for scanning.
        :param line: The full trajectory line.
        """
        # Move the stage to position
        caput(target_stage, float(line.trj_positions[0]), wait=True)

    def auto_centering_positions(self, step: float):
        positions = []
        starting_position = 90

        if step is not None:
            positions = [
                float(starting_position - step),
                float(starting_position),
                float(starting_position + step),
            ]
            positions.sort()

        return positions, starting_position

    def auto_centering_stages(self) -> (str, str):
        scanning_stage = self.stages.sample_vertical.value
        rotation_stage = self.stages.sample_omega.value

        return scanning_stage, rotation_stage
