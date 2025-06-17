from PySide6.QtWidgets import (QApplication,
                            QWidget, 
                            QMainWindow,
                            QHBoxLayout, 
                            QVBoxLayout,
                            QPushButton, 
                            QPlainTextEdit, 
                            QStackedLayout,
                            QComboBox,
                            QGridLayout,
                            QLabel
    )
import json
import os

from combo_box import ComboBox

from llm_utils import MODELS, generate_plan

UBUNTU_ORANGE = "#E95420"

class Interface(QMainWindow):
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LLM Planner")

        widget = QWidget()
        
        self.active_btn_ = None

        self.views_ = {"Edit task":QPlainTextEdit(""),
                    "View full prompt":QPlainTextEdit(""),
                    "View LLM response": QPlainTextEdit("")}

        self.current_model_ = None
        self.dropdown_widget_ = self.create_dropdown_group()
        self.main_view_widget_ = self.create_views()
        self.control_widget_ = self.create_controls()
        
        content_layout = QHBoxLayout()
        content_layout.addWidget(self.control_widget_)
        content_layout.addWidget(self.main_view_widget_)

        main_layout = QGridLayout()
        # Start row, start col, row span, col span
        main_layout.addWidget(self.dropdown_widget_, 0, 0, 1, 2)
        main_layout.addWidget(self.control_widget_, 1, 0)
        main_layout.addWidget(self.main_view_widget_, 1, 1)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)
        
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)

    def create_dropdown_group(self):
        dropdown_widget = QWidget()
        dropdown_widget_layout = QHBoxLayout()
        dropdown_widget.setLayout(dropdown_widget_layout)
        dropdown_widget_layout.setContentsMargins(0,0,0,0)
        dropdown_widget_layout.setSpacing(0)

        selected_model_label = QLabel("No model selected")

        for model in MODELS:
            dropdown = ComboBox(placeholderText=model)
            dropdown.activated.connect(lambda _, dropdown=dropdown, label=selected_model_label: self.switch_model(dropdown, label))
            dropdown.addItems(MODELS[model])
            dropdown_widget_layout.addWidget(dropdown)

        dropdown_widget_layout.addStretch()
        dropdown_widget_layout.addWidget(selected_model_label)

        return dropdown_widget

    def create_views(self):

        main_view_widget = QWidget()
        stack = QStackedLayout()
        main_view_widget.setLayout(stack)

        # Stack layout to switch between editors
        # See: https://www.tutorialspoint.com/pyqt/pyqt_qstackedlayout.htm
        
        for view_name in self.views_:
            editor = self.views_[view_name]
            editor.setProperty('code', 'true')
            stack.addWidget(editor)
            editor.setReadOnly(True)
        
        # Set the task view as default view and enable it
        self.views_["Edit task"].setReadOnly(False)
        
        return main_view_widget

    def create_controls(self):
        # Buttons to switch views
        control_widget = QWidget()
        control_widget_layout = QVBoxLayout()
        control_widget_layout.setSpacing(5)
        control_widget_layout.setContentsMargins(2,2,2,2)
        control_widget.setLayout(control_widget_layout)
        control_widget_layout.addStretch()

        buttons = {}
        for i, (label, _) in enumerate(self.views_.items()):
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, idx=i, b=btn: self.switch_view(idx, b))
            control_widget_layout.addWidget(btn)
            buttons[label] = btn
        
        init_button = QPushButton("Send a request to LLM")
        control_widget_layout.addWidget(init_button)
        init_button.clicked.connect(lambda _: generate_plan(self.views_["Edit task"].toPlainText(), self.current_model_))

        self.active_btn_:QPushButton = buttons["Edit task"]
        self.active_btn_.setStyleSheet(f"background-color: {UBUNTU_ORANGE};")
        
        return control_widget

    def switch_view(self, index: int, button: QPushButton):
        self.main_view_widget_.layout().setCurrentIndex(index)
        self.active_btn_.setStyleSheet("background-color: none;")
        button.setStyleSheet(f"background-color: {UBUNTU_ORANGE};")
        self.active_btn_ = button
    
    def switch_model(self, dropdown:QComboBox, label:QLabel):
        model = dropdown.currentText()
        self.current_model_ = model
        label.setText(f"Selected model: {model}")
    
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
