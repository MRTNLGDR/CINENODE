from pathlib import Path
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

home = Path(tempfile.mkdtemp(prefix="cinenode-smoke-"))
env = os.environ | {"CINENODE_HOME": str(home), "CINENODE_TEST_MODE": "1"}
process = subprocess.Popen([sys.executable, "-m", "cinenode", "serve", "--host", "127.0.0.1", "--port", "8876", "--no-open"], env=env)
try:
    for _ in range(80):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8876/api/health", timeout=1) as response:
                if response.status == 200:
                    print(response.read().decode())
                    break
        except Exception:
            time.sleep(0.25)
    else:
        raise SystemExit("HTTP smoke test failed")
finally:
    process.terminate()
    try:
        process.wait(10)
    except subprocess.TimeoutExpired:
        process.kill()
