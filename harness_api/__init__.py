# -*- coding: utf-8 -*-
"""Research Harness UI 백엔드(FastAPI). repo 루트를 sys.path에 넣어
harness_paths·sim.config를 임포트 가능하게 한다(엔진 코드는 읽기만)."""
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

REPO_ROOT = _REPO
