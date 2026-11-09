# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Write the backend OpenAPI schema as JSON to the given path.

Run from the repository root:
``uv run python -m scripts.export_openapi <output.json>``. The schema comes
from the FastAPI app object, so no server and no database are needed.
"""

import json
import sys
from pathlib import Path

from src.main import app


def main(argv: list[str]) -> int:
    """Write ``app.openapi()`` to the path in ``argv[1]``.

    Args:
        argv: Command line arguments, the output path at index 1.

    Returns:
        2 when the output path is missing, otherwise 0.
    """
    if len(argv) != 2:
        print("usage: export_openapi.py <output.json>", file=sys.stderr)
        return 2
    Path(argv[1]).write_text(
        json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
