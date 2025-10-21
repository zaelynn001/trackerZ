# Rev 0.6.8

# ui/window_mode.py
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QGuiApplication

def lock_maximized(win, *, lock_resize: bool = False):
    """
    Open the window maximized. If lock_resize=True, prevent user resizing
    by fixing the size to the available screen area (taskbar-safe).
    """
    screen = QGuiApplication.screenAt(win.frameGeometry().center()) or QGuiApplication.primaryScreen()
    rect: QRect = screen.availableGeometry()

    # Remove any fullscreen/frameless flags we might have experimented with
    win.setWindowFlag(Qt.FramelessWindowHint, False)
    win.setWindowFlag(Qt.WindowMaximizeButtonHint, True)

    if lock_resize:
        # Fix size to the available area so the user can't resize after maximize
        win.setMinimumSize(rect.size())
        win.setMaximumSize(rect.size())
    else:
        # Allow resizing after maximize
        win.setMinimumSize(0, 0)
        win.setMaximumSize(16777215, 16777215)

    win.showMaximized()


def lock_dialog_fixed(win, *, width_ratio=0.6, height_ratio=0.7):
    """
    For modal dialogs: keep them *not* maximized, but non-resizable and sized
    as a fraction of the current screen.
    """
    screen = QGuiApplication.screenAt(win.frameGeometry().center()) or QGuiApplication.primaryScreen()
    rect: QRect = screen.availableGeometry()
    w = int(rect.width() * width_ratio)
    h = int(rect.height() * height_ratio)
    win.setFixedSize(w, h)
    win.setWindowFlag(Qt.WindowMaximizeButtonHint, False)
