from __future__ import annotations

from pathlib import Path
import re
import shutil
from typing import Optional, Literal, cast, Any

from PySide6.QtCore import Qt, QProcess, QSettings
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLabel, QMessageBox,
    QLineEdit, QCheckBox, QTextBrowser, QStatusBar, QSpinBox, QProgressBar
)

from reeltransfer_app.core.transfer import (
    build_plan,
    is_windows,
    find_duplicates,
    find_duplicates_for_files,
    estimate_transfer,
    apply_duplicate_renames,
)


APP_NAME = "ReelTransfer"
APP_VERSION = "1.2.6"


def _to_int(value: object, default: int) -> int:
    try:
        return int(cast(Any, value))
    except (TypeError, ValueError):
        return default


class MainWindow(QMainWindow):
    def __init__(self, app) -> None:
        super().__init__()
        self.app = app

        self.setWindowTitle(f"{APP_NAME} — {APP_VERSION}")
        self.resize(980, 640)

        self._process: Optional[QProcess] = None
        self._duplicate_action: Optional[Literal["ask", "skip", "overwrite", "rename"]] = None
        self._duplicate_pairs: list[tuple[Path, Path]] = []
        self._source_files: list[Path] = []
        self._settings = QSettings("ReelTransfer", "ReelTransfer")
        self._progress_total_files = 0
        self._progress_total_bytes = 0
        self._progress_copied_files = 0
        self._progress_copied_bytes = 0
        self._output_buffer = ""
        self._progress_enabled = True
        self._file_line_re = re.compile(
            r"^\s*(New File|Newer|Older|Changed)\s+([0-9,]+)\s+",
            re.IGNORECASE,
        )

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
        self.src_storage_card, self.src_storage_value = self._make_storage_card("Source Storage")
        row1.addWidget(self.src_storage_card)

        row2 = QHBoxLayout()
        layout.addLayout(row2)
        row2.addWidget(QLabel("Destination:"))
        self.dst_edit = QLineEdit()
        self.dst_edit.setPlaceholderText("Select destination folder (local or network path)")
        self.btn_dst = QPushButton("Browse…")
        row2.addWidget(self.dst_edit, 1)
        row2.addWidget(self.btn_dst)
        self.dst_storage_card, self.dst_storage_value = self._make_storage_card("Destination Storage")
        row2.addWidget(self.dst_storage_card)

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
        self.chk_dry_run = QCheckBox("Dry run (/L) — no changes")
        self.chk_check_space = QCheckBox("Verify destination free space")
        self.chk_check_space.setChecked(True)
        dupes.addWidget(self.chk_check_dupes)
        dupes.addWidget(self.chk_dry_run)
        dupes.addWidget(self.chk_check_space)
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
        self.btn_clear = QPushButton("Clear Log")
        self.btn_stop.setEnabled(False)
        actions.addWidget(self.btn_preview)
        actions.addWidget(self.btn_start)
        actions.addWidget(self.btn_stop)
        actions.addWidget(self.btn_clear)
        actions.addStretch(1)

        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("Progress: 0%")
        layout.addWidget(self.progress)

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
        self.btn_clear.clicked.connect(self.log.clear)
        self.chk_mirror.toggled.connect(self._mirror_toggled)
        self.src_edit.textEdited.connect(self._src_text_edited)
        self.src_edit.textChanged.connect(self._update_storage_cards)
        self.dst_edit.textChanged.connect(self._update_storage_cards)

        self._load_settings()
        self._update_storage_cards()

    @staticmethod
    def _extract_path_text(text: str) -> str:
        if "  (" in text:
            return text.split("  (", 1)[0].strip()
        return text.strip()

    def _make_storage_card(self, title: str) -> tuple[QWidget, QLabel]:
        card = QWidget()
        card.setMinimumWidth(220)
        card.setStyleSheet(
            "QWidget {"
            "border: 1px solid #3a3f44;"
            "border-radius: 6px;"
            "padding: 6px;"
            "background-color: #1f2329;"
            "}"
            "QLabel { color: #d5dbe3; }"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 6)
        title_label = QLabel(f"<b>{title}</b>")
        value_label = QLabel("—")
        value_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return card, value_label

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
            self._update_storage_cards()

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
            self._update_storage_cards()

    def _src_text_edited(self) -> None:
        if self._source_files:
            self._source_files = []

    def _pick_dst(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select destination folder", str(Path.home()))
        if folder:
            self.dst_edit.setText(folder)
            self._update_storage_cards()

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

        if not self._preflight_check(plan.src, plan.dst):
            return

        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            QMessageBox.information(self, "Busy", "A transfer is already running.")
            return

        self.log.append(f"<b>Starting:</b> {plan.command_string()}")

        proc = QProcess(self)
        proc.setProgram(plan.command()[0])
        proc.setArguments(plan.command()[1:])
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        proc.readyReadStandardOutput.connect(lambda: self._read_output(proc))
        proc.finished.connect(self._on_finished)
        proc.started.connect(lambda: self._set_running(True))

        proc.start()
        self._process = proc

    def _stop(self) -> None:
        if not self._process:
            return
        if self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()
            self.statusBar().showMessage("Transfer stopped", 4000)

    def _read_output(self, proc: QProcess) -> None:
        data = bytes(proc.readAllStandardOutput().data()).decode(errors="ignore")
        if data:
            self.log.append(data.replace("\n", "<br>"))
            if self._progress_enabled:
                self._consume_output_lines(data)

    def _on_finished(self, exit_code: int, _status) -> None:
        self._set_running(False)

        # Robocopy exit codes: 0-7 are success/warnings, >=8 is failure
        if exit_code >= 8:
            self._update_progress(final=True)
            self.statusBar().showMessage(f"Transfer failed (code {exit_code})", 8000)
            current = self.progress.value()
            self.progress.setFormat(f"Progress: {current}% (failed)")
            QMessageBox.warning(self, "Transfer failed", f"Robocopy failed with code {exit_code}.")
            return
        else:
            self._update_progress(final=True)
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
        if running:
            self.progress.setValue(0)
            self.progress.setFormat("Progress: 0%")

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
        btn_skip = box.addButton("Skip existing", QMessageBox.ButtonRole.AcceptRole)
        btn_overwrite = box.addButton("Overwrite existing", QMessageBox.ButtonRole.DestructiveRole)
        btn_rename = box.addButton("Auto-rename duplicates", QMessageBox.ButtonRole.ActionRole)
        btn_cancel = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.exec()

        clicked = box.clickedButton()
        if clicked == btn_skip:
            self._duplicate_pairs = pairs
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
        dup_action = cast(Literal["ask", "skip", "overwrite", "rename"], dup_action)
        self._duplicate_action = dup_action

        exclude_files: list[str] | None = None
        if for_execution and dup_action == "skip" and self._duplicate_pairs:
            relative_paths: list[str] = []
            for src_file, _ in self._duplicate_pairs:
                try:
                    rel = src_file.relative_to(src)
                except ValueError:
                    rel = Path(src_file.name)
                relative_paths.append(str(rel))
            max_excludes = 200
            exclude_files = relative_paths[:max_excludes]

        try:
            return build_plan(
                src,
                dst,
                include_subdirs=self.chk_subdirs.isChecked(),
                move_files=self.chk_move.isChecked(),
                mirror=self.chk_mirror.isChecked(),
                dry_run=self.chk_dry_run.isChecked(),
                retry_count=self.spin_retries.value(),
                retry_wait_sec=self.spin_wait.value(),
                multithread_count=self.spin_threads.value(),
                duplicate_action=dup_action,
                include_files=include_files,
                include_file_list=for_execution,
                exclude_files=exclude_files,
            )
        except Exception as e:
            QMessageBox.critical(self, "Invalid Setup", str(e))
            return None

    def _preflight_check(self, src: Path, dst: Path) -> bool:
        files = self._source_files if self._source_files else None
        include_files = [p.name for p in files] if files else None

        count, total_bytes = estimate_transfer(
            src,
            include_subdirs=self.chk_subdirs.isChecked(),
            include_files=include_files,
            files=files,
        )

        self._progress_total_files = count
        self._progress_total_bytes = total_bytes
        self._progress_copied_files = 0
        self._progress_copied_bytes = 0
        if count > 0:
            size_mb = total_bytes / (1024 * 1024)
            self.log.append(f"<b>Preflight:</b> {count} file(s), ~{size_mb:,.2f} MB")

        if self.chk_check_space.isChecked():
            try:
                free = shutil.disk_usage(dst).free
                if total_bytes > 0 and free < total_bytes:
                    needed_mb = total_bytes / (1024 * 1024)
                    free_mb = free / (1024 * 1024)
                    needed_gb = total_bytes / (1024 * 1024 * 1024)
                    free_gb = free / (1024 * 1024 * 1024)
                    if needed_gb >= 10:
                        needed_text = f"~{needed_gb:,.2f} GB"
                        free_text = f"~{free_gb:,.2f} GB"
                    else:
                        needed_text = f"~{needed_mb:,.2f} MB"
                        free_text = f"~{free_mb:,.2f} MB"
                    QMessageBox.warning(
                        self,
                        "Low disk space",
                        f"Destination may not have enough space.\n\n"
                        f"Needed: {needed_text}\n"
                        f"Free: {free_text}",
                    )
            except Exception:
                self.log.append("<b>Preflight:</b> Unable to check free space.")

        if self.chk_dry_run.isChecked():
            self._progress_enabled = False
            self.statusBar().showMessage("Dry run enabled — no files will be changed", 6000)
            self.progress.setValue(0)
            self.progress.setFormat("Progress: disabled (dry run)")
        else:
            self._progress_enabled = True

        return True

    def _update_storage_cards(self) -> None:
        src_text = self._extract_path_text(self.src_edit.text())
        dst_text = self._extract_path_text(self.dst_edit.text())
        self._update_storage_card_value(self.src_storage_value, src_text)
        self._update_storage_card_value(self.dst_storage_value, dst_text)

    def _update_storage_card_value(self, label: QLabel, path_text: str) -> None:
        if not path_text:
            label.setText("—")
            return
        path = Path(path_text).expanduser()
        if not path.exists():
            label.setText("Unavailable")
            return
        if path.is_file():
            path = path.parent
        try:
            usage = shutil.disk_usage(path)
            label.setText(
                f"{self._format_bytes(usage.free)} free / {self._format_bytes(usage.total)} total"
            )
        except Exception:
            label.setText("Unavailable")

    def _consume_output_lines(self, data: str) -> None:
        self._output_buffer += data
        lines = self._output_buffer.splitlines(keepends=True)
        if not lines:
            return
        if not lines[-1].endswith("\n") and not lines[-1].endswith("\r"):
            self._output_buffer = lines[-1]
            lines = lines[:-1]
        else:
            self._output_buffer = ""

        for line in lines:
            self._update_progress_from_line(line.strip())

    def _update_progress_from_line(self, line: str) -> None:
        if not line:
            return
        match = self._file_line_re.match(line)
        if not match:
            return
        size_text = match.group(2).replace(",", "")
        try:
            size = int(size_text)
        except ValueError:
            size = 0

        self._progress_copied_files += 1
        self._progress_copied_bytes += max(size, 0)
        self._update_progress()

    def _update_progress(self, *, final: bool = False) -> None:
        total_bytes = self._progress_total_bytes
        total_files = self._progress_total_files
        copied_bytes = self._progress_copied_bytes
        copied_files = self._progress_copied_files

        if total_bytes > 0:
            percent = min(100, int((copied_bytes / total_bytes) * 100))
            self.progress.setValue(percent)
            self.progress.setFormat(
                f"Progress: {percent}% ({self._format_bytes(copied_bytes)} / {self._format_bytes(total_bytes)})"
            )
        elif total_files > 0:
            percent = min(100, int((copied_files / total_files) * 100))
            self.progress.setValue(percent)
            self.progress.setFormat(
                f"Progress: {percent}% ({copied_files} / {total_files} files)"
            )
        elif final:
            if copied_bytes > 0 or copied_files > 0:
                self.progress.setValue(100)
                self.progress.setFormat("Progress: 100%")
            else:
                self.progress.setValue(0)
                self.progress.setFormat("Progress: 0%")

    @staticmethod
    def _format_bytes(value: int) -> str:
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(value)
        for unit in units:
            if size < 1024 or unit == units[-1]:
                return f"{size:,.2f} {unit}"
            size /= 1024
        return f"{size:,.2f} TB"

    def _load_settings(self) -> None:
        self.src_edit.setText(str(self._settings.value("src", "")))
        self.dst_edit.setText(str(self._settings.value("dst", "")))
        self.chk_subdirs.setChecked(bool(self._settings.value("subdirs", True)))
        self.chk_move.setChecked(bool(self._settings.value("move", True)))
        self.chk_mirror.setChecked(bool(self._settings.value("mirror", False)))
        self.chk_check_dupes.setChecked(bool(self._settings.value("dupes", True)))
        self.chk_dry_run.setChecked(bool(self._settings.value("dry_run", False)))
        self.chk_check_space.setChecked(bool(self._settings.value("check_space", True)))
        retries_val = self._settings.value("retries", 1)
        wait_val = self._settings.value("wait", 1)
        threads_val = self._settings.value("threads", 4)
        self.spin_retries.setValue(_to_int(retries_val, 1))
        self.spin_wait.setValue(_to_int(wait_val, 1))
        self.spin_threads.setValue(_to_int(threads_val, 4))

    def closeEvent(self, event) -> None:
        self._settings.setValue("src", self.src_edit.text())
        self._settings.setValue("dst", self.dst_edit.text())
        self._settings.setValue("subdirs", self.chk_subdirs.isChecked())
        self._settings.setValue("move", self.chk_move.isChecked())
        self._settings.setValue("mirror", self.chk_mirror.isChecked())
        self._settings.setValue("dupes", self.chk_check_dupes.isChecked())
        self._settings.setValue("dry_run", self.chk_dry_run.isChecked())
        self._settings.setValue("check_space", self.chk_check_space.isChecked())
        self._settings.setValue("retries", self.spin_retries.value())
        self._settings.setValue("wait", self.spin_wait.value())
        self._settings.setValue("threads", self.spin_threads.value())
        super().closeEvent(event)
