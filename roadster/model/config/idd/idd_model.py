import time
from enum import Enum
from typing import List, Optional

from epics import caget, caput, caput_many

from roadster.model import MapModel, TrajectoryLine
from roadster.model.config import StationModel


class IDDStages(Enum):
    # Enumeration of required stages.
    sample_horizontal = "Horizontal", "13IDD:m98", "ST-Hor", "G6"
    sample_vertical = "Vertical", "13IDD:m97", "ST-Vert", "G1"
    sample_focus = "Focus", "13IDD:m99", "ST-Foc", "G3"
    sample_omega = "Omega", "13IDD:Auto1:m1"

    pinhole_horizontal = "Horizontal", "13IDD:m101", "PIN-Hor", "G5"
    pinhole_vertical = "Vertical", "13IDD:m100", "PIN-Vert", "G4"
    pinhole_position = "Pinhole Position", "13IDD:m22"

    mirror_ds = "Mirror DS", "13IDD:m103"
    mirror_us = "Mirror US", "13IDD:m102"

    microscope = "Microscope", "13IDD:m67"


class IDDScalers(Enum):
    # Enumeration with all available scalers.
    empty = "None", "None"
    s2 = "LVP_PD", "13IDD:scaler1.S2"
    s3 = "LVP_IC", "13IDD:scaler1.S3"
    s4 = "DAC_PD", "13IDD:scaler1.S4"
    s5 = "DAC_PD2", "13IDD:scaler1.S5"
    s6 = "IC_2", "13IDD:scaler1.S6"
    s7 = "IC_1", "13IDD:scaler1.S7"
    s8 = "I8", "13IDD:scaler1.S8"
    s9 = "Ketek", "13KETEK1:mca1.R0"

    s2_calc = "LVP_PD Calc", "13IDD:scaler1_cts1.B"
    s3_calc = "LVP_IC Calc", "13IDD:scaler1_cts1.C"
    s4_calc = "DAC_PD Calc", "13IDD:scaler1_cts1.D"
    s5_calc = "DAC_PD2 Calc", "13IDD:scaler1_cts2.A"
    s6_calc = "IC_2 Calc", "13IDD:scaler1_cts2.B"
    s7_calc = "IC_1 Calc", "13IDD:scaler1_cts2.C"
    s8_calc = "I8 Calc", "13IDD:scaler1_cts2.D"


class IDDMiscellaneous(Enum):
    table_shutter = "Table shutter", "13IDD:TableShutter"  # 0: Close, 1: Open
    photodiode = "Photodiode", "13IDD:Photodiode"  # 0: IN, 1: OUT
    xps_stop = "Stages stop", "13IDD_DAC_XPS16:allstop"
    station_stop = "Station stop", "13IDD:allstop"
    mirror_stop = "Mirror stop", "13Mirror:allstop"
    pd_count = "Photodiode count", "13IDD:scaler1.CNT"
    ketek_count = "Ketek count", "13KETEK1:mca1EraseStart"
    pd_count_time = "Photodiode count time", "13IDD:scaler1.TP"
    pd_count_type = "Scaler count type", "13IDD:scaler1.CONT"
    mcs_control_channels = "Channels to use", "13IDD:MCS1:NuseAll"
    mcs_erase_start = "Erase start", "13IDD:MCS1:EraseStart"
    mcs_stop = "Stop acquiring", "13IDD:MCS1:StopAll"
    mcs_channel = "Array channel", "13IDD:MCS1:mca4"
    mcs_ch_advance = "Channel advance source", "13IDD:MCS1:ChannelAdvance"
    energy = "Energy", "13IDA:CDEn:E_RBV"
    current = "Ring current", "S:SRcurrentAI"
    hutch = "Hutch status", "PA:13ID:STA_D_SRCHD_TO_B"


class IDDXps(Enum):
    host = "10.54.160.71"
    username = "Administrator"
    password = "Administrator"


class IDDDirectories(Enum):
    save_location = "data/"


class IDDModel(StationModel):
    name = "13-ID-D"
    base_dir = "T:/dac_user/2026/IDD_2026-2/"

    stages = IDDStages
    scalers = IDDScalers
    miscellaneous = IDDMiscellaneous
    xps = IDDXps

    _expert_pwd = "Pilatus2"

    def stop_all(self) -> None:
        """Implements the stop_all method for 13ID-D"""
        caput_many(
            [
                self.miscellaneous.mirror_stop.value[1],
                self.miscellaneous.station_stop.value[1],
                self.miscellaneous.xps_stop.value[1],
                self.miscellaneous.mcs_stop.value[1],
            ],
            [1, 1, 1, 1],
        )

    # TODO: Make inputs more specific.
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
        caput(self.miscellaneous.table_shutter.value[1], 0)
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
        caput(self.miscellaneous.table_shutter.value[1], 1)

        if not centering:
            # Move photodiode out
            caput(self.miscellaneous.photodiode.value[1], 1)
            time.sleep(2)

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

        # Check 13ID-D mirrors
        if not self._check_mirrors():
            return False

        # Check 13ID-D microscope
        if not self._check_microscope():
            return False

        # Check for stage limits based on map positions
        if not self._check_stage_limits(target_stage, scan.lines):
            return False

        return True

    def check_beam_hutch_status(self) -> bool:
        """Implements the check_beam_status method for the 13-ID-D station."""
        # Check hutch.
        if caget(self.miscellaneous.hutch.value[1]) == 0:
            return False

        # Check for beam.
        if caget(self.miscellaneous.current.value[1]) < 10:
            return False

        return True

    def _check_mirrors(self) -> bool:
        """
        Checks if the mirrors are in the scanning position.
        :return: In case of errors it returns False.
        """
        ds_position = round(caget(self.stages.mirror_ds.value[1]))
        us_position = round(caget(self.stages.mirror_us.value[1]))

        if not caget(self.stages.mirror_ds.value[1] + ".DMOV") == 1:
            print("DS mirror is moving.")
            return False
        elif ds_position != -180:
            print("DS mirror is not out.")
            return False

        if not caget(self.stages.mirror_us.value[1] + ".DMOV") == 1:
            print("US mirror is moving.")
            return False
        elif us_position != -180:
            print("US mirror is not out.")
            return False

        return True

    def _check_microscope(self) -> bool:
        """
        Checks if the microscope is in the IN position.
        :return: In case of errors it returns False.
        """
        microscope_position = round(caget(self.stages.microscope.value[1]))

        if not caget(self.stages.microscope.value[1] + ".DMOV") == 1:
            print("The microscope is moving.")
            return False
        elif microscope_position != -140:
            print("The microscope is not out.")
            return False

        return True

    def _move_to_position(self, target_stage, line: TrajectoryLine) -> None:
        """
        Moves the target stage to the starting position of the scan,
        the photodiode to the IN position and opens the table shutter.
        :param target_stage: The stage that is used for scanning.
        :param line: The full trajectory line.
        """
        # Move the stage to position
        caput(target_stage, float(line.trj_positions[0]), wait=True)

        # Move the photodiode IN
        caput(self.miscellaneous.photodiode.value[1], 0)
        time.sleep(2)

    def auto_centering_positions(self, step: float):
        positions = []
        starting_position = 0

        if step is not None:
            positions = [
                float(starting_position - step),
                float(starting_position),
                float(starting_position + step),
            ]
            positions.sort()

        return positions, starting_position

    def auto_centering_stages(self) -> (str, str):
        scanning_stage = self.stages.sample_horizontal.value
        rotation_stage = self.stages.sample_omega.value

        return scanning_stage, rotation_stage
