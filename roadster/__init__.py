import argparse
import os
import shutil
import sys
from importlib.metadata import version as pkg_version
from sys import platform

from roadster.controller import MainController


def _set_macos_dock_icon(icon_path: str) -> None:
    try:
        from AppKit import NSApplication, NSImage
        ns_app = NSApplication.sharedApplication()
        image = NSImage.alloc().initWithContentsOfFile_(icon_path)
        if image:
            ns_app.setApplicationIconImage_(image)
    except ImportError:
        pass


def main() -> None:
    """Main entry point for `roadster` console script."""
    parser = argparse.ArgumentParser("Roadster CLI")
    parser.add_argument("-m", "--make-icon", action="store_true", help="create desktop shortcut icon")
    parser.add_argument("-p", "--public", action="store_true", help="create shortcut on public desktop")

    args = parser.parse_args()

    _icons_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons")

    if args.make_icon or args.public:
        from pyshortcuts import make_shortcut
        bindir = "Scripts" if os.name == "nt" else "bin"
        script = os.path.join(sys.prefix, bindir, "roadster")
        iconfile = os.path.join(_icons_dir, "roadster.png")
        if os.name == "nt":
            ico = os.path.join(_icons_dir, "roadster.ico")
            if os.path.exists(ico):
                local_icon = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "roadster.ico")
                shutil.copy2(ico, local_icon)
                iconfile = local_icon
        make_shortcut(script, name="Roadster", icon=iconfile, terminal=False,
                      public=args.public, folder="GSEApps" if args.public else None)
        return

    if platform == "darwin":
        try:
            from Foundation import NSBundle
            info = NSBundle.mainBundle().infoDictionary()
            if info is not None:
                info["CFBundleName"] = "Roadster"
                info["CFBundleDisplayName"] = "Roadster"
        except ImportError:
            pass

    try:
        _version = pkg_version("roadster")
    except Exception:
        _version = ""

    from qtpy import QtGui
    controller = MainController()
    icon_path = os.path.join(_icons_dir, "roadster.png")
    controller._app.setWindowIcon(QtGui.QIcon(icon_path))
    if platform == "darwin":
        _set_macos_dock_icon(icon_path)
    controller.run(_version)


def main2() -> None:
    """Minimal test window to verify Qt is working."""
    from qtpy import QtWidgets
    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QWidget()
    win.setFixedSize(200, 200)
    win.setWindowTitle("Test")
    win.show()
    sys.exit(app.exec())
