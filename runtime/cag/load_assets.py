from __future__ import annotations

from pathlib import Path
from typing import Tuple


def load_cag_assets(
    style_path: str = "assets/style_guide.md",
    example_path: str = "assets/example_exercise.md",
) -> Tuple[str, str]:
    style_file = Path(style_path)
    example_file = Path(example_path)
    style_text = style_file.read_text(encoding="utf-8") if style_file.exists() else ""
    example_text = example_file.read_text(encoding="utf-8") if example_file.exists() else ""
    return style_text, example_text
