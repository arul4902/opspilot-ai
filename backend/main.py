import os
import sys
import types

current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(current_dir)
for p in [current_dir, repo_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

if "backend" not in sys.modules:
    backend_pkg = types.ModuleType("backend")
    backend_pkg.__path__ = [current_dir]
    backend_pkg.__file__ = os.path.join(current_dir, "__init__.py")
    sys.modules["backend"] = backend_pkg

from backend.app.main import app

__all__ = ["app"]
