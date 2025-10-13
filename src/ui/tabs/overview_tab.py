# Rev 0.5.1
# trackerZ – OverviewTab (Rev 0.5.1)
from PySide6.QtWidgets import QWidget, QLabel, QGridLayout

class OverviewTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._t = QLabel("–")
        self._st = QLabel("–")
        self._att = QLabel("–")
        self._exp = QLabel("–")
        g = QGridLayout(self)
        g.addWidget(QLabel("Tasks"), 0,0); g.addWidget(self._t, 0,1)
        g.addWidget(QLabel("Subtasks"), 1,0); g.addWidget(self._st, 1,1)
        g.addWidget(QLabel("Attachments"), 2,0); g.addWidget(self._att, 2,1)
        g.addWidget(QLabel("Expenses"), 3,0); g.addWidget(self._exp, 3,1)

    def set_counts(self, counts:dict):
        self._t.setText(str(counts.get("tasks_total", 0)))
        self._st.setText(str(counts.get("subtasks_total", 0)))
        self._att.setText(str(counts.get("attachments_total", 0)))
        self._exp.setText(str(counts.get("expenses_total", 0)))


