"""Import/export helpers for .agent bundles."""

from __future__ import annotations

import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import yaml

from patternloop.loopspec import LoopSpec


def build_agent_bundle(
    *,
    spec_path: Path,
    out_path: Path,
    extra_readme: str | None = None,
) -> Path:
    spec = LoopSpec.model_validate(yaml.safe_load(spec_path.read_text(encoding="utf-8")))
    manifest = {
        "format": "patternloop.agent.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "name": spec.name,
        "content_sha256": spec.hash(),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=2))
        z.writestr("loopspec.yaml", spec_path.read_text(encoding="utf-8"))
        if extra_readme:
            z.writestr("README.txt", extra_readme)
    return out_path


def import_agent_bundle(*, zip_path: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        names = z.namelist()
        if "loopspec.yaml" not in names:
            raise ValueError("Invalid .agent bundle: missing loopspec.yaml")
        raw = z.read("loopspec.yaml").decode("utf-8")
    spec = LoopSpec.model_validate(yaml.safe_load(raw))
    final = dest_dir / f"{spec.name}.yaml"
    final.write_text(raw, encoding="utf-8")
    return final
