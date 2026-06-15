import json
from pathlib import Path

NOTEBOOK_DIR = Path(__file__).resolve().parents[2] / "notebooks"


def test_notebooks_have_markdown_and_code_cells():
    notebook_paths = sorted(NOTEBOOK_DIR.glob("*.ipynb"))
    assert notebook_paths, "Expected at least one notebook."

    for path in notebook_paths:
        payload = json.loads(path.read_text())
        cells = payload["cells"]
        assert payload["nbformat"] == 4
        assert any(cell["cell_type"] == "markdown" for cell in cells), f"{path.name} is missing markdown cells."
        assert any(cell["cell_type"] == "code" for cell in cells), f"{path.name} is missing code cells."
