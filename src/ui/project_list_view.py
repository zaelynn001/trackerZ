# Rev 0.6.5

# trackerZ – ProjectListView (Rev 0.6.5)
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableView

class ProjectListView(QWidget):
    projectActivated = Signal(int)

    def __init__(self, model, proxy=None, parent=None):
        super().__init__(parent)
        self._model = model
        self._proxy = proxy

        self.table = QTableView(self)
        self.table.setModel(self._proxy or self._model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.doubleClicked.connect(self._on_row_activated)

        lay = QVBoxLayout(self)
        lay.addWidget(self.table)

    def _on_row_activated(self, index):
        if not index.isValid():
            return
        src = self._proxy.mapToSource(index) if self._proxy else index
        # Prefer UserRole (robust even if columns move/hide)
        pid = self._model.data(src, Qt.UserRole)
        if pid is None:
            pid = self._model.data(self._model.index(src.row(), 0))  # fallback to col 0 text
        try:
            self.projectActivated.emit(int(pid))
        except Exception:
            pass

