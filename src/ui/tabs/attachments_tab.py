# Rev 0.4.1
# trackerZ – AttachmentsTab (Rev 0.4.1)
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
class AttachmentsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Attachments coming in M7."))

    def load(self, project_id:int):
        pass


