# Rev 0.6.8
# trackerZ – HistoryTab (Rev 0.6.8)
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
class HistoryTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("History (project/task/subtask updates) coming in M5–M6."))

    def load(self, project_id:int):
        pass


