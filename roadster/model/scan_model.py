from typing import List
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from roadster.model import TrajectoryLine, TrajectoryDirection
from roadster.model import MapModel, SingleMap, DoubleMap


class ScanModes(Enum):
    """Represents the available scanning modes."""

    step = "Step"
    fly = "Fly"


class ScanTypes(Enum):
    """Represents the available scan types."""

    single = "Single"
    # double = "2D"  # TODO: Not currently implemented.


class ScanProc(Enum):
    Single = "Single"
    Centering = "Centering"
    Pinhole = "Pinhole"


class ScanModel:
    """Represents a scan that contains a trajectory map a scan type and a way to scan."""

    def __init__(self) -> None:
        self.direction = TrajectoryDirection
        self.scan_modes = ScanModes
        self.scan_types = ScanTypes

    @staticmethod
    def create_trajectory(
        trj_range: float,
        mid_position: float,
        direction: TrajectoryDirection = TrajectoryDirection.Forward,
        step: float = 0.001,
        all_positions: bool = True,
    ) -> TrajectoryLine:
        """
        Creates and returns a single trajectory line.

        :param trj_range: The trajectory range divided by two.
        :param mid_position: The center position of the trajectory.
        :param direction: The direction that the trajectory will run.
        :param step: The step size of the trajectory. Default value is 0.001.
        :param all_positions: Set to false to only create the edge positions of the trajectory. Default is true.
        :return: The trajectory line.
        """
        trj = TrajectoryLine(
            trj_step=step,
            trj_range=trj_range,
            trj_mid=mid_position,
            trj_direction=direction,
            trj_all_positions=all_positions,
        )
        return trj

    @staticmethod
    def create_map(
        lines: List[TrajectoryLine],
        exposure_time: float,
        delay: float = 0.0,
        single: bool = True,
        single_line: TrajectoryLine = None,
    ) -> MapModel:
        """
        Creates and returns a map of trajectories.

        :param lines: The available trajectories.
        :param exposure_time: Exposure time.
        :param delay: Total delay that exists between steps and at the start of the scan.
        :param single: Changes between Single and 2D map.
        :param single_line: The additional trajectory for the 2D map.
        :return: MapModel -> Single or double map.
        """
        if single:
            trj_map = SingleMap(
                lines=lines, exposure_time=exposure_time, additional_delay=delay
            )
        else:
            trj_map = DoubleMap(
                lines=lines,
                exposure_time=exposure_time,
                additional_delay=delay,
                additional_trj=single_line,
            )
        return trj_map

    def create_scan(
        self,
        exposure: float,
        trj_range: float,
        center: float,
        direction: int = 1,
        step: float = 0.001,
        single: bool = True,
    ) -> MapModel:

        # TODO: Fix return types.
        if direction is not None:

            # Set direction
            if direction == 2:
                direction = self.direction.Backwards
            else:
                direction = self.direction.Forward

            # TODO: Add support for multiple trajectories.
            # Create trajectories
            trj = []

            if single:
                trj.append(
                    self.create_trajectory(
                        trj_range=trj_range,
                        mid_position=center,
                        direction=direction,
                        step=step,
                        all_positions=True,
                    )
                )

            # Create map
            trj_map = self.create_map(
                lines=trj,
                exposure_time=exposure,
                delay=0,  # TODO: Add delay option (PD and step * nsteps)
            )

            return trj_map


class ScanThread(ThreadPoolExecutor):
    def __init__(self, method, *args, **kwargs):
        super(ScanThread, self).__init__()

        self.submit(method, *args, **kwargs)
