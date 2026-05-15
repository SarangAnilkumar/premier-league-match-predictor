from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


def save_json(data: Dict[str, Any], path: Path, *, pretty: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if pretty:
        text = json.dumps(data, indent=2, ensure_ascii=False)
    else:
        text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    path.write_text(text, encoding="utf-8")
    logger.info("Saved raw JSON response to %s", path)


def coerce_output_dir(output_dir: Optional[Path]) -> Path:
    if output_dir is None:
        return Path("data") / "raw" / "api_football"
    return output_dir


def coerce_processed_dir(output_dir: Optional[Path]) -> Path:
    """
    Processed outputs are kept separate from raw API payloads.

    If output_dir is provided, it is used as the base directory (the processed
    path will be `output_dir/processed/...` to keep artifacts together).
    """

    if output_dir is None:
        return Path("data") / "processed" / "api_football"

    return output_dir / "processed" / "api_football"

