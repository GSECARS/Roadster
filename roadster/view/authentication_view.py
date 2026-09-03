from qtpy import QtWidgets, QtCore


class AuthenticationView(QtWidgets.QDialog):
    def __init__(self):
        super(AuthenticationView, self).__init__(
            flags=QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint
        )

        self.lbl_dialog = QtWidgets.QLabel()
        self.lbl_wrong_pwd = QtWidgets.QLabel()
        self.pwd_dialog = QtWidgets.QLineEdit()

        self.btn_authenticate = QtWidgets.QPushButton()
        self.btn_cancel = QtWidgets.QPushButton()

        self.init_dialog()

    def init_dialog(self) -> None:
        self.config_dialog()
        self.config_labels()
        self.config_buttons()
        self.config_line_edit()
        self.layout_authentication_view()

        # Set default focused widget
        # self.btn_authenticate.setFocus()

    def config_dialog(self) -> None:
        self.setWindowTitle("User Authentication")
        self.setFixedSize(200, 95)

    def config_labels(self) -> None:
        self.lbl_dialog.setText("Password")

    def config_buttons(self) -> None:
        """QPushButton configuration"""
        # Display text
        self.btn_authenticate.setText("Authenticate")
        self.btn_cancel.setText("Cancel")

        # Set size
        self.btn_authenticate.setFixedSize(105, 30)
        self.btn_cancel.setFixedSize(70, 30)

        # Connect signals/slots
        self.btn_cancel.clicked.connect(self.cancel_authentication)

    def config_line_edit(self) -> None:
        # Hide characters for password
        self.pwd_dialog.setEchoMode(QtWidgets.QLineEdit.Password)

        # Set alignments
        self.pwd_dialog.setAlignment(QtCore.Qt.AlignCenter)

        # Set placeholder
        self.pwd_dialog.setPlaceholderText("Password")

        # Set size
        self.pwd_dialog.setFixedHeight(25)

    def layout_authentication_view(self) -> None:
        """Layout configuration"""
        # Create layouts
        dialog_layout = QtWidgets.QVBoxLayout()
        password_layout = QtWidgets.QHBoxLayout()
        buttons_layout = QtWidgets.QHBoxLayout()

        # Configure layouts
        dialog_layout.setContentsMargins(10, 10, 10, 10)
        dialog_layout.setSpacing(0)
        password_layout.setContentsMargins(0, 0, 0, 0)
        password_layout.setSpacing(5)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(5)

        # Add widgets to the password layout
        password_layout.addWidget(self.lbl_dialog, alignment=QtCore.Qt.AlignLeft)
        password_layout.addWidget(self.pwd_dialog, alignment=QtCore.Qt.AlignCenter)

        # Add widgets to the buttons layout
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(self.btn_authenticate, alignment=QtCore.Qt.AlignCenter)
        buttons_layout.addWidget(self.btn_cancel, alignment=QtCore.Qt.AlignRight)

        # Add widgets/layouts to the main layout
        dialog_layout.addLayout(password_layout)
        dialog_layout.addWidget(self.lbl_wrong_pwd)
        dialog_layout.addLayout(buttons_layout)

        # Set layout and display
        self.setLayout(dialog_layout)

    def display(self) -> None:
        """Resets the authentication status and opens the dialog."""
        self.show()

    def cancel_authentication(self) -> None:
        """Cancels the authentication process and closes the dialog window."""
        self.close()
