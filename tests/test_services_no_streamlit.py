"""Guard test: ensure service modules don't import streamlit."""

import subprocess
import sys


def test_services_no_streamlit():
    """Verify that service modules can be imported without streamlit being loaded."""
    # Run in a subprocess to ensure clean module state
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; "
            "import app.services.ingest_service, "
            "app.services.document_service, "
            "app.services.auth_service; "
            "assert 'streamlit' not in sys.modules, f'streamlit loaded: {sys.modules[\"streamlit\"]}'"
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Subprocess failed: {result.stderr}"