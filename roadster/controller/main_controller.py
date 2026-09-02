import sys

from qtpy.QtWidgets import QApplication

from roadster.controller.options_controller import OptionsController
from roadster.controller.scanning_controller import ScanningController
from roadster.model import MainModel
from roadster.view import MainView


class MainController:
    """
    This class is used to implement Controller part of the MVC pattern for python.
    Helps to bring together the model and the view parts of the application.
    """

    def __init__(self) -> None:
        # Create core app, views and models.
        self._app = QApplication(sys.argv)
        self._model = MainModel()
        self._view = MainView()

        # Specific controller section modules.
        self.options = OptionsController(self._model, self._view)
        self.scanning = ScanningController(self._model, self._view)

        self.scanning.loaded_file_changed.connect(self._change_window_title)
        self._view.scanning.plot.new_file_saved.connect(self._change_window_title)

    def run(self, version: str) -> None:
        """Used to start the application."""
        self._view.display_main_window(version)
        sys.exit(self._app.exec())

    def _change_window_title(self, text: str) -> None:
        if not text:
            self._view.setWindowTitle("Roadster")
        else:
            self._view.setWindowTitle(f"Roadster - {text}")
