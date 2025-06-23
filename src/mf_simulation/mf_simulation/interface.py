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
                            QLabel,
                            QTextEdit
    )


from PySide6.QtCore import QTimer, QThread, QRunnable, QThreadPool, Slot, Signal, QObject, Qt

import os

from combo_box import ComboBox
from llm_utils import MODELS, PromptGenerator

# Save this for the gu

UBUNTU_ORANGE = "#E95420"

from enum import Enum

class WorkerSignals(QObject):
    result_signal = Signal(tuple)

# https://www.pythonguis.com/tutorials/multithreading-pyside6-applications-qthreadpool/
class Worker(QRunnable):
   
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    # Override the run method
    # https://www.pythonguis.com/faq/what-does-slot-do/
    # Solot decorator is only necessary with threads
    @Slot()
    def run(self):
        result = self.fn(*self.args, **self.kwargs)
        self.signals.result_signal.emit(result)


class Formats(Enum):
    JSON = "json"
    YAML = "yaml"

class Interface(QMainWindow):
    
    def __init__(self):
        super().__init__()

        self.threadpool = QThreadPool()
        self.prompt_generator_ = PromptGenerator()

        self.setWindowTitle("LLM Planner v3")

        widget = QWidget()
        
        self.active_btn_ = None

        self.views_ = {"Edit task":QTextEdit(""),
                    "View full prompt":QTextEdit(""),
                    "View LLM response": QTextEdit("")}
        
        self.current_model_ = "gpt-4o-mini"

        self.current_format_ = Formats.JSON
        self.plan_ = ""
        
        self.status_text_ = QLabel("")
        self.status_text_.setProperty("class", "status-text")
        
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
            dropdown.activated.connect(lambda _,
                dropdown=dropdown,
                label=selected_model_label: self.switch_model(dropdown, label))
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
            # editor.setLineWrapMode(QTextEdit.WidgetWidth)
            # editor.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            # editor.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
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
        control_widget_layout.setSpacing(0)
        control_widget_layout.setContentsMargins(0,0,0,0)
        control_widget.setLayout(control_widget_layout)
        
        buttons = {}
        for i, (label, _) in enumerate(self.views_.items()):
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, idx=i, b=btn: self.switch_view(idx, b))
            control_widget_layout.addWidget(btn)
            buttons[label] = btn
            btn.setProperty("class", "view-control")
        
        control_widget_layout.addStretch()

        control_widget_layout.addWidget(self.status_text_)

        format_mode_button = QPushButton(f"Toggle format (current: {self.current_format_.value})")
        format_mode_button.clicked.connect(lambda _, btn=format_mode_button: self.switch_format_(btn))
        control_widget_layout.addWidget(format_mode_button)

        init_button = QPushButton("Send a request to LLM")
        control_widget_layout.addWidget(init_button)
        init_button.clicked.connect(self.generate_ai_plan)

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
    
    def generate_ai_plan(self):

        self.status_text_.setText("Generating...")

        worker = Worker(self.prompt_generator_.generate_plan,
            self.views_["Edit task"].toPlainText(),
            self.current_model_,
            self.current_format_.value)
        
        worker.signals.result_signal.connect(self.update_gui)

        self.threadpool.start(worker)
    
    def update_gui(self, result):
        prompt, plan = result
        self.plan_ = plan

        # Reformat for GUI only
        print(self.current_format_)
        plan_formatted = self.prompt_generator_.return_formatted(self.current_format_.value)

        self.views_["View full prompt"].setPlainText(prompt)
        self.views_["View LLM response"].setPlainText(plan_formatted)
        
        # Make the status text dissappear
        self.status_text_.setText("Done!")
        timer = QTimer(self)
        timer.timeout.connect(lambda label=self.status_text_: label.setText(""))
        timer.start(2000)

    def switch_format_(self, btn: QPushButton):
        self.current_format_ = (Formats.JSON
                     if self.current_format_ is Formats.YAML
                     else Formats.YAML)
        
        btn.setText(f"Toggle format (current: {self.current_format_.value})")
        plan = self.prompt_generator_.return_formatted(
            self.current_format_.value)
        
        self.views_["View LLM response"].setPlainText(plan)

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
