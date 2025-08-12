from PySide6.QtWidgets import QComboBox
                 
# Credit to: https://stackoverflow.com/questions/66898774/qcombobox-dropdown-not-proper-on-linux
class ComboBox(QComboBox):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # https://www.qtcentre.org/threads/25054-QcomboBox-hide-the-drop-down-arrow
        self.setStyleSheet("""
            QComboBox {background-color: #f0f0f0;border-radius: 0px;padding: 2px; border:1px solid darkgray}
            QComboBox::drop-down { border-width: 0px; }
            QComboBox::down-arrow { image: none; width: 0px; height: 0px; }
        """)
    
    def showPopup(self):
        super().showPopup()
        # Get the container holding the items
        container = self.view().parentWidget()
        # Get the local position (relative to the list itself) of 
        # the bottom left corner and convert to global screen position
        global_pos = self.mapToGlobal(self.rect().bottomLeft())
        # Move the container downwards (origin is top left)
        container.move(global_pos)