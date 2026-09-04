from __future__ import annotations

from pathlib import Path

import nbformat
from nbclient import NotebookClient


def test_walkthrough_bundled_example_executes_offline() -> None:
    root = Path(__file__).resolve().parents[1]
    notebook = nbformat.read(root / "examples" / "walkthrough.ipynb", as_version=4)
    real_data_heading = next(
        index
        for index, cell in enumerate(notebook.cells)
        if cell.cell_type == "markdown" and "# Part 2 — real public CND" in cell.source
    )
    notebook.cells = notebook.cells[:real_data_heading]

    NotebookClient(
        notebook,
        timeout=120,
        kernel_name="python3",
        resources={"metadata": {"path": str(root)}},
    ).execute()
