from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from epics import caget
from typing import List, Optional

from roadster.model import MapModel, TrajectoryLine


@dataclass(frozen=True)
class StationModel(ABC):
    """Abstract class for stations."""

    name: str = field(init=False, repr=True, compare=False)
    base_dir: str = field(init=False, repr=True, compare=False)

    stages: Enum = field(init=False, repr=True, compare=False)
    scalers: Enum = field(init=False, repr=True, compare=False)
    miscellaneous: Enum = field(init=False, repr=True, compare=False)
    directories: Enum = field(init=False, repr=True, compare=False)

    _aborted: bool = field(init=True, repr=False, default=False, compare=False)
    _trj_running: bool = field(init=False, repr=False, compare=False, default=False)
    _trj_aborted: bool = field(init=False, repr=False, compare=False, default=False)

    _expert_mode: bool = field(init=False, repr=False, compare=False, default=False)
    _expert_pwd: str = field(init=False, repr=False, compare=False, default=None)

    @abstractmethod
    def stop_all(self) -> None:
        """Used to stop selected motion on a station."""

    @abstractmethod
    def prepare_for_scan(
        self, target_stage, scan: MapModel, expert: Optional[bool] = False
    ) -> bool:
        """Prepares the station for a scanning procedure."""

    @abstractmethod
    def prepare_shutter(self):
        """Opens the station shutter."""

    @abstractmethod
    def prepare_for_auto_centering(
        self, positions: List[float], expert: Optional[bool] = False
    ) -> bool:
        """Prepares the station for an rotation center procedure"""

    @abstractmethod
    def restore_station(
        self, target_stage, center: float, centering: Optional[bool] = False
    ) -> None:
        """Restores everything back to the normal state, before the scan started."""

    @abstractmethod
    def _check_station_status(self, *args, **kwargs) -> bool:
        """Used to run the methods specific to each station."""

    @abstractmethod
    def check_beam_hutch_status(self) -> bool:
        """Checks if the hutch is open and if there is beam."""

    @staticmethod
    def _check_stage_limits(target_stage, lines: List[TrajectoryLine]) -> bool:
        """
        Makes sure that all the target positions are within the set limits of the target stage.
        :param target_stage: The stage pv without the .VAL extension.
        :param lines: All available trajectory lines.
        :return: Returns false if the target positions are outside of the stage's limits.
        """
        for line in lines:
            # Check low limit
            if min(line.trj_positions) < caget(target_stage + ".LLM"):
                return False

            # Check high limit
            if max(line.trj_positions) > caget(target_stage + ".HLM"):
                return False

        return True

    @abstractmethod
    def auto_centering_positions(self, *args, **kwargs) -> List[float]:
        """Used to define the positions need for the automatic center of rotation procedure."""

    @abstractmethod
    def auto_centering_stages(self) -> (str, str):
        """Used to provide the stages required for the automatic center of rotation procedure."""

    @property
    def trj_running(self):
        return self._trj_running

    @property
    def trj_aborted(self):
        return self._trj_aborted
    
    @property
    def aborted(self):
        return self._aborted

    @property
    def expert_mode(self):
        return self._expert_mode

    @property
    def expert_pwd(self):
        return self._expert_pwd

    @trj_running.setter
    def trj_running(self, value):
        if isinstance(value, bool):
            object.__setattr__(self, "_trj_running", value)

    @trj_aborted.setter
    def trj_aborted(self, value):
        if isinstance(value, bool):
            object.__setattr__(self, "_trj_aborted", value)

    @aborted.setter
    def aborted(self, value):
        if isinstance(value, bool):
            object.__setattr__(self, "_aborted", value)

    @expert_mode.setter
    def expert_mode(self, value):
        if isinstance(value, bool):
            object.__setattr__(self, "_expert_mode", value)
