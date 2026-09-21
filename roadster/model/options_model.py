from qtpy import QtCore
from roadster.model.config.idd.idd_model import IDDModel

ORGANIZATION = "GSECARS"
APPNAME = "Roadster"


class OptionsModel:
    """Represents the available application options."""

    def __init__(self) -> None:

        self.app_settings = QtCore.QSettings("settings.ini", QtCore.QSettings.IniFormat)

        self.station = IDDModel()
