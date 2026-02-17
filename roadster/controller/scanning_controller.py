import time
import os
import threading
import numpy as np

from epics import caget, caput
from newportxps import NewportXPS

from typing import List, Optional
from qtpy import QtWidgets
from qtpy.QtCore import QObject, Signal

from roadster.model import MainModel, ScanProc
from roadster.model import MapModel, PromptModel
from roadster.view import MainView

from roadster.view.authentication_view import AuthenticationView


class ScanningController(QObject):
    """Connects the scanning view and the scanning models while providing additional functionality."""

    loaded_file_changed: Signal = Signal(str)
    scan_running: Signal = Signal(bool)

    _delta_position_changed: Signal = Signal(float)

    def __init__(self, model: MainModel, view: MainView):
        super(ScanningController, self).__init__()
        self.model = model
        self.view = view
        self.scanning_view = self.view.scanning
        self.scanning_model = self.model.scanning
        self.station = self.model.options.station
        self.raw_data = []

        self.msg_prompt = None
        self.authentication_dialog = None
        self._test_mode = False
        self._fly_scan_starting = False

        # Create the xps connection instance
        self.stage_xps = NewportXPS(
            host=self.station.xps.host.value,
            username=self.station.xps.username.value,
            password=self.station.xps.password.value,
        )
        
        # Set combo box information
        self._populate_combo_boxes()

        # Helpers
        self._loaded_file = ""

        # Connect widgets
        self._connect_plot_widgets()
        self._connect_scanning_control_widgets()

        # Error codes
        self._limit_error = False
        self._station_error = False

        # Status
        self._trj_running = False
        self._aborted = False
        
        # Store scan state for abort recovery
        self._scan_center = None
        self._scan_target_stage = None

    def _populate_combo_boxes(self) -> None:
        """Adds the combo box items."""
        # Scanning modes.
        for item in self.scanning_model.scan_modes:
            self.scanning_view.cmb_scan_mode.addItem(item.value)
        
        # Set default scan mode to "Fly" (index 1: step=0, fly=1)
        self.scanning_view.cmb_scan_mode.setCurrentIndex(1)

        # Scanning types.
        for item in self.scanning_model.scan_types:
            self.scanning_view.cmb_scan_type.addItem(item.value)

        # Scalers.
        default_found = False
        scaler_index = 0

        for item in self.model.options.station.scalers:
            self.scanning_view.cmb_scaler.addItem(item.value[0])
            self.scanning_view.cmb_correction_scaler.addItem(item.value[0])

        # Set default scaler
        self.scanning_view.cmb_scaler.setCurrentIndex(3)
        self.scanning_view.cmb_correction_scaler.setCurrentIndex(0)

    def _connect_plot_widgets(self):
        """Connects the signals of the plot widgets."""
        self.scanning_view.plot.btn_invert.clicked.connect(
            self.scanning_view.plot.invert_plot
        )
        self.scanning_view.plot.btn_derivative.clicked.connect(
            self.scanning_view.plot.derivative_plot
        )

        self.scanning_view.plot.btn_peak.clicked.connect(
            self.scanning_view.plot.find_peak
        )

        self.scanning_view.plot.btn_center.clicked.connect(
            self.scanning_view.plot.center_plot
        )

        self.scanning_view.plot.btn_clear.clicked.connect(
            self.scanning_view.plot.clear_plot
        )

        # Move button
        self.scanning_view.plot.btn_move.clicked.connect(self.move_by_marker)

        self.scanning_view.plot.btn_load_file.clicked.connect(self.load_from_file)
        self.scanning_view.plot.btn_previous_file.clicked.connect(self.load_previous_file)
        self.scanning_view.plot.btn_next_file.clicked.connect(self.load_next_file)
        self.scan_running.connect(self.scanning_view.plot.toggle_plot_buttons)
        
        # Connect loaded file signal to update plot name for overlays
        self.loaded_file_changed.connect(self.scanning_view.plot.update_plot_name)

    def _connect_scanning_control_widgets(self):
        """Connects the signals of the scanning control widgets."""

        # Buttons
        scanning_buttons = [
            self.scanning_view.btn_pinhole_vertical,
            self.scanning_view.btn_pinhole_horizontal,
            self.scanning_view.btn_sample_vertical,
            self.scanning_view.btn_sample_horizontal,
            self.scanning_view.btn_sample_focus,
            self.scanning_view.btn_sample_omega,
            self.scanning_view.btn_custom_scan,
        ]

        self.scanning_view.btn_sample_vertical.clicked.connect(
            lambda: self.set_target_stage(self.station.stages.sample_vertical.value)
        )

        self.scanning_view.btn_sample_horizontal.clicked.connect(
            lambda: self.set_target_stage(self.station.stages.sample_horizontal.value)
        )

        self.scanning_view.btn_sample_focus.clicked.connect(
            lambda: self.set_target_stage(self.station.stages.sample_focus.value)
        )

        self.scanning_view.btn_sample_omega.clicked.connect(
            lambda: self.set_target_stage(self.station.stages.sample_omega.value)
        )

        self.scanning_view.btn_pinhole_horizontal.clicked.connect(
            lambda: self.set_target_stage(self.station.stages.pinhole_horizontal.value)
        )

        self.scanning_view.btn_pinhole_vertical.clicked.connect(
            lambda: self.set_target_stage(self.station.stages.pinhole_vertical.value)
        )

        self.scanning_view.btn_pinhole_auto.clicked.connect(
            lambda: self.set_target_stage(self.station.stages.pinhole_horizontal.value)
        )

        self.scanning_view.btn_auto_centering.clicked.connect(
            lambda: self.set_target_stage(self.station.stages.sample_horizontal.value)
        )

        self.scanning_view.btn_custom_scan.clicked.connect(
            lambda: self.set_target_stage(
                [" ", self.scanning_view.lne_custom_scan.text()]
            )
        )

        for button in scanning_buttons:
            button.clicked.connect(
                lambda: self.scanning_procedure(
                    trj_range=float(self.scanning_view.lne_range.text()),
                    step=float(self.scanning_view.lne_step.text()),
                    exposure=float(self.scanning_view.lne_exposure.text()),
                    scanning_type=ScanProc.Single,
                )
            )

        self.scanning_view.btn_pinhole_auto.clicked.connect(
            lambda: self.scanning_procedure(
                trj_range=0.04, step=0.002, exposure=0.1, scanning_type=ScanProc.Pinhole
            )
        )

        # Abort button
        self.scanning_view.btn_abort_scan.clicked.connect(self._abort_scan)

        # Center of rotation
        self.scanning_view.btn_auto_centering.clicked.connect(
            lambda: self.scanning_procedure(
                trj_range=float(self.scanning_view.lne_range.text()),
                step=float(self.scanning_view.lne_step.text()),
                exposure=float(self.scanning_view.lne_exposure.text()),
                scanning_type=ScanProc.Centering,
            )
        )

        self.scanning_view.btn_save_negative_position.clicked.connect(
            lambda: self.btn_save_clicked("negative")
        )
        self.scanning_view.btn_save_positive_position.clicked.connect(
            lambda: self.btn_save_clicked("positive")
        )
        self.scanning_view.btn_save_central_position.clicked.connect(
            lambda: self.btn_save_clicked("central")
        )

        self.scanning_view.btn_reset_saved.clicked.connect(
            self.scanning_view.reset_save_labels
        )

        self.scanning_view.btn_apply_correction.clicked.connect(
            self.btn_apply_correction_clicked
        )

        # Expert mode toggle
        self.scanning_view.btn_expert_toggle.clicked.connect(self.authentication)

        # Checkbox test mode
        self.scanning_view.check_test_mode.stateChanged.connect(
            self._scanning_mode_changed
        )

        # Delta positioning
        self._delta_position_changed.connect(self.change_delta_position)

    def change_delta_position(self, start: float) -> None:
        self.scanning_view.plot.update_delta_position(start=start)

    def authentication(self) -> None:
        """
        Check if the given password matches the set station password.
        """
        if self.station.expert_mode:
            self.station.expert_mode = False
            self.scanning_view.lbl_expert_user_mode.setText("User mode")
            self.scanning_view.lbl_expert_user_mode.setStyleSheet("color: forestgreen;")
            return None

        self.authentication_dialog = AuthenticationView()
        self.authentication_dialog.btn_authenticate.clicked.connect(
            lambda: self.authenticate_user(view=self.authentication_dialog)
        )
        self.authentication_dialog.display()

    def authenticate_user(self, view: AuthenticationView):
        if view.pwd_dialog.text() == self.station.expert_pwd:
            view.close()
            self.station.expert_mode = True
            self.scanning_view.lbl_expert_user_mode.setText("Expert mode")
            self.scanning_view.lbl_expert_user_mode.setStyleSheet("color: lightcoral;")
        else:
            view.lbl_wrong_pwd.setText("Wrong Password")
            self.station.expert_mode = False

    def _scanning_mode_changed(self):
        state = self.scanning_view.check_test_mode.checkState()

        if state == 0:
            self._test_mode = False
        else:
            self._test_mode = True

    def set_target_stage(self, stage: List):
        """Sets the target stage of the scan."""
        if stage[1].strip() != "":
            self.scanning_view.plot.update_target_stage(stage)

    def move_by_marker(self):
        """
        Checks if the target position is within the limits of the stage and the moves the stage.
        """
        if not self.station.trj_running:
            if len(self.scanning_view.plot.target_position_motor) >= 1:

                target_position = self.scanning_view.plot.marker_coords
                target_motor = self.scanning_view.plot.target_position_motor[1]
                motor_name = self.scanning_view.plot.target_position_motor[0]

                if target_position is None:
                    self.msg_prompt = PromptModel(
                        parent=self.scanning_view,
                        msg_title="Missing target value",
                        msg_text="Target position not selected.",
                    )
                    return None

                # Check stage limits.
                if not target_position > caget(
                    target_motor + ".HLM"
                ) and not target_position < caget(target_motor + ".LLM"):

                    current_position = caget(
                        self.scanning_view.plot.target_position_motor[1]
                    )

                    move_distance = round(current_position - target_position, 4) * -1
                    formatted_distance = self.scanning_view.plot._format_length_with_unit(move_distance)
                    self.msg_prompt = PromptModel(
                        parent=self.scanning_view,
                        msg_title="Move confirmation",
                        msg_text=f"The {motor_name} ({target_motor}) stage is going to move by "
                        f"{formatted_distance}. Do you want to continue?",
                        user_prompt=True,
                    )

                    if self.msg_prompt.response:
                        # Move within limits
                        caput(target_motor + ".VAL", target_position, wait=True)
                        moved_value = round(current_position - target_position, 4) * -1
                        formatted_moved = self.scanning_view.plot._format_length_with_unit(moved_value)
                        self.scanning_view.plot.moved_by_label.setText(
                            f"Moved: {formatted_moved}"
                        )
                        self.scanning_view.plot.update_delta_position()
                else:
                    self.msg_prompt = PromptModel(
                        parent=self.scanning_view,
                        msg_title="Stage limits",
                        msg_text=f"The {target_position} surpasses the stage limits.",
                    )

    def fly_scan(
        self,
        xps_stage: str,
        xps_group: str,
        scan_range: float,
        scantime: float,
        step: float,
        scan: MapModel,
        target_stage: str,
        center: float,
        centering: bool,
        revert_position: bool,
        scan_mode: str,
        energy: float,
        current: float,
    ):
        # Check stage velocity
        max_velocity = caget(target_stage + ".VMAX")
        velocity = round(scan_range / scantime, 4)

        if velocity > max_velocity:
            self._abort_scan()
            print(f"The velocity of {round(velocity, 4)} is invalid.")
        else:
            # Get direction
            direction = -1 if caget(target_stage + ".DIR") == 1 else 1
            xps_direction = "backward" if direction == -1 else "foreward"

            # Define xps trajectory
            self.stage_xps.define_line_trajectories(
                axis=xps_stage,
                group=xps_group,
                stop=scan_range,
                step=step,
                pixeltime=None,
                scantime=scantime,
            )

            # Set count type to oneshot
            caput(self.station.miscellaneous.pd_count_type.value[1], 0)
            time.sleep(0.5)

            # Set channel advance source to external
            caput(self.station.miscellaneous.mcs_ch_advance.value[1], 1)

            # Set number of channels
            caput(
                self.model.options.station.miscellaneous.mcs_control_channels.value[1],
                scan.points - 1,
            )

            self.station.prepare_shutter()

            # Trigger readback
            self._fly_scan_starting = True

            # Start trajectory
            caput(self.model.options.station.miscellaneous.mcs_erase_start.value[1], 1)
            self.stage_xps.run_trajectory(name=xps_direction, save=False, clean=True)

            data_array = caget(self.station.miscellaneous.mcs_channel.value[1])

            self.scanning_view.plot.update_plot_array(
                x_list=scan.lines[0].trj_positions, y_list=data_array, auto_scale=True
            )

            caput(self.station.miscellaneous.mcs_stop.value[1], 1)

        self.scan_finished(
            target_stage=target_stage,
            center=center,
            centering=centering,
            revert_position=revert_position,
            scan=scan,
            scan_mode=scan_mode,
            energy=energy,
            current=current,
        )

    def read_fly_data(self, scan: MapModel):
        time.sleep(3)

        # Add delay to start after the trajectory has began.
        while self.station.trj_running and not self.station.trj_aborted and not self.station.aborted:

            if self._fly_scan_starting:
                # Break sleep into smaller chunks to check abort status
                sleep_time = scan.exposure_time / 2
                elapsed = 0
                while elapsed < sleep_time and not self.station.trj_aborted and not self.station.aborted:
                    time.sleep(0.1)
                    elapsed += 0.1

                if self.station.trj_aborted or self.station.aborted:
                    break

                # Get fly data
                data_array = caget(self.station.miscellaneous.mcs_channel.value[1])

                self.scanning_view.plot.update_plot_array(
                    x_list=scan.lines[0].trj_positions,
                    y_list=data_array,
                    auto_scale=True,
                )
                
                # Break sleep into smaller chunks to check abort status
                elapsed = 0
                while elapsed < sleep_time and not self.station.trj_aborted and not self.station.aborted:
                    time.sleep(0.1)
                    elapsed += 0.1

        self._fly_scan_starting = False

        # Note: fly_scan will call scan_finished at the end, which will restore station and reset status
        # So we don't need to call _abort_scan() here

    def _abort_scan(self):
        print("Aborted Now")

        # Check if a scan is actually running
        scan_was_running = self.station.trj_running or (self._scan_target_stage is not None and self._scan_center is not None)

        # Always set both abort flags when abort button is clicked
        self.station.aborted = True
        self.station.trj_aborted = True

        # Set status to aborting
        self.update_status(
            abort_status=True, running_status=False, label_text="Aborting..."
        )

        # Station stop
        self.station.stop_all()
        
        # Restore station if scan was started (shutter opened, motor moved)
        # This handles the case where abort is clicked before scan thread starts
        if self._scan_target_stage is not None and self._scan_center is not None:
            self.station.restore_station(
                target_stage=self._scan_target_stage,
                center=self._scan_center,
                centering=False,
                revert_position=True,
            )
            # Clear stored values
            self._scan_target_stage = None
            self._scan_center = None
        
        # If no scan was running, reset status back to Idle immediately
        if not scan_was_running:
            self.update_status(
                abort_status=False, running_status=False, label_text="Idle"
            )

    def _update_status_label(self, text: str, color: str):
        self.scanning_view.lbl_scanning_status.setText(text)
        self.scanning_view.lbl_scanning_status.setStyleSheet(f"color: {color};")

    def btn_save_clicked(self, save_type: str):

        target_value = round(caget(self.station.stages.sample_omega.value[1]), 4)

        if save_type == "negative":
            if target_value >= 0:
                self.msg_prompt = PromptModel(
                    parent=self.scanning_view,
                    msg_title="Save error",
                    msg_text=f"The target value must be < 0",
                )
                return None
            label = self.scanning_view.lbl_saved_negative_position
        elif save_type == "positive":
            if target_value <= 0:
                self.msg_prompt = PromptModel(
                    parent=self.scanning_view,
                    msg_title="Save error",
                    msg_text=f"The target value must be > 0",
                )
                return None
            label = self.scanning_view.lbl_saved_positive_position
        else:
            if target_value != 0:
                self.msg_prompt = PromptModel(
                    parent=self.scanning_view,
                    msg_title="Save error",
                    msg_text=f"The target value must equals 0",
                )
                return None
            label = self.scanning_view.lbl_saved_central_position

        position = round(caget(self.station.stages.sample_horizontal.value[1]), 4)
        omega_position = round(caget(self.station.stages.sample_omega.value[1]), 4)
        self.scanning_view.update_save_labels(
            position=position, omega_position=omega_position, label=label
        )

    def btn_apply_correction_clicked(self):

        _, rotation_stage = self.station.auto_centering_stages()

        if (
            self.scanning_view._focal_correction_mm is None
            or self.scanning_view.lbl_centering_correction.text() == "None"
        ):
            self.msg_prompt = PromptModel(
                parent=self.scanning_view,
                msg_title="Missing focal correction value",
                msg_text="No focal correction value available.",
            )
            return None
        elif self.scanning_view.lbl_centering_correction.text() == "Applied":
            self.msg_prompt = PromptModel(
                parent=self.scanning_view,
                msg_title="Correction applied",
                msg_text="The focal correction has already been applied.",
            )
            return None

        # Get the raw focal correction value in mm (not from display label)
        focal_correction = self.scanning_view._focal_correction_mm

        value = caget(self.station.stages.sample_focus.value[1]) - focal_correction
        high_limit = caget(self.station.stages.sample_focus.value[1] + ".HLM")
        low_limit = caget(self.station.stages.sample_focus.value[1] + ".LLM")

        if value < low_limit or value > high_limit:
            self.msg_prompt = PromptModel(
                parent=self.scanning_view,
                msg_title="Stage limits",
                msg_text=f"The {value} surpasses the stage limits.",
            )
            return None

        formatted_correction = self.scanning_view.plot._format_length_with_unit(focal_correction)
        self.msg_prompt = PromptModel(
            parent=self.scanning_view,
            msg_title="Move confirmation",
            msg_text=f"The Focus stage will be corrected by {formatted_correction} and {rotation_stage[0]} "
            f"({rotation_stage[1]}) will return to the central position. Do you want to continue?",
            user_prompt=True,
        )

        if self.msg_prompt.response:
            if round(caget(rotation_stage[1]), 4) != 0:
                caput(rotation_stage[1], 0)

            caput(self.station.stages.sample_focus.value[1], value, wait=True)
            formatted_moved = self.scanning_view.plot._format_length_with_unit(focal_correction)
            self.scanning_view.plot.moved_by_label.setText(
                f"Moved: {formatted_moved}"
            )
            self.scanning_view.lbl_centering_correction.setText("Applied")

    @staticmethod
    def _get_file(directory: str, oldest: Optional[bool] = False) -> Optional[str]:
        if not os.path.exists(directory) or not os.path.isdir(directory):
            return None
        
        try:
            files = os.listdir(directory)
            if not files:
                return None
                
            full_paths = []
            [full_paths.append(os.path.join(directory, file)) for file in files if os.path.isfile(os.path.join(directory, file))]

            if not full_paths:
                return None

            if oldest:
                target_file = min(full_paths, key=os.path.getctime)
            else:
                target_file = max(full_paths, key=os.path.getctime)

            return str(target_file)
        except (OSError, PermissionError) as e:
            return None

    def _get_relative_file(self, directory: str, next_file: Optional[bool] = False) -> Optional[str]:
        if not os.path.exists(directory) or not os.path.isdir(directory):
            return None
            
        relative_file: Optional[str] = None
        
        # Account for nothing loaded
        if not self._loaded_file or not os.path.exists(self._loaded_file):
            target_file = self._get_file(directory=directory)
            if target_file:
                self._loaded_file = target_file
            else:
                return None
        
        if not os.path.exists(self._loaded_file):
            return None
            
        loaded_file_creation_time = os.path.getctime(self._loaded_file)

        try:
            files = []
            
            if next_file:
                latest_file = self._get_file(directory=directory)
                if latest_file and latest_file == self._loaded_file:
                    relative_file = self._loaded_file
                else:
                    for file in os.listdir(directory):
                        filepath = os.path.join(directory, file)
                        if not os.path.isfile(filepath):
                            continue
                        file_creation_time = os.path.getctime(filepath)

                        if relative_file is None:
                            relative_file = filepath

                        if loaded_file_creation_time < file_creation_time:
                            files.append(filepath)

                    if files:
                        relative_file = min(files, key=os.path.getctime)
                    else:
                        relative_file = self._loaded_file
            else:
                oldest_file = self._get_file(directory=directory, oldest=True)
                if oldest_file and oldest_file == self._loaded_file:
                    relative_file = self._loaded_file
                else:
                    for file in os.listdir(directory):
                        filepath = os.path.join(directory, file)
                        if not os.path.isfile(filepath):
                            continue
                        file_creation_time = os.path.getctime(filepath)

                        if relative_file is None:
                            relative_file = filepath

                        if loaded_file_creation_time > file_creation_time:
                            files.append(filepath)

                    if files:
                        relative_file = max(files, key=os.path.getctime)
                    else:
                        relative_file = self._loaded_file

            return relative_file
        except (OSError, PermissionError):
            return None

    def load_next_file(self):
        target_directory = None
        
        # Priority 1: If a file is manually loaded, always use its directory as the base
        if self._loaded_file and os.path.exists(self._loaded_file):
            target_directory = os.path.dirname(self._loaded_file)
        else:
            # Priority 2: Fall back to EPICS path only if no file is manually loaded
            # Try to get directory from EPICS
            try:
                epics_path = caget("13IDDLF1:cam1:FilePath.VAL", as_string=True)
                if epics_path:
                    try:
                        target_directory = epics_path.split("\\")[4].strip()
                        target_directory = (
                            self.station.base_dir + f"/{target_directory}" + "/Absorption_Scans/"
                        )
                    except (IndexError, AttributeError):
                        # EPICS path format is unexpected, try to use it directly or construct differently
                        target_directory = None
            except Exception:
                # EPICS connection failed, target_directory remains None
                pass
        
        # Check if directory exists
        if not target_directory:
            QtWidgets.QMessageBox.information(
                None, "No Folder Selected", "Unable to determine folder path from EPICS. Please load a file manually first."
            )
            return
            
        if not os.path.exists(target_directory) or not os.path.isdir(target_directory):
            QtWidgets.QMessageBox.information(
                None, "Folder Not Found", f"Folder does not exist: {target_directory}\nPlease load a file manually first."
            )
            return

        filename = self._get_relative_file(directory=target_directory, next_file=True)
        if not filename:
            QtWidgets.QMessageBox.information(
                None, "No More Files", "No more files found in this directory."
            )
            return
            
        self._loaded_file = filename
        self.loaded_file_changed.emit(self._loaded_file)

        with open(filename, "r") as file:

            for line in file.readlines():
                if line.startswith("# Scanned motor: "):
                    motor = line.split(" ")[3]

        y = []
        y_corrected = []

        try:
            x, y, y_corrected = np.loadtxt(
                fname=filename,
                dtype=float,
                comments="#",
                delimiter=",",
                unpack=True,
            )
        except Exception as e:
            x, y = np.loadtxt(
                fname=filename,
                dtype=float,
                comments="#",
                delimiter=",",
                unpack=True,
            )

        self.scanning_view.plot.reset_plot()

        if len(y_corrected) > 1:
            y_list = y_corrected
        else:
            y_list = y

        self.scanning_view.plot.update_plot_array(
            x_list=x, y_list=y_list, pv_name=motor
        )
        self.scanning_view.plot.rescale_plot()

    def load_previous_file(self):
        target_directory = None
        
        # Priority 1: If a file is manually loaded, always use its directory as the base
        if self._loaded_file and os.path.exists(self._loaded_file):
            target_directory = os.path.dirname(self._loaded_file)
        else:
            # Priority 2: Fall back to EPICS path only if no file is manually loaded
            # Try to get directory from EPICS
            try:
                epics_path = caget("13IDDLF1:cam1:FilePath.VAL", as_string=True)
                if epics_path:
                    try:
                        target_directory = epics_path.split("\\")[4].strip()
                        target_directory = (
                            self.station.base_dir + f"/{target_directory}" + "/Absorption_Scans/"
                        )
                    except (IndexError, AttributeError):
                        # EPICS path format is unexpected, try to use it directly or construct differently
                        target_directory = None
            except Exception:
                # EPICS connection failed, target_directory remains None
                pass
        
        # Check if directory exists
        if not target_directory:
            QtWidgets.QMessageBox.information(
                None, "No Folder Selected", "Unable to determine folder path from EPICS. Please load a file manually first."
            )
            return
            
        if not os.path.exists(target_directory) or not os.path.isdir(target_directory):
            QtWidgets.QMessageBox.information(
                None, "Folder Not Found", f"Folder does not exist: {target_directory}\nPlease load a file manually first."
            )
            return

        filename = self._get_relative_file(directory=target_directory)
        if not filename:
            QtWidgets.QMessageBox.information(
                None, "No More Files", "No more files found in this directory."
            )
            return
            
        self._loaded_file = filename
        self.loaded_file_changed.emit(self._loaded_file)

        with open(filename, "r") as file:

            for line in file.readlines():
                if line.startswith("# Scanned motor: "):
                    motor = line.split(" ")[3]

        y = []
        y_corrected = []

        try:
            x, y, y_corrected = np.loadtxt(
                fname=filename,
                dtype=float,
                comments="#",
                delimiter=",",
                unpack=True,
            )
        except Exception as e:
            x, y = np.loadtxt(
                fname=filename,
                dtype=float,
                comments="#",
                delimiter=",",
                unpack=True,
            )

        self.scanning_view.plot.reset_plot()

        if len(y_corrected) > 1:
            y_list = y_corrected
        else:
            y_list = y

        self.scanning_view.plot.update_plot_array(
            x_list=x, y_list=y_list, pv_name=motor
        )
        self.scanning_view.plot.rescale_plot()

    def load_from_file(self):
        if not self._trj_running:
            # Set / Create directory
            target_directory = None
            try:
                epics_path = caget("13IDDLF1:cam1:FilePath.VAL", as_string=True)
                if epics_path:
                    try:
                        target_directory = epics_path.split("\\")[4].strip()
                        target_directory = (
                            self.station.base_dir + f"/{target_directory}" + "/Absorption_Scans/"
                        )
                    except (IndexError, AttributeError):
                        # EPICS path format is unexpected, use base directory as fallback
                        target_directory = self.station.base_dir
            except Exception:
                # EPICS connection failed, use base directory as fallback
                target_directory = self.station.base_dir
            
            if not target_directory:
                target_directory = self.station.base_dir

            dialog = QtWidgets.QFileDialog()
            dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)

            filename = dialog.getOpenFileName(
                dialog, "Open file", target_directory, "CSV Files (*.csv)"
            )

            if not filename[0]:  # User cancelled file dialog
                return
                
            self._loaded_file = filename[0]
            self.loaded_file_changed.emit(self._loaded_file)

            with open(filename[0], "r") as file:

                for line in file.readlines():
                    if line.startswith("# Scanned motor: "):
                        motor = line.split(" ")[3]

            y = []
            y_corrected = []

            try:
                x, y, y_corrected = np.loadtxt(
                    fname=filename[0],
                    dtype=float,
                    comments="#",
                    delimiter=",",
                    unpack=True,
                )
            except Exception as e:
                x, y = np.loadtxt(
                    fname=filename[0],
                    dtype=float,
                    comments="#",
                    delimiter=",",
                    unpack=True,
                )

            self.scanning_view.plot.reset_plot()

            if len(y_corrected) > 1:
                y_list = y_corrected
            else:
                y_list = y

            self.scanning_view.plot.update_plot_array(
                x_list=x, y_list=y_list, pv_name=motor
            )
            self.scanning_view.plot.rescale_plot()

    def scanning_procedure(
        self,
        trj_range: float,
        step: float,
        exposure: float,
        scanning_type: Optional[ScanProc] = ScanProc.Single,
    ):
        # Exit if trajectory is running.
        if self.station.trj_running:
            return None

        self.update_status(abort_status=False, running_status=False)
        self.station.aborted = False

        scan_mode = self.scanning_view.cmb_scan_mode.currentText()

        # Clear plot
        self.scanning_view.plot.reset_plot()

        # Clear loaded file
        self._loaded_file = ""
        self.loaded_file_changed.emit(self._loaded_file)

        if not self._test_mode:
            # Check hutch and beam
            if not self.station.check_beam_hutch_status():
                self.msg_prompt = PromptModel(
                    parent=self.scanning_view,
                    msg_title="Beam/Hutch",
                    msg_text="The ID-D hutch is not searched or there is no beam in the ring.",
                )
                self.update_status(
                    abort_status=False, running_status=False, label_text="Idle"
                )
                return None

        # Get energy and ring current
        if not self._test_mode:
            energy = caget(self.station.miscellaneous.energy.value[1])
            current = caget(self.station.miscellaneous.current.value[1])
        else:
            energy = 0
            current = 0

        target_stage = self.get_target_stage()
        scaler, correction_scaler = self.get_scalers()

        center = caget(target_stage)
        
        # Store scan state for abort recovery
        self._scan_target_stage = target_stage
        self._scan_center = center

        scan = self.scanning_model.create_scan(
            trj_range=trj_range, step=step, exposure=exposure, center=center
        )

        # Auto pinhole scan
        if scanning_type.value == ScanProc.Pinhole.value:
            # Check station.
            if self.station.prepare_for_scan(
                target_stage=target_stage, scan=scan, expert=self.station.expert_mode
            ):

                centering = False
                revert_position = False

                # Check abort status
                if not self.station.trj_aborted and not self.station.aborted:

                    # Set status
                    self.update_status(running_status=True, label_text="Scanning...")

                    scan_range = scan.lines[0].trj_range * 2

                    if scan_mode.lower() == "step":

                        if scaler[1] == self.station.scalers.s9.value[1]:
                            counter = self.station.miscellaneous.ketek_count.value[1]
                        else:
                            counter = self.station.miscellaneous.pd_count.value[1]
                        
                        pinhole_scan_thread = threading.Thread(
                            target=self.step_scan,
                            kwargs={
                                "target_stage": target_stage,
                                "pd_count": counter,
                                "scaler": scaler,
                                "exposure_time": exposure,
                                "positions": scan.lines[0].trj_positions,
                                "center": center,
                                "centering": centering,
                                "revert_position": revert_position,
                                "scan_mode": scan_mode,
                                "energy": energy,
                                "current": current,
                                "scan": scan,
                                "correction_scaler": correction_scaler,
                            },
                        )

                        self.station.prepare_shutter()

                    else:
                        xps_stage, xps_group = self.get_xps_stage_and_group()
                        scantime = scan.exposure_time * (scan.points - 1)

                        pinhole_scan_thread = threading.Thread(
                            target=self.fly_scan,
                            kwargs={
                                "xps_stage": xps_stage,
                                "xps_group": xps_group,
                                "scan_range": scan_range,
                                "scantime": scantime,
                                "step": step,
                                "scan": scan,
                                "target_stage": target_stage,
                                "center": center,
                                "centering": centering,
                                "revert_position": revert_position,
                                "scan_mode": scan_mode,
                                "energy": energy,
                                "current": current,
                            },
                        )

                    pinhole_scan_thread.start()

                    if scan_mode.lower() != "step":
                        read_data_thread = threading.Thread(
                            target=self.read_fly_data, kwargs={"scan": scan}
                        )
                        read_data_thread.start()

                    while self.station.trj_running and not self.station.trj_aborted and not self.station.aborted:
                        QtWidgets.QApplication.processEvents()

                    time.sleep(0.1)

                    if not self.station.trj_aborted and not self.station.aborted:
                        # Find peak and move horizontal
                        # peak = self.scanning_view.plot.find_peak()
                        peak = self.scanning_view.plot.fit(center=center, sigma=scan_range)

                        # Center
                        # center_position = (
                        #     self.scanning_view.plot.center_plot()
                        # )
                        QtWidgets.QApplication.processEvents()
                        time.sleep(0.1)
                        self._delta_position_changed.emit(center)
                        caput(target_stage, round(peak, 4), wait=True)

                        time.sleep(0.1)

                        # Check abort before starting second scan
                        if not self.station.trj_aborted and not self.station.aborted:
                            # Switch to vertical scan
                            self.set_target_stage(
                                self.station.stages.pinhole_vertical.value
                            )
                            target_stage = self.get_target_stage()
                            center = caget(target_stage)
                            
                            # Update stored scan state for second scan
                            self._scan_target_stage = target_stage
                            self._scan_center = center

                            scan = self.scanning_model.create_scan(
                                trj_range=trj_range,
                                step=step,
                                exposure=exposure,
                                center=center,
                            )

                            if self.station.prepare_for_scan(
                                target_stage=target_stage,
                                scan=scan,
                                expert=self.station.expert_mode,
                            ):

                                # Clear plot
                                self.scanning_view.plot.reset_plot()
                                QtWidgets.QApplication.processEvents()

                                # Set status
                                self.update_status(
                                    running_status=True, label_text="Scanning..."
                                )

                                scan_range = scan.lines[0].trj_range * 2

                                if scan_mode.lower() == "step":

                                    if scaler[1] == self.station.scalers.s9.value[1]:
                                        counter = self.station.miscellaneous.ketek_count.value[1]
                                    else:
                                        counter = self.station.miscellaneous.pd_count.value[1]
                                        
                                    pinhole_scan_thread = threading.Thread(
                                        target=self.step_scan,
                                        kwargs={
                                            "target_stage": target_stage,
                                            "pd_count": counter,
                                            "scaler": scaler,
                                            "exposure_time": exposure,
                                            "positions": scan.lines[0].trj_positions,
                                            "center": center,
                                            "centering": centering,
                                            "revert_position": revert_position,
                                            "scan_mode": scan_mode,
                                            "energy": energy,
                                            "current": current,
                                            "scan": scan,
                                            "correction_scaler": correction_scaler,
                                        },
                                    )

                                    self.station.prepare_shutter()

                                else:
                                    xps_stage, xps_group = self.get_xps_stage_and_group()
                                    scantime = scan.exposure_time * (scan.points - 1)

                                    pinhole_scan_thread = threading.Thread(
                                        target=self.fly_scan,
                                        kwargs={
                                            "xps_stage": xps_stage,
                                            "xps_group": xps_group,
                                            "scan_range": scan_range,
                                            "scantime": scantime,
                                            "step": step,
                                            "scan": scan,
                                            "target_stage": target_stage,
                                            "center": center,
                                            "centering": centering,
                                            "revert_position": revert_position,
                                            "scan_mode": scan_mode,
                                            "energy": energy,
                                            "current": current,
                                        },
                                    )

                                pinhole_scan_thread.start()

                                if scan_mode.lower() != "step":
                                    read_data_thread = threading.Thread(
                                        target=self.read_fly_data, kwargs={"scan": scan}
                                    )
                                    read_data_thread.start()

                                while self.station.trj_running and not self.station.trj_aborted and not self.station.aborted:
                                    QtWidgets.QApplication.processEvents()

                                time.sleep(0.1)

                                if not self.station.trj_aborted and not self.station.aborted:
                                    # Find peak and move horizontal
                                    # peak = self.scanning_view.plot.find_peak()
                                    peak = self.scanning_view.plot.fit(center=center, sigma=scan_range)

                                    # Center
                                    # center_position = (
                                    #     self.scanning_view.plot.center_plot()
                                    # )
                                    time.sleep(0.1)
                                    QtWidgets.QApplication.processEvents()
                                    self._delta_position_changed.emit(center)
                                    caput(target_stage, round(peak, 4), wait=True)

                                    time.sleep(0.1)
                            else:
                                # Clear stored values since prepare_for_scan failed for second scan
                                self._scan_target_stage = None
                                self._scan_center = None
                                self.msg_prompt = PromptModel(
                                    parent=self.scanning_view,
                                    msg_title="Collisions Errors - Stage Limits",
                                    msg_text="Please make sure to remove the mirrors and/or microscope.\n"
                                    "Make sure the scan range doesn't exceed the stage's limits.",
                                )
            else:
                # Clear stored values since prepare_for_scan failed
                self._scan_target_stage = None
                self._scan_center = None
                self.msg_prompt = PromptModel(
                    parent=self.scanning_view,
                    msg_title="Collisions Errors - Stage Limits",
                    msg_text="Please make sure to remove the mirrors and/or microscope.\n"
                    "Make sure the scan range doesn't exceed the stage's limits.",
                )

        # Auto center of rotation
        elif scanning_type.value == ScanProc.Centering.value:
            positions = None
            starting_position = None

            if self.scanning_view.lne_omega_rotation_range.text() is not None:
                centering_step = float(
                    self.scanning_view.lne_omega_rotation_range.text()
                )
                if isinstance(centering_step, float):
                    (
                        positions,
                        starting_position,
                    ) = self.station.auto_centering_positions(step=centering_step)
                else:
                    self.station.trj_aborted = True
                    self.station.aborted = True
                    print("Omega range cannot be empty.")
                    return None

            self.scanning_view.reset_save_labels()

            # Check station.
            if self.station.prepare_for_auto_centering(
                positions=positions, expert=self.station.expert_mode
            ):
                # Get stages
                scanning_stage, rotation_stage = self.station.auto_centering_stages()
                self.scanning_view.plot.target_position_motor = scanning_stage

                if self.station.prepare_for_scan(
                    target_stage=target_stage,
                    scan=scan,
                    expert=self.station.expert_mode,
                ):

                    # Set status
                    self.update_status(running_status=True, label_text="Scanning...")

                    revert_position = False

                    for i in range(0, len(positions), 1):
                        if not self.station.trj_aborted and not self.station.aborted:
                            if self.station.prepare_for_scan(
                                target_stage=target_stage,
                                scan=scan,
                                expert=self.station.expert_mode,
                            ):
                                if i < len(positions) - 1:
                                    centering = True
                                    position = positions[i + 1]
                                else:
                                    centering = False
                                    position = starting_position

                                # Check abort status
                                if not self.station.trj_aborted and not self.station.aborted:

                                    # Clear plot
                                    self.scanning_view.plot.reset_plot()

                                    # Set status
                                    self.update_status(
                                        running_status=True, label_text="Scanning..."
                                    )

                                    if scan_mode.lower() == "step":

                                        if scaler[1] == self.station.scalers.s9.value[1]:
                                            counter = self.station.miscellaneous.ketek_count.value[1]
                                        else:
                                            counter = self.station.miscellaneous.pd_count.value[1]

                                        centering_scan_thread = threading.Thread(
                                            target=self.step_scan,
                                            kwargs={
                                                "target_stage": target_stage,
                                                "pd_count": counter,
                                                "scaler": scaler,
                                                "exposure_time": exposure,
                                                "positions": scan.lines[
                                                    0
                                                ].trj_positions,
                                                "center": center,
                                                "centering": centering,
                                                "revert_position": revert_position,
                                                "scan_mode": scan_mode,
                                                "energy": energy,
                                                "current": current,
                                                "scan": scan,
                                                "correction_scaler": correction_scaler,
                                            },
                                        )

                                        self.station.prepare_shutter()

                                    else:
                                        (
                                            xps_stage,
                                            xps_group,
                                        ) = self.get_xps_stage_and_group()
                                        scan_range = scan.lines[0].trj_range * 2
                                        scantime = scan.exposure_time * (
                                            scan.points - 1
                                        )

                                        centering_scan_thread = threading.Thread(
                                            target=self.fly_scan,
                                            kwargs={
                                                "xps_stage": xps_stage,
                                                "xps_group": xps_group,
                                                "scan_range": scan_range,
                                                "scantime": scantime,
                                                "step": step,
                                                "scan": scan,
                                                "target_stage": target_stage,
                                                "center": center,
                                                "centering": centering,
                                                "revert_position": revert_position,
                                                "scan_mode": scan_mode,
                                                "energy": energy,
                                                "current": current,
                                            },
                                        )

                                    centering_scan_thread.start()

                                    if scan_mode.lower() != "step":
                                        read_data_thread = threading.Thread(
                                            target=self.read_fly_data,
                                            kwargs={"scan": scan},
                                        )
                                        read_data_thread.start()

                                    while self.station.trj_running and not self.station.trj_aborted and not self.station.aborted:
                                        QtWidgets.QApplication.processEvents()

                                    if not self.station.trj_aborted and not self.station.aborted:
                                        time.sleep(1.5)
                                        # Center
                                        center_position = (
                                            self.scanning_view.plot.center_plot()
                                        )

                                        QtWidgets.QApplication.processEvents()

                                        time.sleep(0.1)

                                        # Save position and move
                                        if i == 0:
                                            save_type = "negative"
                                        elif i == 1:
                                            save_type = "central"
                                        else:
                                            save_type = "positive"

                                        caput(
                                            scanning_stage[1],
                                            center_position,
                                            wait=True,
                                        )

                                        self.btn_save_clicked(save_type=save_type)

                                        QtWidgets.QApplication.processEvents()

                                        # Move rotation
                                        caput(rotation_stage[1], position, wait=True)

                                        # Add some delay to display the center position
                                        # Check abort during delay
                                        elapsed = 0
                                        while elapsed < 3 and not self.station.trj_aborted and not self.station.aborted:
                                            time.sleep(0.1)
                                            elapsed += 0.1
                                            QtWidgets.QApplication.processEvents()

                                        # Check abort before continuing to next scan
                                        if self.station.trj_aborted or self.station.aborted:
                                            break

                                        center = caget(target_stage)
                                        
                                        # Update stored scan state for next scan
                                        self._scan_target_stage = target_stage
                                        self._scan_center = center

                                        scan = self.scanning_model.create_scan(
                                            trj_range=trj_range,
                                            step=step,
                                            exposure=exposure,
                                            center=center,
                                        )

                                        if i > 2:
                                            # Clear plot
                                            self.scanning_view.plot.reset_plot()

                    # Handle abort - restore station and move rotation stage back
                    if self.station.trj_aborted or self.station.aborted:
                        # Restore station (close shutter, move motor back)
                        if self._scan_target_stage is not None and self._scan_center is not None:
                            self.station.restore_station(
                                target_stage=self._scan_target_stage,
                                center=self._scan_center,
                                centering=False,
                                revert_position=True,
                            )
                            # Clear stored values
                            self._scan_target_stage = None
                            self._scan_center = None
                        # Move rotation stage back to starting position
                        caput(rotation_stage[1], starting_position, wait=True)

                else:
                    # Clear stored values since prepare_for_scan failed
                    self._scan_target_stage = None
                    self._scan_center = None
                    self.msg_prompt = PromptModel(
                        parent=self.scanning_view,
                        msg_title="Collisions Errors - Stage Limits",
                        msg_text="Please make sure to remove the mirrors and/or microscope.\n"
                        "Make sure the scan range doesn't exceed the stage's limits.",
                    )
            else:
                # Clear stored values since prepare_for_auto_centering failed
                self._scan_target_stage = None
                self._scan_center = None
                self.msg_prompt = PromptModel(
                    parent=self.scanning_view,
                    msg_title="Collisions Errors - Stage Limits",
                    msg_text="Please make sure to remove the mirrors and/or microscope.\n"
                    "Make sure the scan range doesn't exceed the stage's limits.",
                )

        # Single scan
        else:
            # Check station.
            if self.station.prepare_for_scan(
                target_stage=target_stage, scan=scan, expert=self.station.expert_mode
            ):

                centering = False
                revert_position = True

                # Check abort status
                if not self.station.trj_aborted and not self.station.aborted:

                    # Set status
                    self.update_status(running_status=True, label_text="Scanning...")

                    if scan_mode.lower() == "step":

                        if scaler[1] == self.station.scalers.s9.value[1]:
                            counter = self.station.miscellaneous.ketek_count.value[1]
                        else:
                            counter = self.station.miscellaneous.pd_count.value[1]

                        single_scan_thread = threading.Thread(
                            target=self.step_scan,
                            kwargs={
                                "target_stage": target_stage,
                                "pd_count": counter,
                                "scaler": scaler,
                                "exposure_time": exposure,
                                "positions": scan.lines[0].trj_positions,
                                "center": center,
                                "centering": centering,
                                "revert_position": revert_position,
                                "scan_mode": scan_mode,
                                "energy": energy,
                                "current": current,
                                "scan": scan,
                                "correction_scaler": correction_scaler,
                            },
                        )

                        self.station.prepare_shutter()

                    else:
                        xps_stage, xps_group = self.get_xps_stage_and_group()
                        scan_range = scan.lines[0].trj_range * 2
                        scantime = scan.exposure_time * (scan.points - 1)

                        single_scan_thread = threading.Thread(
                            target=self.fly_scan,
                            kwargs={
                                "xps_stage": xps_stage,
                                "xps_group": xps_group,
                                "scan_range": scan_range,
                                "scantime": scantime,
                                "step": step,
                                "scan": scan,
                                "target_stage": target_stage,
                                "center": center,
                                "centering": centering,
                                "revert_position": revert_position,
                                "scan_mode": scan_mode,
                                "energy": energy,
                                "current": current,
                            },
                        )
                    single_scan_thread.start()

                    if scan_mode.lower() != "step":
                        read_data_thread = threading.Thread(
                            target=self.read_fly_data, kwargs={"scan": scan}
                        )
                        read_data_thread.start()
            else:
                # Clear stored values since prepare_for_scan failed
                self._scan_target_stage = None
                self._scan_center = None
                self.msg_prompt = PromptModel(
                    parent=self.scanning_view,
                    msg_title="Collisions Errors - Stage Limits",
                    msg_text="Please make sure to remove the mirrors and/or microscope.\n"
                    "Make sure the scan range doesn't exceed the stage's limits.",
                )

    def step_scan(
        self,
        target_stage: str,
        pd_count: str,
        scaler: List[str],
        exposure_time: float,
        positions: List,
        center: float,
        centering: bool,
        revert_position: bool,
        scan_mode: str,
        energy: float,
        current: float,
        scan: MapModel,
        correction_scaler: Optional[List[str]] = None,
    ):
        sleep_time = exposure_time + 0.1

        if scaler != self.station.scalers.s9.value[1]:
            # Set count type to oneshot
            caput(self.station.miscellaneous.pd_count_type.value[1], 0)
            time.sleep(0.5)

            # Set scaler counter to done state
            caput(self.station.miscellaneous.pd_count.value[1], 0)

            # Set exposure time.
            caput(self.station.miscellaneous.pd_count_time.value[1], exposure_time)

        caput(pd_count, 1)
        # Break sleep into smaller chunks to check abort status
        elapsed = 0
        while elapsed < sleep_time and not self.station.trj_aborted and not self.station.aborted:
            time.sleep(0.1)
            elapsed += 0.1

        if self.station.trj_aborted or self.station.aborted:
            # Still need to call scan_finished to restore station and reset status
            if correction_scaler is not None:
                raw_data = self.raw_data
            else:
                raw_data = []
            self.scan_finished(
                target_stage=target_stage,
                center=center,
                centering=centering,
                revert_position=revert_position,
                scan=scan,
                scan_mode=scan_mode,
                energy=energy,
                current=current,
                scaler=scaler,
                correction_scaler=correction_scaler,
                raw_data=raw_data,
            )
            return

        # Read counts
        counts = caget(scaler[1])
        if correction_scaler is not None:
            self.raw_data.append(counts)
            correction_counts = caget(correction_scaler[1])
            counts = counts - correction_counts

        # Update the plot
        self.scanning_view.plot.update_plot(x=positions[0], y=counts, auto_scale=True)

        for i in range(1, len(positions)):

            # Check abort status
            if not self.station.trj_aborted and not self.station.aborted:

                # Move to the next position.
                position = positions[i]
                caput(target_stage, position, wait=True)

                # Count
                caput(pd_count, 1)
                # Break sleep into smaller chunks to check abort status
                elapsed = 0
                while elapsed < sleep_time and not self.station.trj_aborted and not self.station.aborted:
                    time.sleep(0.1)
                    elapsed += 0.1

                if self.station.trj_aborted or self.station.aborted:
                    break

                # Read counts
                counts = caget(scaler[1])
                if correction_scaler is not None:
                    self.raw_data.append(counts)
                    correction_counts = caget(correction_scaler[1])
                    counts = counts - correction_counts

                # Update plot
                self.scanning_view.plot.update_plot(
                    x=positions[i], y=counts, auto_scale=True
                )

        if correction_scaler is not None:
            raw_data = self.raw_data
        else:
            raw_data = []

        self.scan_finished(
            target_stage=target_stage,
            center=center,
            centering=centering,
            revert_position=revert_position,
            scan=scan,
            scan_mode=scan_mode,
            energy=energy,
            current=current,
            scaler=scaler,
            correction_scaler=correction_scaler,
            raw_data=raw_data,
        )

    @staticmethod
    def get_correction_status(correction_scaler: List[str] = None):
        # Set correction status
        if correction_scaler is not None:
            correction = True
        else:
            correction = False

        return correction

    def update_status(
        self,
        abort_status: Optional[bool] = None,
        running_status: Optional[bool] = None,
        label_text: Optional[str] = None,
    ):

        if abort_status is not None:
            self.station.trj_aborted = abort_status

        if running_status is not None:
            self.station.trj_running = running_status

        if label_text is not None:

            if label_text == "Idle":
                color = "ForestGreen"
            else:
                color = "LightCoral"

            self._update_status_label(label_text, color)

        if self.station.trj_running:
            self.scan_running.emit(True)
        else:
            self.scan_running.emit(False)

    def get_target_stage(self):
        if len(self.scanning_view.plot.target_position_motor) < 1:
            target_stage = None
        else:
            target_stage = self.scanning_view.plot.target_position_motor[1]

        return target_stage

    def get_xps_stage_and_group(self):
        if len(self.scanning_view.plot.target_position_motor) < 1:
            target_stage = None
            group = None
        else:
            target_stage = self.scanning_view.plot.target_position_motor[2]
            group = self.scanning_view.plot.target_position_motor[3]

        return target_stage, group

    def get_scalers(self):
        target_scaler = None
        correction_scaler = None

        for scaler in self.station.scalers:
            if self.scanning_view.cmb_scaler.currentText() == scaler.value[0]:
                target_scaler = [scaler.value[0], scaler.value[1]]

            if (
                self.scanning_view.cmb_correction_scaler.currentText()
                == scaler.value[0]
            ):
                correction_scaler = [scaler.value[0], scaler.value[1]]

        if target_scaler is None or target_scaler[0] == "None":
            self.msg_prompt = PromptModel(
                parent=self.scanning_view,
                msg_title="Missing scaler",
                msg_text="Please select a scaler.",
            )
            return None

        if correction_scaler is None or correction_scaler[0] == "None":
            correction_scaler = None
        elif correction_scaler[0] == target_scaler[0]:
            correction_scaler = None

        return target_scaler, correction_scaler

    def scan_finished(
        self,
        target_stage: str,
        center: float,
        centering: bool,
        revert_position: bool,
        scan: MapModel,
        scan_mode: str,
        energy: float,
        current: float,
        scaler: Optional[List[str]] = None,
        correction_scaler: Optional[List[str]] = None,
        raw_data: Optional[List[float]] = None,
    ) -> None:

        if self.station.trj_aborted:
            revert_position = True
            centering = False

        # Reset station
        self.station.restore_station(
            target_stage=target_stage,
            center=center,
            centering=centering,
            revert_position=revert_position,
        )
        
        # Clear stored scan state
        self._scan_target_stage = None
        self._scan_center = None

        # Set status
        self.update_status(abort_status=False, running_status=False, label_text="Idle")

        # Set/Create directory
        target_directory = caget("13IDDLF1:cam1:FilePath.VAL", as_string=True)
        target_directory = target_directory.split("\\")[4].strip()
        target_directory = os.path.join(self.station.base_dir, os.path.join(target_directory, "Absorption_Scans"))

        print(target_directory)

        if not os.path.exists(target_directory):
            os.mkdir(target_directory)

        # Save data
        self.scanning_view.plot.save_to_file(
            station=self.station.name,
            base_dir=target_directory,
            filename=target_stage,
            stage=target_stage,
            scan=scan,
            mode=scan_mode.capitalize() + " scan",
            center=center,
            energy=energy,
            current=current,
            scaler=scaler,
            correction_scaler=correction_scaler,
            aborted=self.station.trj_aborted,
            raw_data=raw_data,
            test_mode=self._test_mode,
        )
