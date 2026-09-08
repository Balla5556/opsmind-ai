"""Keep unit tests deterministic and independent of downloaded model binaries."""

import os


os.environ.setdefault("OPSMIND_EMBEDDING_PROVIDER", "offline")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
