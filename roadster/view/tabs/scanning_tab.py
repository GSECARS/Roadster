import os
from qtpy import QtWidgets, QtCore, QtGui

import math

from roadster.view.drawing import VLine, HLine
from roadster.view.tabs import BasePlotWidget


class ScanningTab(QtWidgets.QWidget):
    def __init__(self) -> None:
        super(ScanningTab, self).__init__(flags=QtCore.Qt.WindowFlags())

        # TODO: Change the plot widget.
        self.plot = BasePlotWidget()

        # Expert mode widgets
        self.btn_expert_toggle = QtWidgets.QPushButton()
        self.lbl_expert_user_mode = QtWidgets.QLabel()

        # Custom scan widgets
        self.lne_custom_scan = QtWidgets.QLineEdit()
        self.btn_custom_scan = QtWidgets.QPushButton()
        self.lbl_custom = QtWidgets.QLabel()

        # Create scanning tab widgets.
        self.lbl_range = QtWidgets.QLabel()
        self.lbl_step = QtWidgets.QLabel()
        self.lbl_exposure = QtWidgets.QLabel()
        self.lbl_scan_mode = QtWidgets.QLabel()
        self.lbl_scan_type = QtWidgets.QLabel()
        self.lbl_scaler = QtWidgets.QLabel()
        self.lbl_correction_scaler = QtWidgets.QLabel()
        self.lbl_pinhole = QtWidgets.QLabel()
        self.lbl_sample = QtWidgets.QLabel()
        self.lbl_center_rotation = QtWidgets.QLabel()
        self.lbl_omega_rotation_range = QtWidgets.QLabel()
        self.lbl_scanning_status = QtWidgets.QLabel()
        self.lbl_saved_central_position = QtWidgets.QLabel()
        self.lbl_saved_negative_position = QtWidgets.QLabel()
        self.lbl_saved_positive_position = QtWidgets.QLabel()
        self.lbl_centering_correction = QtWidgets.QLabel()
        self.lbl_calculated_correction = QtWidgets.QLabel()

        self.lne_range = QtWidgets.QLineEdit()
        self.lne_step = QtWidgets.QLineEdit()
        self.lne_exposure = QtWidgets.QLineEdit()
        self.lne_omega_rotation_range = QtWidgets.QLineEdit()

        self.cmb_scan_mode = QtWidgets.QComboBox()
        self.cmb_scan_type = QtWidgets.QComboBox()
        self.cmb_scaler = QtWidgets.QComboBox()
        self.cmb_correction_scaler = QtWidgets.QComboBox()

        self.btn_pinhole_vertical = QtWidgets.QPushButton()
        self.btn_pinhole_horizontal = QtWidgets.QPushButton()
        self.btn_pinhole_auto = QtWidgets.QPushButton()
        self.btn_sample_vertical = QtWidgets.QPushButton()
        self.btn_sample_horizontal = QtWidgets.QPushButton()
        self.btn_sample_focus = QtWidgets.QPushButton()
        self.btn_sample_omega = QtWidgets.QPushButton()
        self.btn_auto_centering = QtWidgets.QPushButton()
        self.btn_abort_scan = QtWidgets.QPushButton()
        self.btn_reset_saved = QtWidgets.QPushButton()
        self.btn_save_central_position = QtWidgets.QPushButton()
        self.btn_save_negative_position = QtWidgets.QPushButton()
        self.btn_save_positive_position = QtWidgets.QPushButton()
        self.btn_apply_correction = QtWidgets.QPushButton()

        self.check_test_mode = QtWidgets.QCheckBox("Test mode")

        self.main_scanning_layout = QtWidgets.QVBoxLayout()
        self.main_layout = QtWidgets.QHBoxLayout()

        self.cmb_scan_mode.currentIndexChanged.connect(self.update_buttons)

        self._init_tab_ui()

    def _init_tab_ui(self) -> None:
        self._layout_scanning()
        self._config_labels()
        self._config_line_edit()
        self._config_combo_boxes()
        self._config_buttons()

    def update_buttons(self):
        if self.cmb_scan_mode.currentText() == "Fly":
            self.btn_sample_omega.setEnabled(False)
            self.btn_custom_scan.setEnabled(False)
            self.lne_custom_scan.setEnabled(False)
        else:
            self.btn_sample_omega.setEnabled(True)
            self.btn_custom_scan.setEnabled(True)
            self.lne_custom_scan.setEnabled(True)

    def _config_labels(self) -> None:
        """Configuration of the scanning tab labels."""
        # Set the text.
        self.lbl_range.setText("Range (\u00B1)")
        self.lbl_step.setText("Step")
        self.lbl_exposure.setText("Exposure")
        self.lbl_scan_mode.setText("Scan mode")
        self.lbl_scan_type.setText("Scan type")
        self.lbl_scaler.setText("Scaler")
        self.lbl_correction_scaler.setText("Correction Scaler")
        self.lbl_sample.setText("Sample")
        self.lbl_pinhole.setText("Pinhole")
        self.lbl_scanning_status.setText("Idle")
        self.lbl_center_rotation.setText("Center of Rotation")
        self.lbl_omega_rotation_range.setText("Ω Range (\u00B1)")
        self.lbl_saved_central_position.setText("None")
        self.lbl_saved_negative_position.setText("None")
        self.lbl_saved_positive_position.setText("None")
        self.lbl_centering_correction.setText("None")
        self.lbl_calculated_correction.setText("Calculated correction:")
        self.lbl_expert_user_mode.setText("User mode")
        self.lbl_custom.setText("Custom")

        # Set the font and size.
        font = QtGui.QFont("Microsoft Sans Serif", 9)
        medium_font = QtGui.QFont("Microsoft Sans Serif", 12)
        big_font = QtGui.QFont("Microsoft Sans Serif", 18)
        self.lbl_range.setFont(font)
        self.lbl_step.setFont(font)
        self.lbl_exposure.setFont(font)
        self.lbl_scan_mode.setFont(font)
        self.lbl_scaler.setFont(font)
        self.lbl_correction_scaler.setFont(font)
        self.lbl_sample.setFont(font)
        self.lbl_pinhole.setFont(font)
        self.lbl_scanning_status.setFont(big_font)
        self.lbl_center_rotation.setFont(medium_font)
        self.lbl_omega_rotation_range.setFont(font)
        self.lbl_calculated_correction.setFont(font)
        self.lbl_expert_user_mode.setFont(font)
        self.lbl_custom.setFont(font)

        # Set color
        self.lbl_expert_user_mode.setStyleSheet("color: forestgreen;")
        self.lbl_scanning_status.setStyleSheet("color: forestgreen;")
        self.lbl_sample.setStyleSheet("font-size: 13px;" "color: #2e3652;")
        self.lbl_pinhole.setStyleSheet("font-size: 13px;" "color: #38522e;")

    def _config_line_edit(self) -> None:
        """Configuration of the scanning tab line edit widgets."""
        # Set the font and size of the text.
        font = QtGui.QFont("Consolas", 9)
        self.lne_range.setFont(font)
        self.lne_step.setFont(font)
        self.lne_exposure.setFont(font)
        self.lne_omega_rotation_range.setFont(font)
        self.lne_custom_scan.setFont(font)

        # Set the widget size.
        size = QtCore.QSize(70, 20)
        self.lne_range.setFixedSize(size)
        self.lne_step.setFixedSize(size)
        self.lne_exposure.setFixedSize(size)
        self.lne_omega_rotation_range.setFixedSize(85, 25)
        self.lne_custom_scan.setFixedSize(95, 25)

        # Set alignment.
        alignment = QtCore.Qt.AlignCenter
        self.lne_range.setAlignment(alignment)
        self.lne_step.setAlignment(alignment)
        self.lne_exposure.setAlignment(alignment)
        self.lne_omega_rotation_range.setAlignment(alignment)
        self.lne_custom_scan.setAlignment(alignment)

        # Input validation
        reg_exp = QtCore.QRegExp("-?[0-9]+.?[0-9]{,5}")
        validator = QtGui.QRegExpValidator(reg_exp, self)
        self.lne_range.setValidator(validator)
        self.lne_step.setValidator(validator)
        self.lne_exposure.setValidator(validator)
        self.lne_omega_rotation_range.setValidator(validator)

        # Set placeholders
        self.lne_range.setPlaceholderText("mm, deg")
        self.lne_step.setPlaceholderText("mm, deg")
        self.lne_exposure.setPlaceholderText("seconds")
        self.lne_exposure.setPlaceholderText("deg")
        self.lne_omega_rotation_range.setPlaceholderText("deg")
        self.lne_custom_scan.setPlaceholderText("PV name")

        # Set starting values
        self.lne_range.setText("0.1")
        self.lne_step.setText("0.01")
        self.lne_exposure.setText("0.1")
        self.lne_omega_rotation_range.setText("1")

    def _config_combo_boxes(self) -> None:
        """Configuration of the scanning tab combo box widgets."""
        # Set active item.
        self.cmb_scan_mode.setCurrentIndex(0)
        self.cmb_scan_type.setCurrentIndex(0)
        self.cmb_scaler.setCurrentIndex(0)
        self.cmb_correction_scaler.setCurrentIndex(0)

        # Set widget size
        size = QtCore.QSize(70, 25)
        self.cmb_scan_mode.setFixedSize(size)
        self.cmb_scan_type.setFixedSize(size)
        self.cmb_scaler.setFixedSize(size)
        self.cmb_correction_scaler.setFixedSize(size)

    def _config_buttons(self) -> None:
        """Configuration of the scanning tab push button widgets."""
        # Set the text.
        self.btn_pinhole_vertical.setText("Vertical")
        self.btn_pinhole_horizontal.setText("Horizontal")
        self.btn_pinhole_auto.setText("Auto")
        self.btn_sample_vertical.setText("Vertical")
        self.btn_sample_horizontal.setText("Horizontal")
        self.btn_sample_focus.setText("Focus")
        self.btn_sample_omega.setText("Omega")
        self.btn_auto_centering.setText("Auto Center")
        self.btn_abort_scan.setText("Abort")
        self.btn_reset_saved.setText("Reset Saved")
        self.btn_save_central_position.setText("Save Central")
        self.btn_save_negative_position.setText("Save Negative")
        self.btn_save_positive_position.setText("Save Positive")
        self.btn_apply_correction.setText("Apply Correction")
        self.btn_expert_toggle.setText("Toggle")
        self.btn_custom_scan.setText("Scan")

        # Set widget size
        size = QtCore.QSize(82, 25)
        bigger_size = QtCore.QSize(125, 25)
        big_font = QtGui.QFont("Microsoft Sans Serif", 12)
        self.btn_pinhole_vertical.setFixedSize(size)
        self.btn_pinhole_horizontal.setFixedSize(size)
        self.btn_pinhole_auto.setFixedSize(size)
        self.btn_sample_vertical.setFixedSize(bigger_size)
        self.btn_sample_horizontal.setFixedSize(bigger_size)
        self.btn_sample_focus.setFixedSize(bigger_size)
        self.btn_sample_omega.setFixedSize(bigger_size)
        self.btn_auto_centering.setFixedHeight(32)
        self.btn_apply_correction.setFixedHeight(25)
        self.btn_reset_saved.setFixedHeight(32)
        self.btn_save_central_position.setFixedSize(size)
        self.btn_save_negative_position.setFixedSize(size)
        self.btn_save_positive_position.setFixedSize(size)
        self.btn_expert_toggle.setFixedSize(70, 25)
        self.btn_custom_scan.setFixedSize(size)

        # TODO: Make expandable.
        self.btn_abort_scan.setFixedHeight(45)
        self.btn_abort_scan.setFont(big_font)

        sample_buttons = [
            self.btn_sample_vertical,
            self.btn_sample_horizontal,
            self.btn_sample_focus,
            self.btn_sample_omega,
        ]

        pinhole_buttons = [
            self.btn_pinhole_vertical,
            self.btn_pinhole_horizontal,
            self.btn_pinhole_auto,
        ]

        [button.setObjectName("btn-sample") for button in sample_buttons]
        [button.setObjectName("btn-pinhole") for button in pinhole_buttons]

    def update_save_labels(
        self, position: float, omega_position: float, label: QtWidgets.QLabel
    ):
        if position is not None and label is not None:
            label.setText(str(position) + ", " + str(omega_position))
        else:
            label.setText("None")

        save_labels = [
            self.lbl_saved_central_position,
            self.lbl_saved_positive_position,
            self.lbl_saved_negative_position,
        ]

        for lbl in save_labels:
            if lbl.text() == "None":
                return None

        self.calculate_focal_correction()

    def reset_save_labels(self):
        labels = [
            self.lbl_saved_negative_position,
            self.lbl_saved_positive_position,
            self.lbl_saved_central_position,
            self.lbl_centering_correction,
        ]

        for label in labels:
            label.setText("None")

    def calculate_focal_correction(self):
        ch = float(self.lbl_saved_central_position.text().split(",")[0].strip())
        ph = float(self.lbl_saved_positive_position.text().split(",")[0].strip())
        nh = float(self.lbl_saved_negative_position.text().split(",")[0].strip())

        co = float(self.lbl_saved_central_position.text().split(",")[1].strip())
        po = float(self.lbl_saved_positive_position.text().split(",")[1].strip())
        no = float(self.lbl_saved_negative_position.text().split(",")[1].strip())

        focal_correction = round(
            (
                ((ch - ph) - (ch - nh))
                / (2 * math.sin(((po - no) / 2) * (math.pi / 180)))
            ),
            4,
        )

        self.lbl_centering_correction.setText(str(focal_correction) + " mm")

    def _layout_scanning(self) -> None:

        # Scanning setup section layout.
        layout_setup_scan = QtWidgets.QGridLayout()
        layout_setup_scan.setHorizontalSpacing(10)
        layout_setup_scan.setContentsMargins(0, 0, 0, 0)
        layout_setup_scan.addWidget(
            self.lbl_range, 0, 0, 1, 1, alignment=QtCore.Qt.AlignLeft
        )
        layout_setup_scan.addWidget(
            self.lne_range, 0, 1, 1, 1, alignment=QtCore.Qt.AlignLeft
        )
        layout_setup_scan.addWidget(
            self.lbl_step, 1, 0, 1, 1, alignment=QtCore.Qt.AlignLeft
        )

        layout_setup_scan.addWidget(
            self.lne_step, 1, 1, 1, 1, alignment=QtCore.Qt.AlignLeft
        )

        layout_setup_scan.addWidget(
            self.lbl_exposure, 2, 0, 1, 1, alignment=QtCore.Qt.AlignLeft
        )
        layout_setup_scan.addWidget(
            self.lne_exposure, 2, 1, 1, 1, alignment=QtCore.Qt.AlignLeft
        )

        layout_setup_scan.addWidget(
            self.lbl_scan_mode, 0, 2, 1, 1, alignment=QtCore.Qt.AlignRight
        )
        layout_setup_scan.addWidget(
            self.cmb_scan_mode, 0, 3, 1, 1, alignment=QtCore.Qt.AlignRight
        )
        layout_setup_scan.addWidget(
            self.lbl_scan_type, 1, 2, 1, 1, alignment=QtCore.Qt.AlignRight
        )
        layout_setup_scan.addWidget(
            self.cmb_scan_type, 1, 3, 1, 1, alignment=QtCore.Qt.AlignRight
        )

        layout_setup_scan.addWidget(
            self.lbl_scaler, 3, 0, 1, 1, alignment=QtCore.Qt.AlignLeft
        )
        layout_setup_scan.addWidget(
            self.cmb_scaler, 3, 1, 1, 1, alignment=QtCore.Qt.AlignRight
        )

        layout_setup_scan.addWidget(
            self.lbl_correction_scaler, 3, 2, 1, 1, alignment=QtCore.Qt.AlignLeft
        )
        layout_setup_scan.addWidget(
            self.cmb_correction_scaler, 3, 3, 1, 1, alignment=QtCore.Qt.AlignLeft
        )

        layout_setup_scan.addWidget(
            self.lbl_expert_user_mode, 2, 2, 1, 1, alignment=QtCore.Qt.AlignRight
        )
        layout_setup_scan.addWidget(
            self.btn_expert_toggle, 2, 3, 1, 1, alignment=QtCore.Qt.AlignRight
        )

        # Scanning buttons section layout.
        layout_fly_scan_buttons = QtWidgets.QGridLayout()
        layout_fly_scan_buttons.setHorizontalSpacing(5)
        layout_fly_scan_buttons.setVerticalSpacing(2)
        layout_fly_scan_buttons.setContentsMargins(0, 0, 0, 0)
        layout_fly_scan_buttons.addWidget(
            self.lbl_sample, 0, 0, 1, 1, alignment=QtCore.Qt.AlignLeft
        )
        layout_fly_scan_buttons.addWidget(
            self.btn_sample_horizontal, 0, 1, 1, 1, alignment=QtCore.Qt.AlignCenter
        )
        layout_fly_scan_buttons.addWidget(
            self.btn_sample_vertical, 0, 2, 1, 1, alignment=QtCore.Qt.AlignCenter
        )

        layout_fly_scan_buttons.addWidget(
            self.btn_sample_focus, 1, 1, 1, 1, alignment=QtCore.Qt.AlignCenter
        )

        layout_fly_scan_buttons.addWidget(
            self.btn_sample_omega, 1, 2, 1, 1, alignment=QtCore.Qt.AlignCenter
        )

        layout_step_scan_buttons = QtWidgets.QGridLayout()
        layout_step_scan_buttons.setHorizontalSpacing(5)
        layout_step_scan_buttons.setContentsMargins(0, 0, 0, 0)
        layout_step_scan_buttons.addWidget(
            self.lbl_pinhole,
            0,
            0,
            1,
            1,
            alignment=QtCore.Qt.AlignLeft,
        )
        layout_step_scan_buttons.addWidget(
            self.btn_pinhole_horizontal, 0, 1, 1, 1, alignment=QtCore.Qt.AlignCenter
        )
        layout_step_scan_buttons.addWidget(
            self.btn_pinhole_vertical, 0, 2, 1, 1, alignment=QtCore.Qt.AlignCenter
        )
        layout_step_scan_buttons.addWidget(
            self.btn_pinhole_auto, 0, 3, 1, 1, alignment=QtCore.Qt.AlignCenter
        )

        layout_custom_scan = QtWidgets.QGridLayout()
        layout_custom_scan.setContentsMargins(0, 0, 0, 0)
        layout_custom_scan.setSpacing(5)
        layout_custom_scan.setAlignment(QtCore.Qt.AlignRight)
        layout_custom_scan.addWidget(
            self.lbl_custom, 0, 2, 1, 1, alignment=QtCore.Qt.AlignCenter
        )
        layout_custom_scan.addWidget(
            self.btn_custom_scan, 0, 3, 1, 1, alignment=QtCore.Qt.AlignCenter
        )
        layout_custom_scan.addWidget(self.lne_custom_scan, 0, 4, 1, 2)

        layout_center_of_rotation = QtWidgets.QVBoxLayout()
        layout_center_of_rotation.setContentsMargins(0, 20, 0, 0)
        layout_center_of_rotation.addWidget(
            self.lbl_center_rotation, alignment=QtCore.Qt.AlignCenter
        )

        layout_center_of_rotation_contents = QtWidgets.QHBoxLayout()

        layout_center_col_1 = QtWidgets.QGridLayout()
        layout_center_col_1.addWidget(self.btn_auto_centering, 0, 0, 1, 3)
        layout_center_col_1.addWidget(self.lbl_omega_rotation_range, 1, 0, 1, 1)
        layout_center_col_1.addWidget(
            self.lne_omega_rotation_range, 1, 1, 1, 2, alignment=QtCore.Qt.AlignRight
        )
        layout_center_col_1.addWidget(self.btn_apply_correction, 2, 0, 1, 3)
        layout_center_col_1.addWidget(self.lbl_calculated_correction, 3, 0, 1, 2)
        layout_center_col_1.addWidget(self.lbl_centering_correction, 3, 2, 1, 1)

        layout_center_col_2 = QtWidgets.QGridLayout()
        layout_center_col_2.addWidget(self.btn_reset_saved, 0, 0, 1, 3)
        layout_center_col_2.addWidget(self.btn_save_central_position, 1, 0, 1, 2)
        layout_center_col_2.addWidget(self.lbl_saved_central_position, 1, 2, 1, 1)
        layout_center_col_2.addWidget(self.btn_save_negative_position, 2, 0, 1, 2)
        layout_center_col_2.addWidget(self.lbl_saved_negative_position, 2, 2, 1, 1)
        layout_center_col_2.addWidget(self.btn_save_positive_position, 3, 0, 1, 2)
        layout_center_col_2.addWidget(self.lbl_saved_positive_position, 3, 2, 1, 1)

        layout_center_of_rotation_contents.addLayout(layout_center_col_1)
        layout_center_of_rotation_contents.addLayout(layout_center_col_2)

        layout_center_of_rotation.addLayout(layout_center_of_rotation_contents)

        layout_status = QtWidgets.QHBoxLayout()
        layout_status.setSpacing(10)
        layout_status.addWidget(
            self.lbl_scanning_status, alignment=QtCore.Qt.AlignRight
        )
        layout_status.addWidget(self.check_test_mode, alignment=QtCore.Qt.AlignRight)

        # Main layout.
        self.main_scanning_layout.addLayout(layout_setup_scan)
        self.main_scanning_layout.addWidget(HLine())
        self.main_scanning_layout.addLayout(layout_step_scan_buttons)
        self.main_scanning_layout.addWidget(HLine())
        self.main_scanning_layout.addLayout(layout_fly_scan_buttons)
        self.main_scanning_layout.addWidget(HLine())
        self.main_scanning_layout.addLayout(layout_custom_scan)
        self.main_scanning_layout.addWidget(HLine())
        self.main_scanning_layout.addLayout(layout_center_of_rotation)
        self.main_scanning_layout.addWidget(HLine())
        self.main_scanning_layout.addStretch(1)

        self.main_scanning_layout.addLayout(layout_status)
        # self.main_scanning_layout.addWidget(self.lbl_scanning_status, alignment=QtCore.Qt.AlignCenter)

        self.main_scanning_layout.addWidget(self.btn_abort_scan)

        self.main_layout.addWidget(self.plot)
        self.main_layout.setSpacing(10)
        self.main_layout.addLayout(self.main_scanning_layout)

        self.setLayout(self.main_layout)
