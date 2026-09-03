import numpy as np
import pyqtgraph as pg
from qtpy.QtCore import QObject, Signal, Qt
from qtpy.QtGui import QMouseEvent

pg.setConfigOption("antialias", True)
pg.setConfigOption("useOpenGL", False)
pg.setConfigOption("leftButtonPan", False)


class LinePlotWidget(QObject):
    mouse_moved: Signal(float, float)
    mouse_clicked: Signal(float, float)

    _plot_item: pg.PlotItem
    _plot_data_item: pg.PlotDataItem
    _view_box: pg.ViewBox

    def __init__(self, gfx_layout: pg.GraphicsLayoutWidget) -> None:
        super(LinePlotWidget, self).__init__()

        self._gfx_layout = gfx_layout

        self._main_pen = pg.mkPen(width=2)

        self._configure_plot_item()
        self._configure_view_box()
        self._configure_gfx()
        self._configure_plot_data_items()

    def _configure_gfx(self) -> None:
        self._gfx_layout.scene().sigMouseMoved.connect(self._mouse_move_event)
        self._gfx_layout.setBackground("#23272a")

    def _configure_plot_item(self) -> None:
        self._plot_item = self._gfx_layout.addPlot()
        self._plot_item.enableAutoRange(False)
        self._plot_item.buttonsHidden = True

    # TODO: Remove random data from the main plot.
    def _configure_plot_data_items(self) -> None:
        self._plot_data_item = pg.PlotDataItem(
            x=np.random.rand(1, 10).tolist()[0],
            y=np.random.rand(1, 10).tolist()[0],
            pen=self._main_pen,
        )
        self._plot_item.addItem(self._plot_data_item)

    # TODO: (Set axis limits)?
    def _configure_view_box(self) -> None:
        self._view_box = self._plot_item.vb
        # self._view_box.state["defaultPadding"] = 0.1
        self._view_box.setMouseMode(self._view_box.RectMode)
        self._view_box.mouseClickEvent = self._mouse_click_event
        self._view_box.mouseDoubleClickEvent = self._mouse_double_click_event

    def _mouse_move_event(self, event: QMouseEvent) -> None:
        """
        Handles mouse move events.
        :emit: The current coordinates of the cursor relative to the _data_plot_item.
        """
        position = self._plot_data_item.mapFromScene(event)
        self.mouse_moved.emit(position.x(), position.y())

    def _mouse_click_event(self, event: QMouseEvent) -> None:
        """
        Handles mouse click events.
        :emit: The left click coordinates relative to the _data_plot_item.
        """
        # Left mouse click
        if event.button() == Qt.LeftButton:
            position = self._plot_data_item.mapFromScene(
                2 * event.pos() - self._view_box.mapFromScene(event.pos())
            )
            self.mouse_clicked.emit(position.x(), position.y())

    # TODO: Modify double click method for roaster. (Set axis limits)
    def _mouse_double_click_event(self, event: QMouseEvent) -> None:
        if event.button() == Qt.RightButton:

            x_range = list(self._plot_data_item.dataBounds(0))
            y_range = list(self._plot_data_item.dataBounds(1))

            # self._view_box.setLimits(xMin=x_range[0], xMax=x_range[1], yMin=y_range[0], yMax=y_range[1])
            self._view_box.setRange(xRange=x_range, yRange=y_range, padding=0.5)
