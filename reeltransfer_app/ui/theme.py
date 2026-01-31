from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt


def dark_palette() -> QPalette:
    p = QPalette()

    p.setColor(QPalette.Window, QColor(24, 24, 28))
    p.setColor(QPalette.WindowText, Qt.white)
    p.setColor(QPalette.Base, QColor(20, 20, 24))
    p.setColor(QPalette.AlternateBase, QColor(30, 30, 36))
    p.setColor(QPalette.ToolTipBase, Qt.white)
    p.setColor(QPalette.ToolTipText, Qt.white)
    p.setColor(QPalette.Text, Qt.white)
    p.setColor(QPalette.Button, QColor(38, 38, 46))
    p.setColor(QPalette.ButtonText, Qt.white)
    p.setColor(QPalette.BrightText, Qt.red)
    p.setColor(QPalette.Highlight, QColor(84, 126, 255))
    p.setColor(QPalette.HighlightedText, Qt.black)

    return p


def dark_stylesheet() -> str:
    return """
    QWidget {
        color: #E8E8EE;
        font-size: 14px;
        font-family: "Segoe UI", "Inter", "Arial";
    }

    QMainWindow, QWidget#centralwidget {
        background-color: #18181C;
    }

    QLineEdit, QTextBrowser, QSpinBox {
        background-color: #141418;
        border: 1px solid #2B2B33;
        border-radius: 8px;
        padding: 6px 10px;
        selection-background-color: #547EFF;
    }

    QSpinBox {
        padding-right: 26px;
    }

    QLineEdit:focus, QTextBrowser:focus, QSpinBox:focus {
        border: 1px solid #547EFF;
    }

    QSpinBox::up-button, QSpinBox::down-button {
        subcontrol-origin: border;
        width: 18px;
        border: none;
        background: #1D1D24;
    }

    QSpinBox::up-button {
        subcontrol-position: top right;
        border-top-right-radius: 8px;
    }

    QSpinBox::down-button {
        subcontrol-position: bottom right;
        border-bottom-right-radius: 8px;
    }

    QSpinBox::up-button:hover, QSpinBox::down-button:hover {
        background: #2B2B35;
    }

    QSpinBox::up-arrow, QSpinBox::down-arrow {
        width: 10px;
        height: 10px;
        background: transparent;
    }

    QSpinBox::up-arrow {
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-bottom: 6px solid #C8C8D6;
    }

    QSpinBox::down-arrow {
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid #C8C8D6;
    }

    QPushButton {
        background-color: #2B2B35;
        border: 1px solid #3A3A46;
        border-radius: 10px;
        padding: 8px 14px;
        font-weight: 600;
    }

    QPushButton:hover {
        background-color: #353543;
    }

    QPushButton:pressed {
        background-color: #24242D;
    }

    QPushButton:disabled {
        background-color: #1F1F25;
        color: #777884;
        border-color: #2B2B33;
    }

    QCheckBox {
        spacing: 8px;
    }

    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 5px;
        border: 1px solid #3A3A46;
        background: #1A1A20;
    }

    QCheckBox::indicator:checked {
        background: #547EFF;
        border: 1px solid #547EFF;
    }

    QMenuBar {
        background-color: #18181C;
        border-bottom: 1px solid #2B2B33;
    }

    QMenuBar::item:selected {
        background-color: #2B2B35;
        border-radius: 6px;
    }

    QMenu {
        background-color: #1B1B22;
        border: 1px solid #2B2B33;
    }

    QMenu::item:selected {
        background-color: #2B2B35;
    }

    QStatusBar {
        background: #18181C;
        color: #B8B8C6;
        border-top: 1px solid #2B2B33;
    }

    QTextBrowser {
        border-radius: 10px;
        line-height: 1.4;
    }

    QScrollBar:vertical {
        background: #18181C;
        width: 12px;
        margin: 6px 0 6px 0;
    }

    QScrollBar::handle:vertical {
        background: #2B2B35;
        min-height: 24px;
        border-radius: 6px;
    }

    QScrollBar::handle:vertical:hover {
        background: #363644;
    }

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
        subcontrol-origin: margin;
    }
    """
