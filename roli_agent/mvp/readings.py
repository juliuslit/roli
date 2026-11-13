"""The menu reader's answer saved per photo, for test reruns (SPEC_3_mvp.md 12.10.5).

The key is the image's hash, the reader prompt's version and the model, so a new photo, prompt or model can never reuse an old reading. Every fresh reading is saved;
one is reused only when ``MvpConfig.reuse_saved_reading`` is on, which is for evaluation reruns: a tester's run always reads the photo.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class SavedReadings:
    def __init__(self, directory: str | Path, model_id: str, prompt_version: str) -> None:
        self.dir, self.model_id, self.prompt_version = Path(directory), model_id, prompt_version

    def path(self, photo_path: str | Path) -> Path:
        image = hashlib.sha256(Path(photo_path).read_bytes()).hexdigest()
        key = hashlib.sha256(f"{image}|{self.prompt_version}|{self.model_id}".encode("utf-8")).hexdigest()[:32]
        return self.dir / f"{key}.json"

    def get(self, photo_path: str | Path) -> dict[str, Any] | None:
        try:
            return json.loads(self.path(photo_path).read_text(encoding="utf-8"))["menu"]
        except (OSError, ValueError, KeyError):
            return None

    def put(self, photo_path: str | Path, menu: dict[str, Any]) -> None:
        try:
            path = self.path(photo_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"model": self.model_id, "prompt_version": self.prompt_version, "menu": menu}, ensure_ascii=False, indent=1), encoding="utf-8")
        except OSError:
            pass                                            # a reading that cannot be saved is read again next time
