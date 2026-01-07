import datetime
import os
from typing import List, Optional

import numpy as np
import pyqtgraph as pg
from epics import caget
from lmfit import Model, lineshapes
from qtpy import QtCore, QtGui, QtWidgets

from roadster.model import MapModel, OverlayModel, icon_path
from roadster.view.drawing import VLine

pg.setConfigOption("antialias", True)
pg.setConfigOption("useOpenGL", False)
pg.setConfigOption("leftButtonPan", False)


class BasePlotWidget(QtWidgets.QWidget, QtCore.QObject):

    new_file_saved: QtCore.Signal = QtCore.Signal(str)

    def __init__(self) -> None:
        super(BasePlotWidget, self).__init__(flags=QtCore.Qt.WindowFlags())

        # Basic graphics layout widget configuration.
        self._graphics_layout = pg.GraphicsLayoutWidget()
        self._plot_widget = self._graphics_layout.addPlot(row=0, col=0)

        # Lines
        self._reference_line = None
        self._lower_line = None
        self._upper_line = None
        self._marker_line = None

        # Motors
        self.target_position_motor = []
        self._current_plot_name = "Current Plot"  # Track the name for saving as overlay

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

        # Coordinates
        self._coord_x = None
        self._coord_y = None
        self._calculated_size = None
        self.marker_coords = None
        self.upper_coords = None
        self.lower_coords = None

        # Additional widgets
        self._coord_label = QtWidgets.QLabel()
        self._marker_coord_label = QtWidgets.QLabel()
        self._calculated_size_label = QtWidgets.QLabel()
        self.moved_by_label = QtWidgets.QLabel()
        self.delta_position_label = QtWidgets.QLabel()
        self.btn_peak = QtWidgets.QPushButton("Peak")
        self.btn_derivative = QtWidgets.QPushButton("Derivative")
        self.btn_center = QtWidgets.QPushButton("Center")
        self.btn_invert = QtWidgets.QPushButton("Invert")
        self.btn_move = QtWidgets.QPushButton("Move")
        self.btn_clear = QtWidgets.QPushButton("Clear")
        self.btn_load_file = QtWidgets.QPushButton()
        self.btn_previous_file = QtWidgets.QPushButton()
        self.btn_next_file = QtWidgets.QPushButton()
        
        # Overlay management widgets
        self.overlay_table = QtWidgets.QTableWidget()
        self.btn_add_overlay = QtWidgets.QPushButton("Add")
        self.btn_save_current = QtWidgets.QPushButton("Add as overlay")
        self.btn_clear_overlays = QtWidgets.QPushButton("Clear")
        self.lbl_shift_step = QtWidgets.QLabel("Shift step:")
        self.spin_shift_step = QtWidgets.QDoubleSpinBox()
        self.lbl_offset_step = QtWidgets.QLabel("Offset step:")
        self.spin_offset_step = QtWidgets.QDoubleSpinBox()
        self.lbl_scale_step = QtWidgets.QLabel("Scale step:")
        self.spin_scale_step = QtWidgets.QDoubleSpinBox()
        self.overlays: List[OverlayModel] = []

        # Status variables
        self.derivative_mode = False
        self.inverted_mode = False

        # Create signal proxy to use for coordinates.
        self.proxy = pg.SignalProxy(
            self._plot_widget.scene().sigMouseMoved, rateLimit=60, slot=self.mouse_moved
        )

        # Run configuration methods
        self._configure_pens()
        self._configure_plot_area()
        self._configure_infinite_lines()
        self._configure_labels()
        self._configure_overlay_table()
        self._connect_local_widgets()
        self._set_object_names()
        self._configure_buttons()
        self._layout_plot()

    def _set_object_names(self) -> None:
        self.btn_move.setObjectName("btn-move")
        self.btn_peak.setObjectName("btn-main")
        self.btn_derivative.setObjectName("btn-main")
        self.btn_center.setObjectName("btn-main")
        self.btn_invert.setObjectName("btn-main")
        self.btn_clear.setObjectName("btn-main")
        self.btn_previous_file.setObjectName("btn-icon")
        self.btn_load_file.setObjectName("btn-icon")
        self.btn_next_file.setObjectName("btn-icon")

    def toggle_plot_buttons(self, state: bool) -> None:
        buttons = [
            self.btn_move, self.btn_peak, self.btn_derivative, self.btn_center,
            self.btn_invert, self.btn_clear, self.btn_previous_file,
            self.btn_load_file, self.btn_next_file,
        ]
        [button.setEnabled(not state) for button in buttons]

    def _configure_pens(self) -> None:
        """Configuration of pen to be used for the infinite lines."""
        # TODO: Make it user adjustable.
        self._main_pen = pg.mkPen(width=2)
        self._main_marker_pen = pg.mkPen(width=2, color=(194, 21, 119))
        self._secondary_marker_pen = pg.mkPen(width=2, color=(11, 158, 84))
        self._hover_pen = pg.mkPen(width=2, color=(200, 180, 85))

    def _configure_plot_area(self) -> None:
        """Initial configuration of the plot widgets."""
        # Set reference line
        self._reference_line = self._plot_widget.plot(
            self._x_list,
            self._y_list,
            pen=self._main_pen,
            symbol="x",
            symbolBrush=0.3,
            name="green",
        )

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

        # Disable default context menu
        self._plot_widget.setMenuEnabled(False)
        self._plot_widget.getViewBox().setMenuEnabled(False)

        # Set plot area background color
        self._graphics_layout.setBackground("#2B2B2B")

    def _configure_infinite_lines(self) -> None:
        """Configures the centering infinite lines."""
        # Configuration values
        angle = 90
        movable = True
        label = "x{value:0.4f}"
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
        self.moved_by_label.setFixedWidth(150)
        self.delta_position_label.setFixedWidth(150)

        # Set text
        self._marker_coord_label.setText("Marker: None")
        self._calculated_size_label.setText("Size: None")
        self.moved_by_label.setText("Moved: None")
        self.delta_position_label.setText("Delta: None")

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

        self._reference_line.setData(self._x_list, self._y_list)

        # Set target motor and X axis title
        if motor_name and pv_name:
            self._plot_widget.setLabel(
                axis="bottom", text=f"{motor_name.capitalize()} ({pv_name})"
            )

            self.target_position_motor.append(motor_name.capitalize())
            self.target_position_motor.append(pv_name)
            
            # Generate preview name for unsaved scan (same format as save_to_file)
            self._current_plot_name = pv_name.replace(":", ".")

        # QtWidgets.QApplication.ProcessEvents()

    def update_plot_array(
        self,
        x_list,
        y_list,
        auto_scale: Optional[bool] = False,
        pv_name: Optional[str] = None,
    ):
        # self._x_list.clear()
        # self._y_list.clear()
        self._x_list = []
        self._y_list = []

        for i in range(len(y_list)):
            self._x_list.append(x_list[i])
            self._y_list.append(y_list[i])

        if auto_scale:
            self.scale_plot(self._x_list, self._y_list)

        self._reference_line.setData(self._x_list, self._y_list)

        # Set target motor and X axis title
        if pv_name is not None:
            self._plot_widget.setLabel(axis="bottom", text=f"{pv_name}")

            self.target_position_motor = []
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
        test_mode: Optional[bool] = False,
    ):
        # Create filename
        full_dir = os.path.join(base_dir, filename.replace(":", ".") + "_%s.csv")

        # Exponential search for files
        j = 1
        while os.path.exists(full_dir % j):
            j += 1

        # Narrow down interval
        a, b = (j // 2, j)
        while a + 1 < b:
            c = (a + b) // 2  # interval midpoint
            a, b = (c, b) if os.path.exists(full_dir % c) else (a, c)

        # Store the filename for overlay naming
        self._current_plot_name = os.path.basename(full_dir % b).replace(".csv", "")
        
        # Create file or open existing
        with open(full_dir % b, "w") as collection_file:

            collection_file.write(f"# Station: {station} | Timestamp: {datetime.datetime.now()}\n")

            if not test_mode:
                collection_file.write(f"# Energy: {round(energy, 3)} eV | Ring current: {round(current, 3)} mA\n")

            collection_file.write(
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
                        f"# Correction Scaler: ({correction_scaler[1]})\n\n"
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
                        f"{self._x_list[i]},{raw_data[i] if raw_data is not None else self._y_list[i]},{self._y_list[i]}\n"
                    )
            else:
                collection_file.write("#Positions,Counts\n")

                # Write positions and counts
                for i in range(0, len(self._x_list) - 1):
                    collection_file.write(f"{self._x_list[i]},{self._y_list[i]}\n")

            self.new_file_saved.emit(full_dir % b)

    def invert_plot(self) -> None:
        """Inverts plot preview by inverting the Y axis."""
        # Check inverted status
        if not self.inverted_mode:
            self._plot_widget.getViewBox().invertY(True)
            self.inverted_mode = True
        else:
            self._plot_widget.getViewBox().invertY(False)
            self.inverted_mode = False

    def derivative_plot(self) -> tuple[list[float], list[float]]:
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
        self._reference_line.setData(array_x, array_y)

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

        self._update_marker_coordinates()
        self.update_delta_position()

        return center

    def fit(self, center: float, sigma: float) -> float | None:
        if self._x_list and self._y_list:
            fit_model = Model(lineshapes.gaussian)
            fit_results = fit_model.fit(
                self._y_list, x=self._x_list, amplitude=100, center=center, sigma=sigma
            )
            fit_array = fit_results.best_fit.tolist()
            fitted_peak_position = self._x_list[fit_array.index(max(fit_array))]

            if self._marker_line not in self._plot_widget.items:
                self._plot_widget.addItem(self._marker_line)

            self._marker_line.setPos(fitted_peak_position)
            self._update_marker_coordinates()
            self.update_delta_position()

            return fitted_peak_position

    def find_peak(self) -> float | None:

        if self._x_list and self._y_list:
            x_peak_position = self._x_list[self._y_list.index(max(self._y_list))]

            if self._marker_line not in self._plot_widget.items:
                self._plot_widget.addItem(self._marker_line)

            self._marker_line.setPos(x_peak_position)
            self._update_marker_coordinates()
            self.update_delta_position()

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
        self.delta_position_label.setText("Delta: None")

    def reset_plot(self) -> None:
        """
        Clears the data arrays of the plot and
        restores all status variables to default.
        Resets the axis titles to generic titles.
        Note: Overlays are preserved during reset.
        """
        # Clear data arrays and updates the plot.
        # self._x_list.clear()
        # self._y_list.clear()
        self._x_list = []
        self._y_list = []
        self._reference_line.setData(self._x_list, self._y_list)

        # Clear markers
        self.clear_plot()

        # Reset status variables
        self.derivative_mode = False
        self.inverted_mode = False
        
        # Ensure overlays remain visible after reset
        self._restore_overlays()

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

        if self.marker_coords is not None:
            self.update_delta_position()

    def mouse_clicked(self, event) -> None:
        """
        Triggers on single mouse click.
        :param event: Current mouse event.
        """
        # Check for modifier keys
        modifiers = QtWidgets.QApplication.keyboardModifiers()

        line = None
        index = 0
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
                index = 1

        if line:
            # Add updated infinite line
            if line in self._plot_widget.items:
                self._plot_widget.removeItem(line)
            self._plot_widget.addItem(line)

            if index == 1:
                self._update_marker_coordinates()
                self.update_delta_position()

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
            self.update_delta_position()

            # TODO: Remove unused move makers with keys code.
            # # Upper bound marker
            # if modifiers == QtCore.Qt.AltModifier:
            #     self._upper_line.setPos(self.upper_coords + arrow_step)
            #     self.upper_coords = round(self._upper_line.pos()[0], 4)
            #
            # # Lower bound marker
            # elif modifiers == QtCore.Qt.ControlModifier:
            #     self._lower_line.setPos(self.lower_coords + arrow_step)
            #     self.lower_coords = round(self._lower_line.pos()[0], 4)
            #
            # # Main marker
            # else:
            #     self._marker_line.setPos(self.marker_coords + arrow_step)
            #     self._update_marker_coordinates()

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
            self.update_delta_position()

            # TODO: Remove unused move makers with keys code.
            # # Upper bound marker
            # if modifiers == QtCore.Qt.AltModifier:
            #     self._upper_line.setPos(self.upper_coords - arrow_step)
            #     self.upper_coords = round(self._upper_line.pos()[0], 4)
            #
            # # Lower bound marker
            # elif modifiers == QtCore.Qt.ControlModifier:
            #     self._lower_line.setPos(self.lower_coords - arrow_step)
            #     self.lower_coords = round(self._lower_line.pos()[0], 4)
            #
            # # Main marker
            # else:
            #     self._marker_line.setPos(self.marker_coords - arrow_step)
            #     self._update_marker_coordinates()

    def update_delta_position(self, start: Optional[float] = None) -> None:
        """Used to calculate and update the delta position label."""
        if len(self.target_position_motor) > 0:

            motor = self.target_position_motor[1]

            if start is not None:
                current_position = start
                print(round(current_position, 4))
                print(self.marker_coords)
            else:
                current_position = caget(motor)

            # Set unit
            unit = "mm"
            if motor == "13IDD:m84":
                unit = "deg"

            # Set direction
            direction = 1
            if self.marker_coords < current_position:
                direction = -1

            # Calculate difference
            delta = round(np.abs(current_position - self.marker_coords), 4)
            delta *= direction

            # Set text
            self.delta_position_label.setText(f"Delta: {delta} {unit}")

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
    
    def update_plot_name(self, filepath: str) -> None:
        """Updates the current plot name from a loaded file path."""
        if filepath:
            self._current_plot_name = os.path.basename(filepath).replace(".csv", "")
        else:
            self._current_plot_name = "Current Plot"

    def update_colors(self) -> None:
        # TODO: Add settings with previously saved colors.
        pass

    def _configure_buttons(self) -> None:
        back_icon = QtGui.QPixmap(os.path.join(icon_path, "back.png"))
        load_icon = QtGui.QPixmap(os.path.join(icon_path, "load.png"))
        next_icon = QtGui.QPixmap(os.path.join(icon_path, "next.png"))

        self.btn_previous_file.setIcon(QtGui.QIcon(back_icon))
        self.btn_load_file.setIcon(QtGui.QIcon(load_icon))
        self.btn_next_file.setIcon(QtGui.QIcon(next_icon))

        self.btn_previous_file.setFixedWidth(35)
        self.btn_load_file.setFixedWidth(35)
        self.btn_next_file.setFixedWidth(35)

    def recalculate_center(self):
        self._calculate_center(self._lower_line.pos(), self._upper_line.pos())

    # def change_color(self):
    #     # color = QtWidgets.QColorDialog.getColor()
    #     #
    #     # if color.isValid():
    #     #     self._graphics_layout.setBackground(color)
    #     # import random
    #     #
    #     # TODO: Example of updating the plot.
    #     self.update_plot(
    #         random.uniform(0, 100),
    #         random.uniform(0, 1000),
    #         "pinhole vertical",
    #         "13IDD:m22.VAL",
    #     )

    def rescale_plot(self):
        self.scale_plot(self._x_list, self._y_list)

    @staticmethod
    def gaussian(a, b, x):
        return a * np.exp(-((x / (2 * b)) ** 2))

    def _configure_overlay_table(self) -> None:
        """Configures the overlay management table."""
        self.overlay_table.setColumnCount(7)
        self.overlay_table.setHorizontalHeaderLabels(["Filename", "Color", "Shift", "Offset", "Scale", "Visible", "Remove"])
        self.overlay_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        
        # Set size policy to expand based on content
        self.overlay_table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.overlay_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        
        # Hide vertical header (row numbers)
        self.overlay_table.verticalHeader().setVisible(False)
        
        # Set initial minimal height (just the header)
        self.overlay_table.setMaximumHeight(self.overlay_table.horizontalHeader().height() + 5)
        
        # Set column widths
        header = self.overlay_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.overlay_table.setColumnWidth(1, 60)   # Color
        self.overlay_table.setColumnWidth(2, 100)  # Shift
        self.overlay_table.setColumnWidth(3, 100)  # Offset
        self.overlay_table.setColumnWidth(4, 100)  # Scale
        self.overlay_table.setColumnWidth(5, 60)   # Visible
        self.overlay_table.setColumnWidth(6, 70)   # Remove
        
        # Configure add overlay button
        self.btn_add_overlay.setObjectName("btn-main")
        self.btn_add_overlay.clicked.connect(self.add_overlay)
        
        # Configure save current button
        self.btn_save_current.setObjectName("btn-main")
        self.btn_save_current.clicked.connect(self.save_current_as_overlay)
        
        # Configure clear all button
        self.btn_clear_overlays.setObjectName("btn-main")
        self.btn_clear_overlays.clicked.connect(self.clear_all_overlays)
        
        # Configure shift step control
        self.spin_shift_step.setRange(0.0001, 100)
        self.spin_shift_step.setValue(0.01)
        self.spin_shift_step.setDecimals(4)
        self.spin_shift_step.setSingleStep(0.01)
        self.spin_shift_step.setFixedWidth(80)
        self.spin_shift_step.valueChanged.connect(self._update_all_shift_steps)
        
        # Configure offset step control
        self.spin_offset_step.setRange(0.0001, 100)
        self.spin_offset_step.setValue(0.01)
        self.spin_offset_step.setDecimals(4)
        self.spin_offset_step.setSingleStep(0.01)
        self.spin_offset_step.setFixedWidth(80)
        self.spin_offset_step.valueChanged.connect(self._update_all_offset_steps)
        
        # Configure scale step control
        self.spin_scale_step.setRange(0.001, 100)
        self.spin_scale_step.setValue(0.1)
        self.spin_scale_step.setDecimals(3)
        self.spin_scale_step.setSingleStep(0.1)
        self.spin_scale_step.setFixedWidth(80)
        self.spin_scale_step.valueChanged.connect(self._update_all_scale_steps)
    
    def add_overlay(self) -> None:
        """Opens file dialog to add a new overlay."""
        dialog = QtWidgets.QFileDialog()
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        
        filename = dialog.getOpenFileName(
            dialog, "Open Overlay File", "", "CSV Files (*.csv)"
        )
        
        if filename[0]:
            self._load_overlay_from_file(filename[0])
    
    def save_current_as_overlay(self) -> None:
        """Saves the current plot data as an overlay."""
        # Check if there's data to save
        if not self._x_list or not self._y_list:
            print("No current plot data to save as overlay")
            return
        
        # Generate a random color for the overlay
        import random
        color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
        
        # Create overlay model from current plot data using the tracked name
        overlay = OverlayModel(
            filename=self._current_plot_name,
            x_data=self._x_list.copy(),
            y_data=self._y_list.copy(),
            color=color,
            shift=0.0,
            offset=0.0,
            visible=True
        )
        
        # Plot the overlay
        pen = pg.mkPen(color=color, width=2)
        overlay.plot_item = self._plot_widget.plot(
            overlay.get_transformed_x_data(),
            overlay.get_transformed_y_data(),
            pen=pen,
            symbol='o',
            symbolSize=4,
            symbolBrush=color,
            name=overlay.filename
        )
        
        self.overlays.append(overlay)
        self._add_overlay_to_table(overlay)
    
    def _load_overlay_from_file(self, filepath: str) -> None:
        """Loads overlay data from a CSV file."""
        try:
            # Use numpy to load the data (same way as load_from_file does it)
            x_data = []
            y_data = []
            
            try:
                # Try loading with 3 columns (positions, raw, corrected)
                x, y_raw, y_corrected = np.loadtxt(
                    fname=filepath,
                    dtype=float,
                    comments="#",
                    delimiter=",",
                    unpack=True,
                )
                x_data = x.tolist()
                y_data = y_corrected.tolist()
            except:
                # Try loading with 2 columns (positions, counts)
                try:
                    x, y = np.loadtxt(
                        fname=filepath,
                        dtype=float,
                        comments="#",
                        delimiter=",",
                        unpack=True,
                    )
                    x_data = x.tolist()
                    y_data = y.tolist()
                except Exception as load_error:
                    print(f"Failed to parse CSV data: {load_error}")
                    return
            
            if x_data and y_data:
                # Generate a random color for the overlay
                import random
                color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
                
                # Create overlay model
                overlay = OverlayModel(
                    filename=os.path.basename(filepath),
                    x_data=x_data,
                    y_data=y_data,
                    color=color,
                    shift=0.0,
                    offset=0.0,
                    visible=True
                )
                
                print(f"Creating overlay plot with color {color}")
                print(f"X range: {min(x_data):.4f} to {max(x_data):.4f}")
                print(f"Y range: {min(y_data):.4f} to {max(y_data):.4f}")
                
                # Plot the overlay with symbols like the reference line
                pen = pg.mkPen(color=color, width=2)
                overlay.plot_item = self._plot_widget.plot(
                    overlay.get_transformed_x_data(),
                    overlay.get_transformed_y_data(),
                    pen=pen,
                    symbol='o',
                    symbolSize=4,
                    symbolBrush=color,
                    name=overlay.filename
                )
                
                print(f"Overlay plot item created: {overlay.plot_item}")
                print(f"Plot item is in widget items: {overlay.plot_item in self._plot_widget.items}")
                
                self.overlays.append(overlay)
                self._add_overlay_to_table(overlay)
                print(f"Overlay added successfully. Total overlays: {len(self.overlays)}")
            else:
                print("No data loaded from file")
                
        except Exception as e:
            print(f"Error loading overlay: {e}")
            import traceback
            traceback.print_exc()
    
    def _resize_table_to_content(self) -> None:
        """Resizes the table to fit its content."""
        # Calculate height needed: header + all rows + some padding
        header_height = self.overlay_table.horizontalHeader().height()
        row_height = self.overlay_table.rowHeight(0) if self.overlay_table.rowCount() > 0 else 30
        total_height = header_height + (row_height * self.overlay_table.rowCount()) + 2  # +2 for border
        
        # Set minimum height if no rows, otherwise set to calculated height
        if self.overlay_table.rowCount() == 0:
            min_height = header_height + 5
            self.overlay_table.setMinimumHeight(min_height)
            self.overlay_table.setMaximumHeight(min_height)
        else:
            # Cap at a reasonable maximum (e.g., 200px) to prevent taking too much space
            capped_height = min(total_height, 200)
            self.overlay_table.setMinimumHeight(capped_height)
            self.overlay_table.setMaximumHeight(capped_height)
    
    def _update_all_shift_steps(self, step_value: float) -> None:
        """Updates the step size for all shift spinboxes in the table."""
        for row in range(self.overlay_table.rowCount()):
            shift_spin = self.overlay_table.cellWidget(row, 2)
            if shift_spin:
                shift_spin.setSingleStep(step_value)
    
    def _update_all_offset_steps(self, step_value: float) -> None:
        """Updates the step size for all offset spinboxes in the table."""
        for row in range(self.overlay_table.rowCount()):
            offset_spin = self.overlay_table.cellWidget(row, 3)
            if offset_spin:
                offset_spin.setSingleStep(step_value)
    
    def _update_all_scale_steps(self, step_value: float) -> None:
        """Updates the step size for all scale spinboxes in the table."""
        for row in range(self.overlay_table.rowCount()):
            scale_spin = self.overlay_table.cellWidget(row, 4)
            if scale_spin:
                scale_spin.setSingleStep(step_value)
    
    def _add_overlay_to_table(self, overlay: OverlayModel) -> None:
        """Adds an overlay to the table widget."""
        row = self.overlay_table.rowCount()
        self.overlay_table.insertRow(row)
        
        # Filename
        filename_item = QtWidgets.QTableWidgetItem(overlay.filename)
        filename_item.setFlags(filename_item.flags() & ~QtCore.Qt.ItemIsEditable)
        self.overlay_table.setItem(row, 0, filename_item)
        
        # Color button (base styling in style.qss, only set dynamic color here)
        color_btn = QtWidgets.QPushButton()
        color_btn.setStyleSheet(f"background-color: rgb{overlay.color};")
        color_btn.clicked.connect(lambda checked, r=row: self._change_overlay_color(r))
        self.overlay_table.setCellWidget(row, 1, color_btn)
        
        # Shift spinbox
        shift_spin = QtWidgets.QDoubleSpinBox()
        shift_spin.setRange(-1000000, 1000000)
        shift_spin.setValue(overlay.shift)
        shift_spin.setSingleStep(self.spin_shift_step.value())
        shift_spin.setDecimals(3)
        shift_spin.valueChanged.connect(lambda value, r=row: self._change_overlay_shift(r, value))
        self.overlay_table.setCellWidget(row, 2, shift_spin)
        
        # Offset spinbox
        offset_spin = QtWidgets.QDoubleSpinBox()
        offset_spin.setRange(-1000000, 1000000)
        offset_spin.setValue(overlay.offset)
        offset_spin.setSingleStep(self.spin_offset_step.value())
        offset_spin.setDecimals(3)
        offset_spin.valueChanged.connect(lambda value, r=row: self._change_overlay_offset(r, value))
        self.overlay_table.setCellWidget(row, 3, offset_spin)
        
        # Scale spinbox
        scale_spin = QtWidgets.QDoubleSpinBox()
        scale_spin.setRange(0.001, 1000)
        scale_spin.setValue(overlay.scale)
        scale_spin.setSingleStep(self.spin_scale_step.value())
        scale_spin.setDecimals(3)
        scale_spin.valueChanged.connect(lambda value, r=row: self._change_overlay_scale(r, value))
        self.overlay_table.setCellWidget(row, 4, scale_spin)
        
        # Visible checkbox
        visible_check = QtWidgets.QCheckBox()
        visible_check.setChecked(overlay.visible)
        visible_check.stateChanged.connect(lambda state, r=row: self._toggle_overlay_visibility(r, state))
        checkbox_widget = QtWidgets.QWidget()
        checkbox_layout = QtWidgets.QHBoxLayout(checkbox_widget)
        checkbox_layout.addWidget(visible_check)
        checkbox_layout.setAlignment(QtCore.Qt.AlignCenter)
        checkbox_layout.setContentsMargins(0, 0, 0, 0)
        self.overlay_table.setCellWidget(row, 5, checkbox_widget)
        
        # Remove button
        remove_btn = QtWidgets.QPushButton("Remove")
        remove_btn.clicked.connect(lambda checked, r=row: self._remove_overlay(r))
        self.overlay_table.setCellWidget(row, 6, remove_btn)
        
        # Resize table to fit content
        self._resize_table_to_content()
    
    def _change_overlay_color(self, row: int) -> None:
        """Opens color dialog to change overlay color."""
        if row < len(self.overlays):
            overlay = self.overlays[row]
            current_color = QtGui.QColor(*overlay.color)
            color = QtWidgets.QColorDialog.getColor(current_color, self, "Select Overlay Color")
            
            if color.isValid():
                overlay.color = (color.red(), color.green(), color.blue())
                
                # Update button color (base styling in style.qss)
                color_btn = self.overlay_table.cellWidget(row, 1)
                color_btn.setStyleSheet(f"background-color: rgb{overlay.color};")
                
                # Update plot color
                if overlay.plot_item:
                    pen = pg.mkPen(color=overlay.color, width=2)
                    overlay.plot_item.setPen(pen)
    
    def _change_overlay_shift(self, row: int, value: float) -> None:
        """Change the shift (x-axis offset) of an overlay."""
        if 0 <= row < len(self.overlays):
            overlay = self.overlays[row]
            overlay.shift = value
            
            # Update plot data (even if hidden, so it's correct when shown)
            if overlay.plot_item:
                overlay.plot_item.setData(overlay.get_transformed_x_data(), overlay.get_transformed_y_data())
    
    def _change_overlay_offset(self, row: int, value: float) -> None:
        """Change the offset of an overlay."""
        if 0 <= row < len(self.overlays):
            overlay = self.overlays[row]
            overlay.offset = value
            
            # Update plot data (even if hidden, so it's correct when shown)
            if overlay.plot_item:
                overlay.plot_item.setData(overlay.get_transformed_x_data(), overlay.get_transformed_y_data())
    
    def _change_overlay_scale(self, row: int, value: float) -> None:
        """Change the scale of an overlay."""
        if 0 <= row < len(self.overlays):
            overlay = self.overlays[row]
            overlay.scale = value
            
            # Update plot data (even if hidden, so it's correct when shown)
            if overlay.plot_item:
                overlay.plot_item.setData(overlay.get_transformed_x_data(), overlay.get_transformed_y_data())
    
    def _toggle_overlay_visibility(self, row: int, state: int) -> None:
        """Toggles visibility of an overlay."""
        if row < len(self.overlays):
            overlay = self.overlays[row]
            overlay.visible = (state == QtCore.Qt.Checked)
            
            if overlay.plot_item:
                overlay.plot_item.setVisible(overlay.visible)
    
    def _remove_overlay(self, row: int) -> None:
        """Removes an overlay from the plot and table."""
        if row < len(self.overlays):
            overlay = self.overlays[row]
            
            # Remove from plot
            if overlay.plot_item and overlay.plot_item in self._plot_widget.items:
                self._plot_widget.removeItem(overlay.plot_item)
            
            # Remove from list
            self.overlays.pop(row)
            
            # Rebuild table
            self._rebuild_overlay_table()
            
            # Resize table
            self._resize_table_to_content()
    
    def clear_all_overlays(self) -> None:
        """Removes all overlays and the main plot from the graph."""
        # Remove all overlay plot items
        for overlay in self.overlays:
            if overlay.plot_item and overlay.plot_item in self._plot_widget.items:
                self._plot_widget.removeItem(overlay.plot_item)
        
        # Clear the overlays list
        self.overlays.clear()
        
        # Clear the table
        self.overlay_table.setRowCount(0)
    
        # Resize table to retract
        self._resize_table_to_content()
        
        # Clear the main plot as well
        self.reset_plot()
    
    def _rebuild_overlay_table(self) -> None:
        """Rebuilds the overlay table from scratch."""
        self.overlay_table.setRowCount(0)
        for overlay in self.overlays:
            self._add_overlay_to_table(overlay)
    
    def _restore_overlays(self) -> None:
        """Ensures all overlays are visible on the plot after reset."""
        for overlay in self.overlays:
            if overlay.plot_item:
                # Check if plot item is in the widget
                if overlay.plot_item not in self._plot_widget.items:
                    # Re-add the plot item
                    pen = pg.mkPen(color=overlay.color, width=2)
                    overlay.plot_item = self._plot_widget.plot(
                        overlay.get_transformed_x_data(),
                        overlay.get_transformed_y_data(),
                        pen=pen,
                        symbol='o',
                        symbolSize=4,
                        symbolBrush=overlay.color,
                        name=overlay.filename
                    )
                # Ensure visibility matches the model state
                overlay.plot_item.setVisible(overlay.visible)
    
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
        status_layout.addWidget(VLine(), alignment=QtCore.Qt.Alignment())
        status_layout.addWidget(self.moved_by_label, alignment=QtCore.Qt.Alignment())
        status_layout.addStretch(1)
        status_layout.addWidget(VLine(), alignment=QtCore.Qt.Alignment())
        status_layout.addWidget(self.delta_position_label, alignment=QtCore.Qt.Alignment())
        status_layout.addStretch(1)

        tools_layout = QtWidgets.QHBoxLayout()
        tools_layout.setContentsMargins(0, 0, 0, 0)
        tools_layout.setSpacing(2)
        tools_layout.addWidget(self.btn_move, alignment=QtCore.Qt.Alignment())
        tools_layout.addWidget(self.btn_peak, alignment=QtCore.Qt.Alignment())
        tools_layout.addWidget(self.btn_center, alignment=QtCore.Qt.Alignment())
        tools_layout.addWidget(self.btn_clear, alignment=QtCore.Qt.Alignment())
        tools_layout.addWidget(self.btn_invert, alignment=QtCore.Qt.Alignment())
        tools_layout.addWidget(self.btn_derivative, alignment=QtCore.Qt.Alignment())
        tools_layout.addWidget(self.btn_previous_file, alignment=QtCore.Qt.Alignment())
        tools_layout.addWidget(self.btn_load_file, alignment=QtCore.Qt.Alignment())
        tools_layout.addWidget(self.btn_next_file, alignment=QtCore.Qt.Alignment())

        toolbar_layout = QtWidgets.QVBoxLayout()
        toolbar_layout.addLayout(status_layout)
        toolbar_layout.addLayout(tools_layout)
        
        # Overlay section layout
        overlay_section_layout = QtWidgets.QVBoxLayout()
        overlay_section_layout.setContentsMargins(0, 10, 0, 0)
        
        overlay_header_layout = QtWidgets.QHBoxLayout()
        overlay_header_layout.setSpacing(5)
        overlay_label = QtWidgets.QLabel("Overlays")
        overlay_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        overlay_header_layout.addWidget(overlay_label)
        overlay_header_layout.addStretch(1)
        overlay_header_layout.addWidget(self.lbl_shift_step)
        overlay_header_layout.addWidget(self.spin_shift_step)
        overlay_header_layout.addWidget(self.lbl_offset_step)
        overlay_header_layout.addWidget(self.spin_offset_step)
        overlay_header_layout.addWidget(self.lbl_scale_step)
        overlay_header_layout.addWidget(self.spin_scale_step)
        overlay_header_layout.addWidget(self.btn_clear_overlays)
        overlay_header_layout.addWidget(self.btn_save_current)
        overlay_header_layout.addWidget(self.btn_add_overlay)
        
        overlay_section_layout.addLayout(overlay_header_layout)
        overlay_section_layout.addWidget(self.overlay_table)

        # Main plot layout.
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._graphics_layout, alignment=QtCore.Qt.Alignment())
        layout.addLayout(toolbar_layout)
        layout.addLayout(overlay_section_layout)
        self.setLayout(layout)
