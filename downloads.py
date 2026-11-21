"""Retrieve and verify the game assets indexed for the guide cores."""

import concurrent.futures
import hashlib
import os
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path


class TransferStopped(Exception):
    """A download was interrupted before it could be installed."""


def get_file(spec, cache, progress=None, stop=None):
    name, sha1, size = spec
    file = cache / sha1

    def emit(status, received=0, detail=""):
        if stop and stop.is_set():
            raise TransferStopped()
        if progress:
            progress(status=status, received=received, size=size, detail=detail)

    def verified(path):
        if not path.exists() or path.stat().st_size != size:
            return False
        with path.open("rb") as f:
            return hashlib.file_digest(f, "sha1").hexdigest() == sha1

    emit("Checking cache")
    if verified(file):
        emit("Verified cache", size)
        return file
    url = "https://archive.org/download/openFPGA-Files/" + urllib.parse.quote(name)
    for attempt in range(3):
        tmp = None
        try:
            emit("Downloading", detail=f"Attempt {attempt + 1} of 3")
            with (
                urllib.request.urlopen(url, timeout=60) as response,
                tempfile.NamedTemporaryFile(dir=cache, delete=False) as stream,
            ):
                tmp = Path(stream.name)
                received = 0
                last_update = 0
                while chunk := response.read(256 * 1024):
                    if stop and stop.is_set():
                        raise TransferStopped()
                    stream.write(chunk)
                    received += len(chunk)
                    now = time.monotonic()
                    if now - last_update >= 0.15:
                        emit("Downloading", received)
                        last_update = now
                emit("Verifying download", received)
            if not verified(tmp):
                raise OSError("Asset size or digest mismatch")
            os.replace(tmp, file)
            emit("Verified download", size)
            return file
        except TransferStopped:
            raise
        except Exception:
            if attempt == 2:
                raise
            emit("Retrying", detail=f"Attempt {attempt + 1} failed; trying again")
            if stop:
                if stop.wait(2**attempt):
                    raise TransferStopped()
            else:
                time.sleep(2**attempt)
        finally:
            if tmp:
                tmp.unlink(missing_ok=True)


def transfer(plan, cache, install, stop, progress=None):
    cache.mkdir(parents=True, exist_ok=True)
    errors = []
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:

        def emit(dest, **values):
            if progress:
                progress({"type": "item", "stage": "assets", "key": dest, **values})

        def fetch_active(dest, spec):
            if stop.is_set():
                raise TransferStopped()
            return get_file(spec, cache, lambda **v: emit(dest, **v), stop)

        jobs = {
            pool.submit(fetch_active, dest, spec): dest for dest, spec in plan.items()
        }
        for job in concurrent.futures.as_completed(jobs):
            if stop.is_set():
                break
            dest = jobs[job]
            try:
                local = job.result()
                emit(
                    dest,
                    status="Copying to card",
                    received=plan[dest][2],
                    size=plan[dest][2],
                )
                state = install(dest, local)
                done += 1
                emit(
                    dest,
                    status="Already on card" if state == "present" else "Installed",
                    received=plan[dest][2],
                    size=plan[dest][2],
                    finished=True,
                )
                if done % 20 == 0:
                    print(
                        "Verified game and system assets:",
                        done,
                        "/",
                        len(plan),
                        flush=True,
                    )
            except TransferStopped:
                pass
            except Exception as e:
                errors.append(f"{dest}: {e}")
                emit(
                    dest,
                    status="Needs attention",
                    detail=str(e),
                    size=plan[dest][2],
                    finished=True,
                    error=True,
                )
    return done, errors
