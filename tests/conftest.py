import asyncio
import sys
import os

import pytest

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Apply to any test that needs a live database.
# Run with: RUN_INTEGRATION_TESTS=1 uv run pytest
skip_no_db = pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION_TESTS"),
    reason="set RUN_INTEGRATION_TESTS=1 to run integration tests",
)
