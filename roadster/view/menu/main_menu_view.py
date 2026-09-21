from qtpy import QtWidgets

from roadster.view.menu import GeneralConfigView, StageConfigView, ScalerConfigView


class MainMenuView(QtWidgets.QMenuBar):
    """Application menu widget."""

    def __init__(self) -> None:
        super(MainMenuView, self).__init__()

        # Menus
        self.file_menu = None
        self.settings_menu = None

        # Actions
        self.general_config_action = None
        self.stage_config_action = None
        self.scaler_config_action = None

        # Additional windows
        self.general_config_window = GeneralConfigView()
        self.stage_config_window = StageConfigView()
        self.scaler_config_window = ScalerConfigView()

        self.add_menus()
        self.add_actions()
        self.connect_actions()

    def add_menus(self) -> None:
        """Add menus to the menu widget."""
        self.file_menu = QtWidgets.QMenu("&File", self)
        self.settings_menu = QtWidgets.QMenu("&Settings", self)

        self.addMenu(self.file_menu)
        self.addMenu(self.settings_menu)

    def add_actions(self) -> None:
        """Add menu actions."""
        self.general_config_action = QtWidgets.QAction("General")
        self.stage_config_action = QtWidgets.QAction("Stages")
        self.scaler_config_action = QtWidgets.QAction("Scalers")

        self.settings_menu.addAction(self.general_config_action)
        self.settings_menu.addAction(self.stage_config_action)
        self.settings_menu.addAction(self.scaler_config_action)

    def connect_actions(self) -> None:
        """Connects the triggered states of actions."""
        self.general_config_action.triggered.connect(
            lambda: self.show_additional_window(self.general_config_window)
        )

        self.stage_config_action.triggered.connect(
            lambda: self.show_additional_window(self.stage_config_window)
        )

        self.scaler_config_action.triggered.connect(
            lambda: self.show_additional_window(self.scaler_config_window)
        )

    @staticmethod
    def show_additional_window(window: QtWidgets.QWidget):
        """Used to display additional windows."""
        # Check if the window is already open
        if window.isVisible():
            window.activateWindow()
        else:
            window.show()
