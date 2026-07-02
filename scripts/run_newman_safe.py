from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path


def read_env(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def runtime_environment(base_path: Path, secrets: dict[str, str]) -> dict:
    payload = json.loads(base_path.read_text(encoding="utf-8"))
    values = payload.setdefault("values", [])
    index = {str(item.get("key", "")): item for item in values}
    for key, value in secrets.items():
        if not value:
            continue
        if key in index:
            index[key]["value"] = value
            index[key]["enabled"] = True
        else:
            values.append({"key": key, "value": value, "type": "secret", "enabled": True})
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Guarded local Newman runner")
    parser.add_argument("--collection", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--secrets", default="config/local.secrets.env")
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--folder", action="append", default=[])
    parser.add_argument("--json-report", help="Optional explicit path for a sensitive Newman JSON report")
    args = parser.parse_args()
    if not args.allow_network:
        raise SystemExit("Refusing network execution. Re-run with --allow-network after offline validation.")

    collection = Path(args.collection).resolve()
    environment = Path(args.environment).resolve()
    if not collection.exists() or not environment.exists():
        raise SystemExit("Collection or environment file does not exist.")

    secrets = read_env(Path(args.secrets))
    merged = runtime_environment(environment, secrets)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".postman_environment.json", delete=False) as handle:
            json.dump(merged, handle)
            temp_path = Path(handle.name)
        try:
            os.chmod(temp_path, 0o600)
        except OSError:
            pass

        command = ["npx", "--no-install", "newman", "run", str(collection), "-e", str(temp_path), "--reporters", "cli", "--bail"]
        if args.json_report:
            report = Path(args.json_report).resolve()
            report.parent.mkdir(parents=True, exist_ok=True)
            command.extend(["--reporters", "cli,json", "--reporter-json-export", str(report)])
        for folder in args.folder:
            command.extend(["--folder", folder])
        print("Running Newman with a temporary local environment. Secret values are not placed on the command line.")
        return subprocess.run(command, check=False).returncode
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
