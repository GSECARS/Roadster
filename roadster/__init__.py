import argparse
import sys
from importlib.metadata import version as pkg_version

from roadster.controller import MainController


def main() -> None:
    """Main entry point for `roadster` console script."""
    parser = argparse.ArgumentParser("Roadster CLI")
    parser.add_argument("-m", "--make-icon", action="store_true", help="create desktop shortcut icon")
    parser.add_argument("-p", "--public", action="store_true", help="create shortcut on public desktop")

    args = parser.parse_args()

    if args.make_icon or args.public:
        # make_icon(public=args.public)
        pass
    else:
        try:
            _version = pkg_version("roadster")
        except Exception:
            _version = ""
        MainController().run(_version)


def main2() -> None:
    """Minimal test window to verify Qt is working."""
    from qtpy import QtWidgets
    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QWidget()
    win.setFixedSize(200, 200)
    win.setWindowTitle("Test")
    win.show()
    sys.exit(app.exec())
