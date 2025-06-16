from PySide6.QtWidgets import QApplication, QWidget, QMainWindow, QHBoxLayout, QVBoxLayout, QPushButton, QPlainTextEdit
from PySide6.QtGui import QFont
import json
import os

UBUNTU_ORANGE = "#E95420"

class Interface(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("LLM Planner")

        self.current_task = "a"
        self.complete_prompt_ = "b"
        self.llm_response_ = "c"

        widget = QWidget()
        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        views_layout = QVBoxLayout()
        views_layout.setContentsMargins(0, 0, 0, 0)
        views_layout.setSpacing(0)
    
        code_font = QFont("Ubuntu Mono", 12, QFont.DemiBold)
        main_font = QFont("Ubuntu", 12, QFont.DemiBold)

        content = {"name": "Elmer","age": 29,"email": "elmer@example.com", "is_active": True, "roles": ["admin", "user"]}
        formatted = json.dumps(content, indent=2)
        self.main_content_ = QPlainTextEdit(formatted)
        self.main_content_.setFont(code_font)

        self.main_content_layout_ = QVBoxLayout()
        self.main_content_layout_.addWidget(self.main_content_)

        view_btns = [(QPushButton("Task"), self.current_task),
                    (QPushButton("View full prompt"), self.complete_prompt_),
                    (QPushButton("LLM response"), self.llm_response_)]
        
        for button, content in view_btns:
            # This has to be done this way because button and btn_name are late-bound
            # and when lambda is executed, all the instances get the values
            # of the last iteration
            button.clicked.connect(lambda _, b=button, c=content: self.handle_view_change(b, c))
            views_layout.addWidget(button)
        
        # Works because python dicts are ordered
        self.active_btn = view_btns[0][0]
        self.active_btn.setStyleSheet(f"background-color: {UBUNTU_ORANGE};")

        layout.addLayout(views_layout)

        views_layout.addStretch()
        views_layout.addWidget(QPushButton("Send a request to LLM"))

        layout.addLayout(self.main_content_layout_)
        widget.setLayout(layout)
        widget.setFont(main_font)

        # Set the central widget of the Window.
        self.setCentralWidget(widget)  # Use the instance, not the class

    def handle_view_change(self, button:QPushButton, content:str):
        self.active_btn.setStyleSheet("background-color: none;")
        self.main_content_.setPlainText(content)
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
    window.resize(600,400)
    window.show()
    app.exec()
