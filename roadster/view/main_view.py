import os

from qtpy import QtCore, QtWidgets

from roadster.model import PromptModel, qss_path
from roadster.view.tabs.scanning_tab import ScanningTab


class MainView(QtWidgets.QMainWindow):
    """Main application window."""

    def __init__(self):
        super(MainView, self).__init__(flags=QtCore.Qt.WindowFlags())

        self.setStyleSheet(open(os.path.join(qss_path, "style.qss"), "r").read())

        # self.menu = MainMenuView()
        # self.tabs = MainTabView()
        self.scanning = ScanningTab()

        self.init_ui()

    def init_ui(self) -> None:
        """Init of ui elements."""
        # TODO: Add an application icon. (.ico)
        # TODO: Add a QSplashScreen.

        # Add the main application menu.
        # self.setMenuBar(self.menu)

        # Set tab widget as central application widget.
        # self.setCentralWidget(self.tabs)
        self.setCentralWidget(self.scanning)

    def display_main_window(self, version: str = ""):
        self.setWindowTitle(f"Roadster {version}")
        self.showNormal()

    def closeEvent(self, event) -> None:
        prompt = PromptModel(
            parent=self,
            msg_title="Close Application",
            msg_text="Are you sure you want to close the application?",
            user_prompt=True,
        )

        if prompt.response:
            event.accept()
        else:
            event.ignore()
