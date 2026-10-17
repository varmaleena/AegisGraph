"""Create a source-only archive without credentials, caches, or installed dependencies."""
from pathlib import Path
import hashlib
import zipfile
root=Path(__file__).resolve().parents[1]
dest=root.parent/"aegis-graph-source.zip"
excluded={"node_modules",".next","__pycache__",".pytest_cache",".git",".venv","recordings"}
with zipfile.ZipFile(dest,"w",zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(root.rglob("*")):
        rel=path.relative_to(root)
        if not path.is_file() or any(part in excluded for part in rel.parts):
            continue
        if (path.name.startswith(".env") and path.name!=".env.example") or path.name.endswith((".tsbuildinfo","-install.log")) or path.name.startswith("debug-"):
            continue
        archive.write(path,Path("aegis-graph")/rel)
with zipfile.ZipFile(dest) as archive:
    assert archive.testzip() is None
    for required in ("README.md","docker-compose.yml","frontend/package-lock.json","backend/main.py"):
        assert "aegis-graph/"+required in archive.namelist()
print(dest)
print("SHA256",hashlib.sha256(dest.read_bytes()).hexdigest())
