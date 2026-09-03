import datetime

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

from roadster.model import TrajectoryLine


@dataclass(frozen=True)
class MapModel(ABC):
    """
    Represents a map with at least one trajectory line.

    :lines parameter: List[TrajectoryLine] -> At least one trajectory line required, there is no max amount of lines.
    :exposure_time parameter: float -> The exposure time for the map.
    :additional_delay parameter: Optional[float] -> Additional delay in seconds.
    """

    lines: List[TrajectoryLine] = field(init=True, repr=True, compare=False)
    exposure_time: float = field(init=True, repr=True, compare=False)
    additional_delay: Optional[float] = field(
        init=True, default=0.0, repr=True, compare=False
    )
    points: int = field(init=False, repr=True, compare=False)
    estimated_time: str = field(init=False, repr=True, compare=False)

    @abstractmethod
    def __post_init__(self) -> None:
        """Runs after the init method."""

    @abstractmethod
    def _get_total_points_number(self) -> int:
        """Returns the complete number of points for the map."""

    @abstractmethod
    def _get_estimated_time(self) -> datetime.timedelta:
        """Returns the estimated time of the complete map as a string."""


class SingleMap(MapModel):
    """Used to create simple maps."""

    def __post_init__(self) -> None:
        # Get the total number of points.
        object.__setattr__(self, "points", self._get_total_points_number())

        # Get the total estimated time for the map.
        object.__setattr__(self, "estimated_time", self._get_estimated_time())

    def _get_total_points_number(self) -> int:
        total_points = 0
        # Get the points for each trajectory.
        for line in self.lines:
            total_points += line.trj_points

        return total_points

    def _get_estimated_time(self) -> datetime.timedelta:
        # Calculate the total time.
        total_time = self.additional_delay + (self.points * abs(self.exposure_time))

        # Return total time in seconds.
        return datetime.timedelta(seconds=total_time)


@dataclass(frozen=True)
class DoubleMap(MapModel):
    """Used to create two-dimensional maps."""

    additional_trj: TrajectoryLine = field(
        init=True, default_factory=[], repr=True, compare=True
    )

    def __post_init__(self) -> None:
        # Get the total number of points.
        object.__setattr__(self, "points", self._get_total_points_number())

        # Get the total estimated time for the map.
        object.__setattr__(self, "estimated_time", self._get_estimated_time())

    def _get_total_points_number(self) -> int:
        total_points = 0
        # Get the points for each trajectory.
        for line in self.lines:
            total_points += line.trj_points

        total_points += self.additional_trj.trj_points

        return total_points

    def _get_estimated_time(self) -> datetime.timedelta:
        # Calculate the total time.
        total_time = self.additional_delay + (self.points * abs(self.exposure_time))

        # Return total time in seconds.
        return datetime.timedelta(seconds=total_time)
