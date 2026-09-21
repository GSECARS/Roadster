from qtpy import QtWidgets

from typing import Optional


class PromptModel:
    def __init__(
        self, parent, msg_title: str, msg_text: str, user_prompt: Optional[bool] = False
    ):
        super(PromptModel, self).__init__()
        self.parent = parent
        self.msg_title = msg_title
        self.msg_text = msg_text
        self.user_prompt = user_prompt

        self._response = False

        self.get_msg_box()

    def get_msg_box(self):
        if self.user_prompt:
            msg_box = QtWidgets.QMessageBox.question(
                self.parent, self.msg_title, self.msg_text
            )

            if msg_box == QtWidgets.QMessageBox.Yes:
                self._response = True
            else:
                self._response = False
        else:
            QtWidgets.QMessageBox.warning(self.parent, self.msg_title, self.msg_text)

    @property
    def response(self):
        return self._response
