import time
import typing as t
from concurrent.futures import Future
from contextlib import contextmanager
from distutils.util import strtobool
from pathlib import Path
from typing import List, Optional, Type

import attrs
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    FileSizeColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from .string import get_common_prefix

console = Console(soft_wrap=True)
print = console.print


@attrs.define
class LogFileRedirector:
    log_path: Path

    _prev_logs: str = attrs.field(factory=str, init=False)

    def update(self):
        logs = self.log_path.read_text()
        log_lines = logs.split("\n")
        common_prefix = get_common_prefix(logs, self._prev_logs)
        offset = len(common_prefix.split("\n")) - 1
        updated = "\n".join(log_lines[offset:])
        if updated:
            print(updated)
        self._prev_logs = logs


def print_pretty(msg: str):
    print(msg)


def print_success(msg: str):
    print(":white_check_mark:", msg)


def print_exception(type: Type[BaseException], value: BaseException):
    print(f"[bold red]{type.__module__}.{type.__name__}[/bold red]: {str(value)}")


def print_warning(msg: str):
    print(f"[bold yellow]Warning:[/bold yellow] {msg}")


def wait_futures_with_pbar(
    futures: List[Future],
    *,
    desc: Optional[str] = None,
    update_interval: float = 0.01,
):
    if len(futures) > 0:
        try:
            with Progress() as progress:
                task_id = progress.add_task(desc if desc else "", total=len(futures))
                while True:
                    num_done = sum(fut.done() for fut in futures)
                    progress.update(task_id, completed=num_done)
                    if num_done >= len(futures):
                        break
                    time.sleep(update_interval)
            for fut in futures:
                fut.result()
        finally:
            for fut in futures:
                fut.cancel()


@contextmanager
def build_upload_and_download_progress(description: str, total: t.Optional[int] = None):
    text_col = TextColumn("{task.description}")
    cols = (
        [
            text_col,
            BarColumn(bar_width=None),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(compact=True),
        ]
        if total
        else [text_col, FileSizeColumn(), TransferSpeedColumn()]
    )
    with Progress(
        *cols,
        expand=total is not None,
    ) as progress:
        task = progress.add_task(description=description, total=total)
        yield task, progress


def yes_or_no_prompt(question: str) -> bool:
    """Prompt the yes/no question to the user."""

    while True:
        user_input = input(question + " [y/n]: ")
        try:
            return bool(strtobool(user_input))
        except ValueError:
            print("Please use y/n or yes/no.\n")
