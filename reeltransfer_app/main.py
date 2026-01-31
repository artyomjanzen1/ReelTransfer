import sys
from pathlib import Path

from dotenv import load_dotenv
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from reeltransfer_app.ui.main_window import MainWindow
from reeltransfer_app.ui.theme import dark_palette, dark_stylesheet


APP_NAME = "ReelTransfer"


def resource_path(*parts: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base.joinpath(*parts)


def main() -> int:
    load_dotenv()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setPalette(dark_palette())
    app.setStyleSheet(dark_stylesheet())

    icon_path = resource_path("assets", "reeltransfer.png")
    if icon_path.exists():
        icon = QIcon(str(icon_path))
        if not icon.isNull():
            app.setWindowIcon(icon)

    win = MainWindow(app)
    if icon_path.exists():
        win.setWindowIcon(QIcon(str(icon_path)))

    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
