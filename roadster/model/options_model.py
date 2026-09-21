from qtpy import QtCore
from roadster.model.config.bmc.bmc_model import BMCModel

ORGANIZATION = "GSECARS"
APPNAME = "Roadster"


class OptionsModel:
    """Represents the available application options."""

    def __init__(self) -> None:

        self.app_settings = QtCore.QSettings("settings.ini", QtCore.QSettings.IniFormat)

        self.station = BMCModel()
