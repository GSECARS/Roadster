from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class OverlayModel:
    """Represents an overlay plot with its configuration."""
    
    filename: str
    x_data: List[float]
    y_data: List[float]
    color: Tuple[int, int, int] = (255, 0, 0)  # RGB tuple, default red
    shift: float = 0.0  # X-axis shift
    offset: float = 0.0  # Y-axis offset
    scale: float = 1.0
    visible: bool = True
    plot_item = None  # Will store the pyqtgraph PlotDataItem reference
    
    def get_transformed_x_data(self) -> List[float]:
        """Returns x_data with shift applied."""
        return [x + self.shift for x in self.x_data]
    
    def get_transformed_y_data(self) -> List[float]:
        """Returns y_data with scale and offset applied."""
        return [y * self.scale + self.offset for y in self.y_data]
