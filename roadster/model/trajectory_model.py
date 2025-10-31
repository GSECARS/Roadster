import math
import numpy as np

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List


class TrajectoryDirection(Enum):
    """Represents trajectory moving direction."""

    Forward = auto()
    Backwards = auto()


@dataclass(frozen=True)
class TrajectoryLine:
    """
    Represents a trajectory line.

    :trj_step parameter: The step size in mm.
    :trj_range parameter: The half range of the trajectory. e.g. for +-10 range: input -> 10
    :trj_mid parameter: The middle position of the trajectory. Usually the current stage position.
    :trj_direction parameter: Default direction is Forward.
    :trj_all_positions parameter: If set to false only the edge positions are created.
    """

    trj_step: float = field(
        init=True, repr=True, compare=False, metadata={"unit": "millimeter"}
    )
    trj_range: float = field(
        init=True, repr=True, compare=False, metadata={"unit": "millimeter"}
    )
    trj_mid: float = field(
        init=True, repr=True, compare=False, metadata={"unit": "millimeter"}
    )
    trj_direction: TrajectoryDirection = field(
        default=TrajectoryDirection.Forward, init=True, repr=True, compare=False
    )
    trj_all_positions: bool = field(default=True, init=True, repr=True, compare=False)

    trj_points: int = field(init=False, repr=True, compare=False)
    trj_positions: List = field(init=False, repr=True, compare=False)

    def __post_init__(self) -> None:
        # Round up trajectory range input to 3 decimals.
        object.__setattr__(
            self, "trj_range", math.ceil(self.trj_range * (10 ** 4)) / float(10 ** 4)
        )

        # Get the trajectory points.
        object.__setattr__(self, "trj_points", self._get_points_number())

        # Get the position list for the trajectory points.
        object.__setattr__(self, "trj_positions", self._get_positions_list())

    def _get_points_number(self) -> int:
        """Returns the number of points for a trajectory."""
        points = 1

        if self.trj_all_positions:
            if self.trj_step > 0:
                points = int(
                    round(1 + (abs(self.trj_range * 2) / abs(self.trj_step)), 0)
                )

        return points

    def _get_positions_list(self) -> List[float]:
        """Returns a list of positions for the trajectory."""
        positions = []

        # Set the range.
        min_range = self.trj_mid - self.trj_range
        max_range = self.trj_mid + self.trj_range

        # Set direction.
        direction = self.trj_direction.value

        # Create the positions list.
        if self.trj_all_positions:
            if direction == TrajectoryDirection.Forward.value:
                for i in np.linspace(min_range, max_range, self.trj_points):
                    positions.append(round(i, 4))
            elif direction == TrajectoryDirection.Backwards.value:
                for i in np.linspace(max_range, min_range, self.trj_points):
                    positions.append(round(i, 4))
        else:
            if direction == TrajectoryDirection.Forward.value:
                positions.append(min_range)
                positions.append(max_range)
            elif direction == TrajectoryDirection.Backwards.value:
                positions.append(max_range)
                positions.append(min_range)

        return positions
