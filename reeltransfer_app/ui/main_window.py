from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QProcess
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLabel, QMessageBox,
    QLineEdit, QCheckBox, QTextBrowser, QStatusBar, QSpinBox
)

from reeltransfer_app.core.transfer import (
    build_plan,
    is_windows,
    find_duplicates,
    find_duplicates_for_files,
    apply_duplicate_renames,
)


APP_NAME = "ReelTransfer"
APP_VERSION = "1.1.0"


class MainWindow(QMainWindow):
    def __init__(self, app) -> None:
        super().__init__()
        self.app = app

        self.setWindowTitle(f"{APP_NAME} — {APP_VERSION}")
        self.resize(980, 640)

        self._process: Optional[QProcess] = None
        self._duplicate_action: Optional[str] = None
        self._duplicate_pairs: list[tuple[Path, Path]] = []
        self._source_files: list[Path] = []

        # Menu
        help_menu = self.menuBar().addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        # Source / Destination
        row1 = QHBoxLayout()
        layout.addLayout(row1)
        row1.addWidget(QLabel("Source:"))
        self.src_edit = QLineEdit()
        self.src_edit.setPlaceholderText("Select source folder or file(s) (local or network path)")
        self.btn_src = QPushButton("Browse…")
        self.btn_src_files = QPushButton("Browse Files…")
        row1.addWidget(self.src_edit, 1)
        row1.addWidget(self.btn_src)
        row1.addWidget(self.btn_src_files)

        row2 = QHBoxLayout()
        layout.addLayout(row2)
        row2.addWidget(QLabel("Destination:"))
        self.dst_edit = QLineEdit()
        self.dst_edit.setPlaceholderText("Select destination folder (local or network path)")
        self.btn_dst = QPushButton("Browse…")
        row2.addWidget(self.dst_edit, 1)
        row2.addWidget(self.btn_dst)

        # Options
        opts = QHBoxLayout()
        layout.addLayout(opts)
        self.chk_subdirs = QCheckBox("Include subfolders (/E)")
        self.chk_subdirs.setChecked(True)
        self.chk_move = QCheckBox("Move files (delete source) (/MOVE)")
        self.chk_move.setChecked(True)
        self.chk_mirror = QCheckBox("Mirror (/MIR) — deletes extra dest files")
        self.chk_mirror.setChecked(False)
        opts.addWidget(self.chk_subdirs)
        opts.addWidget(self.chk_move)
        opts.addWidget(self.chk_mirror)
        opts.addStretch(1)

        dupes = QHBoxLayout()
        layout.addLayout(dupes)
        self.chk_check_dupes = QCheckBox("Check for duplicates before transfer")
        self.chk_check_dupes.setChecked(True)
        dupes.addWidget(self.chk_check_dupes)
        dupes.addStretch(1)

        # Robocopy tuning
        tuning = QHBoxLayout()
        layout.addLayout(tuning)
        tuning.addWidget(QLabel("Retries (/R):"))
        self.spin_retries = QSpinBox()
        self.spin_retries.setRange(0, 100)
        self.spin_retries.setValue(1)
        tuning.addWidget(self.spin_retries)

        tuning.addWidget(QLabel("Wait sec (/W):"))
        self.spin_wait = QSpinBox()
        self.spin_wait.setRange(0, 300)
        self.spin_wait.setValue(1)
        tuning.addWidget(self.spin_wait)

        tuning.addWidget(QLabel("Threads (/MT):"))
        self.spin_threads = QSpinBox()
        self.spin_threads.setRange(0, 128)
        self.spin_threads.setValue(4)
        tuning.addWidget(self.spin_threads)
        tuning.addStretch(1)

        # Actions
        actions = QHBoxLayout()
        layout.addLayout(actions)
        self.btn_preview = QPushButton("Preview Command")
        self.btn_start = QPushButton("Start Transfer")
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setEnabled(False)
        actions.addWidget(self.btn_preview)
        actions.addWidget(self.btn_start)
        actions.addWidget(self.btn_stop)
        actions.addStretch(1)

        # Log output
        self.log = QTextBrowser()
        self.log.setOpenExternalLinks(True)
        self.log.setPlaceholderText("Robocopy output will appear here…")
        layout.addWidget(self.log, 1)

        # Status bar
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

        # Signals
        self.btn_src.clicked.connect(self._pick_src)
        self.btn_src_files.clicked.connect(self._pick_src_files)
        self.btn_dst.clicked.connect(self._pick_dst)
        self.btn_preview.clicked.connect(self._preview)
        self.btn_start.clicked.connect(self._start)
        self.btn_stop.clicked.connect(self._stop)
        self.chk_mirror.toggled.connect(self._mirror_toggled)
        self.src_edit.textEdited.connect(self._src_text_edited)

    def _show_about(self) -> None:
        QMessageBox.information(
            self,
            "About",
            f"<b>{APP_NAME}</b> v{APP_VERSION}<br>" 
            "Move media with Robocopy (local or network).",
        )

    def _pick_src(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select source folder", str(Path.home()))
        if folder:
            self.src_edit.setText(folder)
            self._source_files = []

    def _pick_src_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select source file(s)",
            str(Path.home()),
            "Media Files (*.mov *.mp4 *.mkv *.avi *.mp3 *.wav *.flac *.jpg *.jpeg *.png *.tif *.tiff *.bmp *.gif *.webp);;All Files (*.*)",
        )
        if files:
            paths = [Path(p) for p in files]
            self._source_files = paths
            parent = paths[0].parent
            self.src_edit.setText(f"{parent}  ({len(paths)} file(s))")

    def _src_text_edited(self) -> None:
        if self._source_files:
            self._source_files = []

    def _pick_dst(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select destination folder", str(Path.home()))
        if folder:
            self.dst_edit.setText(folder)

    def _mirror_toggled(self, checked: bool) -> None:
        if checked:
            QMessageBox.warning(
                self,
                "Mirror mode",
                "Mirror will delete destination files not present in source.",
            )

    def _preview(self) -> None:
        plan = self._build_plan(for_execution=False)
        if not plan:
            return
        self.log.append(f"<b>Command:</b> {plan.command_string()}")
        self.statusBar().showMessage("Preview generated", 3000)

    def _start(self) -> None:
        if not is_windows():
            QMessageBox.critical(self, "Unsupported", "Robocopy is Windows-only.")
            return

        plan = self._build_plan(for_execution=True)
        if not plan:
            return

        if self._process and self._process.state() != QProcess.NotRunning:
            QMessageBox.information(self, "Busy", "A transfer is already running.")
            return

        self.log.append(f"<b>Starting:</b> {plan.command_string()}")

        proc = QProcess(self)
        proc.setProgram(plan.command()[0])
        proc.setArguments(plan.command()[1:])
        proc.setProcessChannelMode(QProcess.MergedChannels)

        proc.readyReadStandardOutput.connect(lambda: self._read_output(proc))
        proc.finished.connect(self._on_finished)
        proc.started.connect(lambda: self._set_running(True))

        proc.start()
        self._process = proc

    def _stop(self) -> None:
        if not self._process:
            return
        if self._process.state() != QProcess.NotRunning:
            self._process.kill()
            self.statusBar().showMessage("Transfer stopped", 4000)

    def _read_output(self, proc: QProcess) -> None:
        data = proc.readAllStandardOutput().data().decode(errors="ignore")
        if data:
            self.log.append(data.replace("\n", "<br>"))

    def _on_finished(self, exit_code: int, _status) -> None:
        self._set_running(False)

        # Robocopy exit codes: 0-7 are success/warnings, >=8 is failure
        if exit_code >= 8:
            self.statusBar().showMessage(f"Transfer failed (code {exit_code})", 8000)
            QMessageBox.warning(self, "Transfer failed", f"Robocopy failed with code {exit_code}.")
            return
        else:
            self.statusBar().showMessage(f"Transfer complete (code {exit_code})", 6000)

        if self._duplicate_action == "rename" and self._duplicate_pairs:
            count, errors = apply_duplicate_renames(
                self._duplicate_pairs,
                move_files=self.chk_move.isChecked(),
            )
            if errors:
                preview = "\n".join(errors[:10])
                QMessageBox.warning(
                    self,
                    "Auto-rename completed (with issues)",
                    f"Renamed: {count}\n\nIssues:\n{preview}",
                )
            else:
                QMessageBox.information(self, "Auto-rename completed", f"Renamed: {count}")

    def _set_running(self, running: bool) -> None:
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)
        self.btn_preview.setEnabled(not running)

    def _choose_duplicate_action(
        self,
        src: Path,
        dst: Path,
        files: Optional[list[Path]] = None,
    ) -> Optional[str]:
        if not self.chk_check_dupes.isChecked():
            return "ask"

        if files:
            count, sample, pairs = find_duplicates_for_files(
                files,
                dst,
                sample_limit=10,
                return_pairs=True,
            )
        else:
            count, sample, pairs = find_duplicates(
                src,
                dst,
                include_subdirs=self.chk_subdirs.isChecked(),
                sample_limit=10,
                return_pairs=True,
            )
        if count == 0:
            self._duplicate_pairs = []
            return "ask"

        preview = "\n".join(str(p) for p in sample)
        if count > len(sample):
            preview += f"\n...and {count - len(sample)} more"

        msg = (
            f"Found {count} duplicate file(s) in destination.\n\n"
            f"Sample:\n{preview}\n\n"
            "Choose how to handle duplicates."
        )

        box = QMessageBox(self)
        box.setWindowTitle("Duplicates Found")
        box.setText(msg)
        btn_skip = box.addButton("Skip existing", QMessageBox.AcceptRole)
        btn_overwrite = box.addButton("Overwrite existing", QMessageBox.DestructiveRole)
        btn_rename = box.addButton("Auto-rename duplicates", QMessageBox.ActionRole)
        btn_cancel = box.addButton("Cancel", QMessageBox.RejectRole)
        box.exec()

        clicked = box.clickedButton()
        if clicked == btn_skip:
            self._duplicate_pairs = []
            return "skip"
        if clicked == btn_overwrite:
            self._duplicate_pairs = []
            return "overwrite"
        if clicked == btn_rename:
            self._duplicate_pairs = pairs
            return "rename"
        if clicked == btn_cancel:
            self._duplicate_pairs = []
            return None
        return None

    def _build_plan(self, *, for_execution: bool):
        src_text = self.src_edit.text().strip()
        dst_text = self.dst_edit.text().strip()

        if not src_text or not dst_text:
            QMessageBox.warning(self, "Missing Paths", "Please select source and destination folders.")
            return None

        src = Path(src_text).expanduser()
        dst = Path(dst_text).expanduser()

        include_files: list[str] | None = None
        files: list[Path] | None = None

        if self._source_files:
            files = self._source_files
            base = files[0].parent
            if any(p.parent != base for p in files):
                QMessageBox.warning(
                    self,
                    "Invalid Selection",
                    "Please select files from the same folder.",
                )
                return None
            if self.chk_mirror.isChecked():
                QMessageBox.warning(
                    self,
                    "Mirror not supported",
                    "Mirror mode is not supported when selecting files.",
                )
                return None
            src = base
            include_files = [p.name for p in files]

        if for_execution:
            dup_action = self._choose_duplicate_action(src, dst, files)
            if dup_action is None:
                return None
        else:
            dup_action = "ask"
            self._duplicate_pairs = []
        self._duplicate_action = dup_action

        try:
            return build_plan(
                src,
                dst,
                include_subdirs=self.chk_subdirs.isChecked(),
                move_files=self.chk_move.isChecked(),
                mirror=self.chk_mirror.isChecked(),
                retry_count=self.spin_retries.value(),
                retry_wait_sec=self.spin_wait.value(),
                multithread_count=self.spin_threads.value(),
                duplicate_action=dup_action,
                include_files=include_files,
            )
        except Exception as e:
            QMessageBox.critical(self, "Invalid Setup", str(e))
            return None
