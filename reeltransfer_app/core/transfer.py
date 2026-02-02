from __future__ import annotations

import os
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Literal


@dataclass(frozen=True)
class RoboCopyPlan:
    src: Path
    dst: Path
    args: List[str]

    def command(self) -> List[str]:
        return ["robocopy", str(self.src), str(self.dst), *self.args]

    def command_string(self) -> str:
        return " ".join(shlex.quote(part) for part in self.command())


def build_plan(
    src: Path,
    dst: Path,
    *,
    include_subdirs: bool = True,
    move_files: bool = True,
    mirror: bool = False,
    dry_run: bool = False,
    retry_count: int = 1,
    retry_wait_sec: int = 1,
    multithread_count: int = 4,
    duplicate_action: Literal["ask", "skip", "overwrite", "rename"] = "ask",
    include_files: list[str] | None = None,
    include_file_list: bool = False,
    exclude_files: list[str] | None = None,
) -> RoboCopyPlan:
    if not src.exists():
        raise ValueError("Source does not exist.")
    if src.resolve() == dst.resolve():
        raise ValueError("Source and destination must be different.")

    args: List[str] = []

    if include_files:
        args.append("/LEV:1")
    elif include_subdirs:
        args.append("/E")
    if move_files:
        args.append("/MOVE")
    if mirror:
        args.append("/MIR")
    if dry_run:
        args.append("/L")

    args += [f"/R:{max(retry_count, 0)}", f"/W:{max(retry_wait_sec, 0)}"]
    if multithread_count and multithread_count > 0:
        args.append(f"/MT:{multithread_count}")

    if duplicate_action in {"skip", "rename"}:
        args += ["/XN", "/XO", "/XC"]
    elif duplicate_action == "overwrite":
        args += ["/IS", "/IT"]
    if include_files:
        args += ["/IF", *include_files]
    if exclude_files:
        args += ["/XF", *exclude_files]
    if include_file_list:
        args.append("/BYTES")
    else:
        args.append("/NFL")
    args += ["/NDL", "/NP", "/TEE"]

    return RoboCopyPlan(src=src, dst=dst, args=args)


def estimate_transfer(
    src: Path,
    *,
    include_subdirs: bool,
    include_files: list[str] | None = None,
    files: list[Path] | None = None,
) -> tuple[int, int]:
    """
    Returns (file_count, total_bytes)
    """
    targets: Iterable[Path]

    if files:
        targets = files
    elif include_files:
        targets = [src / name for name in include_files]
    else:
        targets = iter_source_files(src, include_subdirs=include_subdirs)

    count = 0
    total = 0
    for f in targets:
        if not f.exists() or not f.is_file():
            continue
        try:
            total += f.stat().st_size
            count += 1
        except OSError:
            continue

    return count, total


def is_windows() -> bool:
    return os.name == "nt"


def iter_source_files(src: Path, include_subdirs: bool) -> Iterable[Path]:
    if src.is_file():
        yield src
        return

    if include_subdirs:
        for root, _, files in os.walk(src):
            base = Path(root)
            for name in files:
                yield base / name
    else:
        for name in os.listdir(src):
            p = src / name
            if p.is_file():
                yield p


def find_duplicates(
    src: Path,
    dst: Path,
    *,
    include_subdirs: bool,
    sample_limit: int = 12,
    return_pairs: bool = False,
) -> tuple[int, list[Path], list[tuple[Path, Path]]]:
    """
    Returns (count, sample list) of files that already exist in destination.
    Duplicate is defined as: dst / relative_path exists.
    """
    total = 0
    sample: list[Path] = []
    pairs: list[tuple[Path, Path]] = []

    if not src.exists() or not dst.exists():
        return 0, [], []

    for f in iter_source_files(src, include_subdirs=include_subdirs):
        try:
            rel = f.relative_to(src)
        except ValueError:
            rel = f.name
        dest_file = dst / rel
        if dest_file.exists():
            total += 1
            if len(sample) < sample_limit:
                sample.append(dest_file)
            if return_pairs:
                pairs.append((f, dest_file))

    return total, sample, pairs


def find_duplicates_for_files(
    files: list[Path],
    dst: Path,
    *,
    sample_limit: int = 12,
    return_pairs: bool = False,
) -> tuple[int, list[Path], list[tuple[Path, Path]]]:
    total = 0
    sample: list[Path] = []
    pairs: list[tuple[Path, Path]] = []

    if not files or not dst.exists():
        return 0, [], []

    base = files[0].parent
    for f in files:
        if not f.exists():
            continue
        try:
            rel = f.relative_to(base)
        except ValueError:
            rel = f.name
        dest_file = dst / rel
        if dest_file.exists():
            total += 1
            if len(sample) < sample_limit:
                sample.append(dest_file)
            if return_pairs:
                pairs.append((f, dest_file))

    return total, sample, pairs


def _next_available_path(dst: Path) -> Path:
    if not dst.exists():
        return dst

    stem = dst.stem
    suffix = dst.suffix
    parent = dst.parent

    i = 1
    while True:
        candidate = parent / f"{stem} ({i}){suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def apply_duplicate_renames(
    pairs: list[tuple[Path, Path]],
    *,
    move_files: bool,
) -> tuple[int, list[str]]:
    """
    For duplicates, move/copy each source to a unique destination name.
    Returns (count, errors).
    """
    count = 0
    errors: list[str] = []

    for src, dst in pairs:
        if not src.exists():
            continue

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            final_dst = _next_available_path(dst)
            if move_files:
                shutil.move(str(src), str(final_dst))
            else:
                shutil.copy2(str(src), str(final_dst))
            count += 1
        except Exception as e:
            errors.append(f"{src} -> {dst}: {e}")

    return count, errors
