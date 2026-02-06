from __future__ import annotations

from pathlib import Path
from typing import Tuple


def load_cag_assets(
    style_path: str = "assets/mock_style_guide.md",
    example_path: str = "assets/mock_example_exercise.md",
) -> Tuple[str, str]:
    style_text = Path(style_path).read_text(encoding="utf-8")
    example_text = Path(example_path).read_text(encoding="utf-8")
    return style_text, example_text
