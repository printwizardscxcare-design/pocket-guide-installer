"""Retrieve and verify the game assets indexed for the guide cores."""

import concurrent.futures
import hashlib
import os
import shutil
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path


def get_file(spec, cache):
    name, sha1, size = spec
    file = cache / sha1

    def verified(path):
        if not path.exists() or path.stat().st_size != size:
            return False
        with path.open("rb") as f:
            return hashlib.file_digest(f, "sha1").hexdigest() == sha1

    if verified(file):
        return file
    url = "https://archive.org/download/openFPGA-Files/" + urllib.parse.quote(name)
    for attempt in range(3):
        tmp = None
        try:
            with (
                urllib.request.urlopen(url, timeout=60) as response,
                tempfile.NamedTemporaryFile(dir=cache, delete=False) as stream,
            ):
                tmp = Path(stream.name)
                shutil.copyfileobj(response, stream)
            if not verified(tmp):
                raise OSError("Asset size or digest mismatch")
            os.replace(tmp, file)
            return file
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2**attempt)
        finally:
            if tmp:
                tmp.unlink(missing_ok=True)


def transfer(plan, cache, install, stop):
    cache.mkdir(parents=True, exist_ok=True)
    errors = []
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:

        def fetch_active(spec):
            if stop.is_set():
                return None
            return get_file(spec, cache)

        jobs = {pool.submit(fetch_active, spec): dest for dest, spec in plan.items()}
        for job in concurrent.futures.as_completed(jobs):
            if stop.is_set():
                break
            dest = jobs[job]
            try:
                install(dest, job.result())
                done += 1
                if done % 20 == 0:
                    print(
                        "Verified game and system assets:",
                        done,
                        "/",
                        len(plan),
                        flush=True,
                    )
            except Exception as e:
                errors.append(f"{dest}: {e}")
    return done, errors
