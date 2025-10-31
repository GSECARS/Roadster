import os
import pyqtgraph as pg
import numpy as np
import datetime
from qtpy import QtWidgets, QtCore
from typing import Optional, List

from roadster.view.drawing import VLine
from roadster.model import MapModel


pg.setConfigOption("antialias", True)
pg.setConfigOption("useOpenGL", False)
pg.setConfigOption("leftButtonPan", False)


class TestPlotWidget(QtWidgets.QWidget):

    graphics_layout: pg.GraphicsLayoutWidget
    _view_box: pg.ViewBox
    _plot_widget: pg.PlotItem
    _main_plot_item: pg.PlotDataItem
    _legend: pg.LegendItem

    def __init__(self) -> None:
        super(TestPlotWidget, self).__init__()

        # Lines
        self._lower_line = None
        self._upper_line = None
        self._marker_line = None

        # Data arrays
        self._x_list = []
        self._y_list = []
        self._dx = []
        self._dxy = []

        # Pens
        self._main_pen = None
        self._main_marker_pen = None
        self._secondary_marker_pen = None
        self._hover_pen = None

        # Motors
        self.target_position_motor = []

        # Additional widgets
        self._coord_label = QtWidgets.QLabel()
        self._marker_coord_label = QtWidgets.QLabel()
        self._calculated_size_label = QtWidgets.QLabel()
        self.btn_peak = QtWidgets.QPushButton("Peak")
        self.btn_derivative = QtWidgets.QPushButton("Derivative")
        self.btn_center = QtWidgets.QPushButton("Center")
        self.btn_invert = QtWidgets.QPushButton("Invert")
        self.btn_move = QtWidgets.QPushButton("Move")
        self.btn_clear = QtWidgets.QPushButton("Clear")
        self.btn_load_file = QtWidgets.QPushButton("Load")

        # Coordinates
        self._coord_x = None
        self._coord_y = None
        self._calculated_size = None
        self.marker_coords = None
        self.upper_coords = None
        self.lower_coords = None

        # Status variables
        self.derivative_mode = False
        self.inverted_mode = False

        # Run configuration methods
        self._init_gfx()
        self._configure_pens()
        self._configure_infinite_lines()
        self._configure_labels()
        self._connect_local_widgets()
        self._init_plot()

        self._layout_plot()

    def _init_gfx(self) -> None:
        self.graphics_layout = pg.GraphicsLayoutWidget()
        self._plot_widget = self.graphics_layout.addPlot()
        self._view_box = self._plot_widget.vb

        # Disable default context menu and hide buttons
        self._view_box.setMenuEnabled(False)
        self._plot_widget.setMenuEnabled(False)
        self._plot_widget.hideButtons()

        # Enable grid
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # Set axis titles
        self._plot_widget.setLabel(axis="left", text="Counts")
        if len(self.target_position_motor) < 1:
            self._plot_widget.setLabel(axis="bottom", text="Motor positions")
        else:
            self._plot_widget.setLabel(
                axis="bottom",
                text=f"{self.target_position_motor[0]} ({self.target_position_motor[1]})",
            )

        # Set plot area background color
        self.graphics_layout.setBackground("#2B2B2B")

    def _configure_pens(self) -> None:
        """Configuration of pen to be used for the infinite lines."""
        # TODO: Make it user adjustable.
        self._main_pen = pg.mkPen(width=2)
        self._main_marker_pen = pg.mkPen(width=2, color=(194, 21, 119))
        self._secondary_marker_pen = pg.mkPen(width=2, color=(11, 158, 84))
        self._hover_pen = pg.mkPen(width=2, color=(200, 180, 85))

    def _configure_infinite_lines(self) -> None:
        """Configures the centering infinite lines."""
        # Configuration values
        angle = 90
        movable = True
        label = "x{value:0.3f}"
        pen = self._secondary_marker_pen
        hover_pen = self._hover_pen
        label_options = {
            "position": 0.15,
            "color": (230, 230, 230),
            "fill": (255, 255, 255, 0),
            "movable": False,
        }

        # Set configuration values
        self._lower_line = pg.InfiniteLine(
            angle=angle,
            label=label,
            movable=movable,
            pen=pen,
            hoverPen=hover_pen,
            labelOpts=label_options,
        )
        self._upper_line = pg.InfiniteLine(
            angle=angle,
            label=label,
            movable=movable,
            pen=pen,
            hoverPen=hover_pen,
            labelOpts=label_options,
        )
        self._marker_line = pg.InfiniteLine(
            angle=angle,
            label=label,
            movable=movable,
            pen=self._main_marker_pen,
            hoverPen=hover_pen,
            labelOpts=label_options,
        )

    def _configure_labels(self) -> None:
        # Set size
        self._coord_label.setFixedWidth(150)
        self._marker_coord_label.setFixedWidth(150)
        self._calculated_size_label.setFixedWidth(150)

        # Set text
        self._marker_coord_label.setText("Marker: None")
        self._calculated_size_label.setText("Size: None")

    def _init_plot(self) -> None:
        self._main_plot_item = pg.PlotDataItem(
            self._x_list,
            self._y_list,
            pen=self._main_pen,
            symbol="x",
            symbolBrush=0.3,
            name="green",
        )

        self._plot_widget.addItem(self._main_plot_item)

    def update_plot(
        self,
        x: float,
        y: float,
        auto_scale: Optional[bool] = False,
        motor_name: Optional[str] = None,
        pv_name: Optional[str] = None,
    ) -> None:
        """
        Update the reference line values and re-scale the plot area.
        :param x: List of positions.
        :param y: List of counts.
        :param auto_scale: Set to true, automatically scales the plot area based on the min and max values of the plot.
        :param motor_name: The name of the motor that is used to provide positions for the X axis.
        :param pv_name: The pv name of the motor.
        """
        self._x_list.append(x)
        self._y_list.append(y)

        if auto_scale:
            self.scale_plot(self._x_list, self._y_list)

        self._main_plot_item.setData(self._x_list, self._y_list)

        # Set target motor and X axis title
        if motor_name and pv_name:
            self._plot_widget.setLabel(
                axis="bottom", text=f"{motor_name.capitalize()} ({pv_name})"
            )

            self.target_position_motor.append(motor_name.capitalize())
            self.target_position_motor.append(pv_name)

    def update_plot_array(
        self,
        x_list,
        y_list,
        auto_scale: Optional[bool] = False,
        pv_name: Optional[str] = None,
    ):
        self._x_list = []
        self._y_list = []

        for i in range(len(y_list)):
            self._x_list.append(x_list[i])
            self._y_list.append(y_list[i])

        if auto_scale:
            self.scale_plot(self._x_list, self._y_list)

        self._main_plot_item.setData(self._x_list, self._y_list)

        # Set target motor and X axis title
        if pv_name is not None:
            self._plot_widget.setLabel(axis="bottom", text=f"{pv_name}")

            self.target_position_motor.append("Unknown")
            self.target_position_motor.append(pv_name)

    def save_to_file(
        self,
        station: str,
        base_dir: str,
        filename: str,
        stage: str,
        scan: MapModel,
        mode: str,
        center: float,
        energy: float,
        current: float,
        aborted: bool,
        scaler: Optional[List[str]] = None,
        correction_scaler: Optional[List[str]] = None,
        raw_data: Optional[List[float]] = None,
    ):
        # Create filename
        full_dir = base_dir + filename + "_%s.csv"

        # Exponential search for files
        j = 1
        while os.path.exists(full_dir % j):
            j += 1

        # Narrow down interval
        a, b = (j // 2, j)
        while a + 1 < b:
            c = (a + b) // 2  # interval midpoint
            a, b = (c, b) if os.path.exists(full_dir % c) else (a, c)

        # Create file or open existing
        with open(full_dir % b, "w") as collection_file:

            # Create file headers
            collection_file.write(
                f"# Station: {station} | Timestamp: {datetime.datetime.now()}\n"
                f"# Energy: {round(energy, 3)} eV | Ring current: {round(current, 3)} mA\n"
                f"# Scanned motor: {stage} | Scan mode: {mode} | Center position {center}\n"
                f"# Range: {scan.lines[0].trj_range * 2} mm | Exposure: {scan.exposure_time} sec | "
                f"# Step: {scan.lines[0].trj_step} mm\n"
            )

            if scaler is not None:
                if scaler[1] != "None":
                    collection_file.write(f"# Scaler: {scaler[0]} ({scaler[1]})\n")

            if correction_scaler is not None:
                if correction_scaler[1] != "None":
                    collection_file.write(
                        f" Correction Scaler: ({correction_scaler[1]})\n\n"
                    )
            else:
                collection_file.write("\n")

            if aborted:
                scan_status = "Aborted"
            else:
                scan_status = "Completed"

            collection_file.write(f"# Scan status: {scan_status}\n\n")

            if correction_scaler is not None:
                collection_file.write("#Positions,Raw,Corrected\n")

                # Write positions and counts
                for i in range(0, len(self._x_list) - 1):
                    collection_file.write(
                        f"{self._x_list[i]},{raw_data[i]},{self._y_list[i]}\n"
                    )
            else:
                collection_file.write("#Positions,Counts\n")

                # Write positions and counts
                for i in range(0, len(self._x_list) - 1):
                    collection_file.write(f"{self._x_list[i]},{self._y_list[i]}\n")

    def invert_plot(self) -> None:
        """Inverts plot preview by inverting the Y axis."""
        # Check inverted status
        if not self.inverted_mode:
            self._plot_widget.getViewBox().invertY(True)
            self.inverted_mode = True
        else:
            self._plot_widget.getViewBox().invertY(False)
            self.inverted_mode = False

    def derivative_plot(self) -> (float, float):
        """Plots the derivative of the x and y arrays of the plot."""

        # Check for derivative status
        if not self.derivative_mode:
            # Calculate derivative
            self._dxy = np.diff(self._y_list) / np.diff(self._x_list)
            self._dx = (np.array(self._x_list)[:-1] + np.array(self._x_list)[1:]) / 2

            # Set derivative status
            self.derivative_mode = True

            # Set arrays to use
            array_x, array_y = self._dx, self._dxy

        else:
            # Set derivative status
            self.derivative_mode = False

            # Set arrays to use
            array_x, array_y = self._x_list, self._y_list

        # Update plot line
        self._main_plot_item.setData(array_x, array_y)

        self.scale_plot(array_x, array_y)

        return array_x, array_y

    def scale_plot(self, array_x: List[float], array_y: List[float]) -> None:
        """
        Used to automatically scale the plot widget.
        :param array_x: The positions array.
        :param array_y: The counts array.
        """
        self._plot_widget.setXRange(min(array_x), max(array_x), padding=0.1)
        self._plot_widget.setYRange(min(array_y), max(array_y), padding=0.1)

    def center_plot(self) -> float:

        # Calculate derivative
        dxy = np.diff(self._y_list) / np.diff(self._x_list)
        dx = (np.array(self._x_list)[:-1] + np.array(self._x_list)[1:]) / 2

        # Get min and max
        x_min = dx[np.where(dxy == np.min(dxy))][0]
        x_max = dx[np.where(dxy == np.max(dxy))][0]

        self._upper_line.setPos(x_max)
        self.upper_coords = x_max
        if self._upper_line in self._plot_widget.items:
            self._plot_widget.removeItem(self._upper_line)
        self._plot_widget.addItem(self._upper_line)

        self._lower_line.setPos(x_min)
        self.lower_coords = x_min
        if self._lower_line in self._plot_widget.items:
            self._plot_widget.removeItem(self._lower_line)
        self._plot_widget.addItem(self._lower_line)

        # Get the center
        center = self._calculate_center(x_min, x_max)

        return center

    def _calculate_center(self, min_value, max_value) -> float:
        # Calculate center
        center = np.round((max_value + min_value) / 2, decimals=4)

        # Set the marker
        self._marker_line.setPos(center)
        if self._marker_line in self._plot_widget.items:
            self._plot_widget.removeItem(self._marker_line)
        self._plot_widget.addItem(self._marker_line)

        # Calculate the size
        self._calculated_size = abs(
            self._upper_line.pos()[0] - self._lower_line.pos()[0]
        )
        # Set the size label
        self._calculated_size_label.setText(
            f"Size: {round(self._calculated_size, 4)} mm"
        )

        return center

    def find_peak(self) -> float:

        if self._x_list and self._y_list:
            x_peak_position = self._x_list[self._y_list.index(max(self._y_list))]

            if self._marker_line not in self._plot_widget.items:
                self._plot_widget.addItem(self._marker_line)

            self._marker_line.setPos(x_peak_position)
            self._update_marker_coordinates()

            return x_peak_position

    def clear_plot(self) -> None:
        """
        Clears the markers of the plot widgets, by removing all infinite lines.
        """
        # Remove infinite lines.
        infinite_lines = [self._lower_line, self._upper_line, self._marker_line]
        for line in infinite_lines:
            if line in self._plot_widget.items:
                self._plot_widget.removeItem(line)

        # Reset coords and size
        self.marker_coords = None
        self._calculated_size = None
        self._marker_coord_label.setText(f"Marker: {self.marker_coords} mm")
        self._calculated_size_label.setText("Size: None")

    def reset_plot(self) -> None:
        """
        Clears the data arrays of the plot and
        restores all status variables to default.
        Resets the axis titles to generic titles.
        """
        # Clear data arrays and updates the plot.
        self._x_list = []
        self._y_list = []
        self._main_plot_item.setData(self._x_list, self._y_list)

        # Clear markers
        self.clear_plot()

        # Reset status variables
        self.derivative_mode = False
        self.inverted_mode = False

    def mouse_moved(self, event) -> None:
        """
        Triggers when the mouse is moving over the plot area.
        :param event: Current mouse event.
        """
        # Get mouse coordinates
        coordinates = self._plot_widget.vb.mapSceneToView(event[0])

        # Update coordinate values
        self._coord_x = coordinates.x()
        self._coord_y = coordinates.y()

        # Update the marker line coordinate values
        if self.marker_coords != round(self._marker_line.pos()[0], 4):
            self._update_marker_coordinates()

        # Update coordinates label
        self._coord_label.setText(
            f"X: {round(self._coord_x, 4)}, Y: {round(self._coord_y, 4)}"
        )

    def mouse_clicked(self, event) -> None:
        """
        Triggers on single mouse click.
        :param event: Current mouse event.
        """
        # Check for modifier keys
        modifiers = QtWidgets.QApplication.keyboardModifiers()

        line = None
        if event.button() == QtCore.Qt.LeftButton:

            # Lower line (Ctrl + Left Mouse Click)
            if modifiers == QtCore.Qt.ControlModifier:
                self._lower_line.setPos(self._coord_x)
                self.lower_coords = self._coord_x
                line = self._lower_line

            # Upper line (Alt + Left Mouse Click)
            elif modifiers == QtCore.Qt.AltModifier:
                self._upper_line.setPos(self._coord_x)
                self.upper_coords = self._coord_x
                line = self._upper_line

            else:
                self._marker_line.setPos(self._coord_x)
                line = self._marker_line
                self._update_marker_coordinates()

        if line:
            # Add updated infinite line
            if line in self._plot_widget.items:
                self._plot_widget.removeItem(line)
            self._plot_widget.addItem(line)

    def mouseDoubleClickEvent(self, event) -> None:
        """
        Triggers on mouse button double click.
        :param event: Current mouse event.
        """
        # Re-scale plot area on double right click.
        if event.button() == QtCore.Qt.RightButton:
            if not self.derivative_mode:
                self.scale_plot(self._x_list, self._y_list)
            else:
                self.scale_plot(self._dx, self._dxy)

    def keyPressEvent(self, event) -> None:
        """Triggers on key press to move the markers using the arrows by a predefined step."""
        modifiers = QtWidgets.QApplication.keyboardModifiers()

        arrow_step = abs(
            self._plot_widget.getAxis("bottom").range[1]
            - self._plot_widget.getAxis("bottom").range[0]
        )

        # Move positive.
        if event.key() == QtCore.Qt.Key_Right:

            # Main marker
            if modifiers == QtCore.Qt.AltModifier:
                arrow_step = round(arrow_step / 1000, 4)
            elif modifiers == QtCore.Qt.ControlModifier:
                arrow_step = round(arrow_step / 10, 4)
            else:
                arrow_step = round(arrow_step / 100, 4)

            self._marker_line.setPos(self.marker_coords + arrow_step)
            self._update_marker_coordinates()

        # Move negative.
        elif event.key() == QtCore.Qt.Key_Left:

            # Main marker
            if modifiers == QtCore.Qt.AltModifier:
                arrow_step = round(arrow_step / 1000, 4)
            elif modifiers == QtCore.Qt.ControlModifier:
                arrow_step = round(arrow_step / 10, 4)
            else:
                arrow_step = round(arrow_step / 100, 4)

            self._marker_line.setPos(self.marker_coords - arrow_step)
            self._update_marker_coordinates()

    def _update_marker_coordinates(self):
        """Used to update appropriate label with the latest marker coordinates."""
        if self._marker_line in self._plot_widget.items:
            self.marker_coords = round(self._marker_line.pos()[0], 4)
            self._marker_coord_label.setText(f"Marker: {self.marker_coords} mm")

    def update_target_stage(self, stage: list):
        # self.target_position_motor.clear()
        self.target_position_motor = []
        for item in stage:
            self.target_position_motor.append(item)
        self.target_position_motor = stage
        self._plot_widget.setLabel(axis="bottom", text=f"{stage[0]} ({stage[1]})")

    def recalculate_center(self):
        self._calculate_center(self._lower_line.pos(), self._upper_line.pos())

    def rescale_plot(self):
        self.scale_plot(self._x_list, self._y_list)

    @staticmethod
    def gaussian(a, b, x):
        return a * np.exp(-((x / (2 * b)) ** 2))

    def _connect_local_widgets(self) -> None:
        """Connects signals for the locally used widgets."""
        self._plot_widget.scene().sigMouseClicked.connect(self.mouse_clicked)

        self._lower_line.sigPositionChanged.connect(lambda: self.recalculate_center())
        self._upper_line.sigPositionChanged.connect(lambda: self.recalculate_center())

    def _layout_plot(self) -> None:
        """Basic plot and plot widgets layout."""

        # Plot toolbar layout
        status_layout = QtWidgets.QHBoxLayout()
        status_layout.addWidget(self._coord_label, alignment=QtCore.Qt.Alignment())
        status_layout.addStretch(1)
        status_layout.addWidget(VLine(), alignment=QtCore.Qt.Alignment())
        status_layout.addWidget(
            self._marker_coord_label, alignment=QtCore.Qt.Alignment()
        )
        status_layout.addStretch(1)
        status_layout.addWidget(VLine(), alignment=QtCore.Qt.Alignment())
        status_layout.addWidget(
            self._calculated_size_label, alignment=QtCore.Qt.Alignment()
        )
        status_layout.addStretch(1)

        tools_layout = QtWidgets.QHBoxLayout()
        tools_layout.addWidget(self.btn_invert, alignment=QtCore.Qt.Alignment())
        tools_layout.addWidget(self.btn_derivative, alignment=QtCore.Qt.Alignment())
        tools_layout.addWidget(self.btn_peak, alignment=QtCore.Qt.Alignment())
        tools_layout.addWidget(self.btn_center, alignment=QtCore.Qt.Alignment())
        tools_layout.addWidget(self.btn_clear, alignment=QtCore.Qt.Alignment())
        tools_layout.addWidget(self.btn_move, alignment=QtCore.Qt.Alignment())
        tools_layout.addWidget(self.btn_load_file, alignment=QtCore.Qt.Alignment())

        toolbar_layout = QtWidgets.QVBoxLayout()
        toolbar_layout.addLayout(status_layout)
        toolbar_layout.addLayout(tools_layout)

        # Main plot layout.
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.graphics_layout, alignment=QtCore.Qt.Alignment())
        layout.addLayout(toolbar_layout)
        self.setLayout(layout)
