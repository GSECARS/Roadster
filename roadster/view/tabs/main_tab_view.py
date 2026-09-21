from qtpy import QtWidgets

from roadster.view.tabs.scanning_tab import ScanningTab


class MainTabView(QtWidgets.QTabWidget):
    def __init__(self):
        super(MainTabView, self).__init__()

        self.scanning = ScanningTab()

        self.add_tabs()

    def add_tabs(self):
        self.addTab(self.scanning, "Scanning")
