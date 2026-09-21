from qtpy import QtWidgets, QtCore


class VLine(QtWidgets.QFrame):
    """
    Vertical line frame template.
    """

    def __init__(self) -> None:
        super(VLine, self).__init__(flags=QtCore.Qt.WindowFlags())
        self.setFrameShape(self.VLine | self.Sunken)


class HLine(QtWidgets.QFrame):
    """
    Horizontal line frame template.
    """

    def __init__(self) -> None:
        super(HLine, self).__init__(flags=QtCore.Qt.WindowFlags())
        self.setFrameShape(self.HLine | self.Sunken)
        self.setObjectName("line-horiz")
