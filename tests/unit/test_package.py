import re

import open_rag_engine


def test_package_exposes_semver_version() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", open_rag_engine.__version__)
