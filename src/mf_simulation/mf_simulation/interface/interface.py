import sys

from PySide6.QtWidgets import (QApplication,
                            QWidget, 
                            QMainWindow,
                            QHBoxLayout, 
                            QVBoxLayout,
                            QPushButton, 
                            QStackedLayout,
                            QComboBox,
                            QGridLayout,
                            QLabel,
                            QTextEdit,
                            QPlainTextEdit,
                            QLayout
    )


from PySide6.QtCore import QTimer, QRunnable, QThreadPool, Slot, Signal, QObject, SignalInstance

import os
import signal

from enum import Enum
from mf_simulation.interface.combo_box import ComboBox
from mf_simulation.interface.llm_utils import PromptGenerator, Plan, GPTModel, ClaudeModel, LLamaModel, MODELS

from mf_simulation.interface.controller_v2 import Controller
from typing import cast



# Save this for the gu

UBUNTU_ORANGE = "#E95420"

from enum import Enum

class WorkerSignals(QObject):
    result_signal = Signal(tuple)
    error = Signal(tuple)
    feedback = Signal(str)

# https://www.pythonguis.com/tutorials/multithreading-pyside6-applications-qthreadpool/
class Worker(QRunnable):
   
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add a callback to the kwargs that is passed
        # to the function that runs in the worker thread
        feedback_signal: SignalInstance = self.signals.feedback
        self.kwargs['feedback_signal'] = feedback_signal

    # Override the run method
    # https://www.pythonguis.com/faq/what-does-slot-do/
    # Slot decorator is only necessary with threads
    @Slot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.result_signal.emit(result)
        except:
            value = cast(BaseException, sys.exc_info()[1])
            self.signals.error.emit(value)

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
        
        self.views_ = {"Edit task":QTextEdit(""),
                    "View full prompt":QTextEdit(""),
                    "View LLM response": QTextEdit("")}
        
        self.current_model_: GPTModel | ClaudeModel | LLamaModel = ClaudeModel.CLAUDE_3_7_SONNET

        self.current_format_ = Formats.JSON
        self.plan_: None | Plan = None
    
        self.dropdown_widget_ = self.create_dropdown_group()
        self.main_view_widget_ = self.create_views()
        self.control_widget_, self.active_btn_ = self.create_controls()
        self.__feedback_widget, self.feedback_area = self.create_feedback_section()

        main_layout = QGridLayout()
        # Start row, start col, row span, col span
        main_layout.addWidget(self.dropdown_widget_, 0, 0, 1, 2)
        main_layout.addWidget(self.control_widget_, 1, 0)
        main_layout.addWidget(self.main_view_widget_, 1, 1)
        main_layout.addWidget(self.__feedback_widget, 2, 0, 1, 2)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)

        main_layout.setRowStretch(1, 70)
        main_layout.setRowStretch(2, 20)

        
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)

    def create_dropdown_group(self):
        dropdown_widget = QWidget()
        dropdown_widget_layout = QHBoxLayout()
        dropdown_widget.setLayout(dropdown_widget_layout)
        dropdown_widget_layout.setContentsMargins(0,0,0,0)
        dropdown_widget_layout.setSpacing(0)

        selected_model_label = QLabel(f"Current model: {self.current_model_.plain_name}")
        
        for provider in MODELS:
            dropdown = ComboBox(placeholderText=provider)
            dropdown.activated.connect(lambda _,
                dropdown=dropdown,
                label=selected_model_label: self.switch_model(dropdown, label))
            provider_models = MODELS[provider]

            for model in provider_models:
                dropdown.addItem(model.plain_name, model)

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
            stack.addWidget(editor)
            editor.setReadOnly(True)
        
        # Set the task view as default view and enable it
        self.views_["Edit task"].setReadOnly(False)
        
        return main_view_widget

    def create_feedback_section(self):
        feedback_widget = QWidget()
        feedback_widget_layout = QVBoxLayout()
        feedback_widget.setLayout(feedback_widget_layout)

        feedback_label = QLabel("Status")
        feedback_section = QTextEdit()
        feedback_section.setReadOnly(True)

        feedback_widget_layout.addWidget(feedback_label)
        feedback_widget_layout.addWidget(feedback_section)

        return feedback_widget, feedback_section

    def create_controls(self):
        # Buttons to switch views
        control_widget = QWidget()
        control_widget_layout = QVBoxLayout()
        control_widget_layout.setSpacing(0)
        control_widget_layout.setContentsMargins(0,0,0,0)
        control_widget.setLayout(control_widget_layout)
        
        buttons: dict[str, QPushButton] = {}
        for i, (label, _) in enumerate(self.views_.items()):
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, idx=i, b=btn: self.switch_view(idx, b))
            control_widget_layout.addWidget(btn)
            buttons[label] = btn
            btn.setProperty("class", "view-control")
        
        control_widget_layout.addStretch()

        format_mode_button = QPushButton(f"Toggle format (current: {self.current_format_.value})")
        format_mode_button.clicked.connect(lambda _, btn=format_mode_button: self.switch_format_(btn))
        control_widget_layout.addWidget(format_mode_button)

        init_button = QPushButton("Send a request to LLM")
        control_widget_layout.addWidget(init_button)
        init_button.clicked.connect(self.generate_ai_plan)

        execute_button = QPushButton("Execute plan")
        control_widget_layout.addWidget(execute_button)
        execute_button.clicked.connect(self.execute_plan_)

        active_btn: QPushButton = buttons["Edit task"]

        active_btn.setStyleSheet(f"background-color: {UBUNTU_ORANGE};")
        
        return control_widget, active_btn

    def switch_view(self, index: int, button: QPushButton):
        
        stack_layout: QLayout| None = self.main_view_widget_.layout()
        if not stack_layout or not isinstance(stack_layout, QStackedLayout):
            return

        stack_layout.setCurrentIndex(index)
        
        self.active_btn_.setStyleSheet("background-color: none;")
        button.setStyleSheet(f"background-color: {UBUNTU_ORANGE};")
        self.active_btn_ = button
    
    def switch_model(self, dropdown:QComboBox, label:QLabel):
        model_name = dropdown.currentText()
        model = dropdown.currentData()
        self.current_model_ : GPTModel | ClaudeModel | LLamaModel = model
        label.setText(f"Selected model: {model_name}")
    
    def generate_ai_plan(self):

        self.write_feedback("Generating...")

        worker = Worker(self.prompt_generator_.generate_plan,
            self.views_["Edit task"].toPlainText(),
            self.current_model_,)
        
        worker.signals.result_signal.connect(self.update_gui)
        worker.signals.error.connect(lambda exception: self.write_feedback(str(exception)))

        self.threadpool.start(worker)
    
    def update_gui(self, result: tuple[str, Plan]):
        prompt, plan = result
        self.plan_ = plan

        self.views_["View full prompt"].setPlainText(prompt)
        self.views_["View LLM response"].setPlainText(
            self.plan_.to_format(self.current_format_.value))
               
        # Make the status text dissappear
        self.feedback_area.append("Done")
    
    def write_feedback(self, text:str = "test"):
        #https://stackoverflow.com/questions/13559990/how-to-append-text-to-qplaintextedit-without-adding-newline-and-keep-scroll-at
        self.feedback_area.append(text)

    def switch_format_(self, btn: QPushButton):
        self.current_format_ = (Formats.JSON
                     if self.current_format_ == Formats.YAML
                     else Formats.YAML)
        
        btn.setText(f"Toggle format (current: {self.current_format_.value})")

        if not self.plan_:
            return
        
        self.views_["View LLM response"].setPlainText(
            self.plan_.to_format(self.current_format_.value))
    
    def plan_callback(self):
        print("DONE")

    def execute_plan_(self):
        
        # Prevent executing if user presses execute without plan
        if not self.plan_:
            return

        worker = Worker(Controller().run_plan, self.plan_)
        
        worker.signals.feedback.connect(self.write_feedback)
        worker.signals.result_signal.connect(self.write_feedback)
        worker.signals.error.connect(lambda exception: self.write_feedback(str(exception)))

        self.threadpool.start(worker)


def main(args=None):
    
    app = QApplication([])

    # The event loop blocks regular KeyboardInterrupts so signals are used instead
    #https://stackoverflow.com/questions/4938723/what-is-the-correct-way-to-make-my-pyqt-application-quit-when-killed-from-the-co

    # SIG_DFL means that kernel handles the signal
    # https://stackoverflow.com/questions/33922223/what-exactly-sig-dfl-do
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    interface_path = os.path.abspath(os.path.dirname(__file__))
    stylesheet_path = os.path.join(interface_path, "style.qss")
    with open(stylesheet_path, "r") as f:
        _style = f.read()
        app.setStyleSheet(_style)

    window = Interface()
    window.resize(700, 600)
    window.show()
    app.exec()

    

if __name__ == "__main__":
    main()


    
