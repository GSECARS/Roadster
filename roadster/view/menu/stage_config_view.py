from qtpy import QtWidgets

from roadster.model import OptionsModel


class StageConfigView(QtWidgets.QWidget):
    def __init__(self):
        super(StageConfigView, self).__init__()

        self.title = "Configuration"

        self.options = OptionsModel()

        self._init_ui()

    def _init_ui(self) -> None:
        self.setWindowTitle(self.title)
