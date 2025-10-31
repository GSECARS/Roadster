from roadster.model import MainModel
from roadster.view import MainView


class OptionsController:
    """Connects the OptionsModel with the application views."""

    def __init__(self, model: MainModel, view: MainView):
        self.model = model
        self.view = view
