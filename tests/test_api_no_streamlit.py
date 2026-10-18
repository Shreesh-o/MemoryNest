"""Guard test: ensure API modules don't import streamlit."""

import subprocess
import sys


def test_api_no_streamlit():
    """Verify that API modules can be imported without streamlit being loaded."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; "
            "import app.api.main, app.api.deps, app.api.schemas, app.api.security; "
            "import app.api.routers.auth, app.api.routers.documents, app.api.routers.health; "
            "assert 'streamlit' not in sys.modules, f'streamlit loaded: {sys.modules[\"streamlit\"]}'"
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Subprocess failed: {result.stderr}"