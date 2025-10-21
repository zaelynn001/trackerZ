# Rev 0.6.8
# trackerZ – ExpensesTab (Rev 0.6.8)
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
class ExpensesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Expenses coming in M8."))

    def load(self, project_id:int):
        pass


