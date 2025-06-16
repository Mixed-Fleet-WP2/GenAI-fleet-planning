from PySide6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QHBoxLayout, QVBoxLayout,
    QPushButton, QPlainTextEdit, QStackedLayout
)
from PySide6.QtGui import QFont
import json
import os

UBUNTU_ORANGE = "#E95420"

class Interface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LLM Planner")

        widget = QWidget()
        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        views_layout = QVBoxLayout()
        views_layout.setContentsMargins(0, 0, 0, 0)
        views_layout.setSpacing(0)

        code_font = QFont("Ubuntu Mono", 12, QFont.DemiBold)
        main_font = QFont("Ubuntu", 12, QFont.DemiBold)

        self.editors = {"Task":QPlainTextEdit("a"),
                        "View full prompt":QPlainTextEdit("b"),
                        "LLM response": QPlainTextEdit("c")}
            
        # Stack layout to switch between editors
        self.stack = QStackedLayout()
        for view_name in self.editors:
            editor = self.editors[view_name]
            self.stack.addWidget(editor)
            editor.setReadOnly(True)

        # Buttons to switch views
        self.buttons = {}
        for i, (label, editor) in enumerate(self.editors.items()):
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, idx=i, b=btn: self.switch_view(idx, b))
            views_layout.addWidget(btn)
            self.buttons[label] = btn

        self.active_btn = self.buttons["Task"]
        self.active_btn.setStyleSheet(f"background-color: {UBUNTU_ORANGE};")

        views_layout.addStretch()
        views_layout.addWidget(QPushButton("Send a request to LLM"))

        layout.addLayout(views_layout)

        content_container = QWidget()
        content_container.setLayout(self.stack)
        layout.addWidget(content_container)

        widget.setLayout(layout)
        widget.setFont(main_font)
        self.setCentralWidget(widget)

    def switch_view(self, index: int, button: QPushButton):
        self.stack.setCurrentIndex(index)
        self.active_btn.setStyleSheet("background-color: none;")
        button.setStyleSheet(f"background-color: {UBUNTU_ORANGE};")
        self.active_btn = button


if __name__ == "__main__":
    app = QApplication([])

    interface_path = os.path.abspath(os.path.dirname(__file__))
    stylesheet_path = os.path.join(interface_path, "style.qss")
    with open(stylesheet_path, "r") as f:
        _style = f.read()
        app.setStyleSheet(_style)

    window = Interface()
    window.resize(600, 400)
    window.show()
    app.exec()
