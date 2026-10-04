"""Build ``dist/fuckwhatday.exe`` from ``src/fuckwhatday.bf``.

Run from the repository root::

    python buildexe.py          # build, then check the smoke inputs
    python buildexe.py --all    # build, then check every supported date too

Steps, in order:

1. translate ``src/fuckwhatday.bf`` to C with ``tools/bf2c.py``
   (one C statement per instruction run; no calendar logic is added)
2. compile ``assets/fuckwhatday.ico`` into a resource with ``windres``
3. compile and statically link with ``gcc``, so the exe needs no runtime
   beyond Windows itself
4. run the finished exe on the specified dates and a set of invalid inputs
   (with ``--all``, on every supported date as well), comparing every
   answer with the oracle; any mismatch fails the build

Requires gcc and windres on PATH (MinGW-w64, for example WinLibs).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from tools import bf2c, reference

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "src" / "fuckwhatday.bf"
ICON = ROOT / "assets" / "fuckwhatday.ico"
BUILD = ROOT / "build"
DIST = ROOT / "dist"
EXE_NAME = "fuckwhatday.exe"

GCC_FLAGS = ("-O2", "-static", "-s", "-Wall", "-Wno-unused-but-set-variable")

SMOKE_INPUTS = (
    b"19000101\n",
    b"19000228\n",
    b"19000229\n",
    b"20000229\n",
    b"20240229\n",
    b"20261004\n",
    b"20991231\n",
    b"20261004\r\n",
    b"20260431\n",
    b"20261301\n",
    b"21000101\n",
    b"2026-10-04\n",
    b"",
)


class BuildError(Exception):
    """A build step failed; the message says which and why."""


def require(tool: str) -> str:
    """Return the full path of ``tool`` on PATH; refuse with a reason if absent."""
    path = shutil.which(tool)
    if path is None:
        raise BuildError(f"{tool} not found on PATH; install MinGW-w64 (WinLibs)")
    return path


def call(*command: str) -> None:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise BuildError(f"{Path(command[0]).name} failed:\n{result.stderr}")


def build(out_dir: Path, work_dir: Path, *, icon: bool = True) -> Path:
    """Translate, compile and link; return the path of the exe."""
    gcc = require("gcc")
    work_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    c_file = work_dir / "fuckwhatday.c"
    c_file.write_text(bf2c.translate(SOURCE.read_text(encoding="ascii")), "ascii")
    print(f"translated {SOURCE.relative_to(ROOT)} to {c_file}")

    inputs = [str(c_file)]
    if icon:
        windres = require("windres")
        rc_file = work_dir / "icon.rc"
        rc_file.write_text(f'1 ICON "{ICON.as_posix()}"\n', "ascii")
        res_file = work_dir / "icon.o"
        call(windres, str(rc_file), "-O", "coff", "-o", str(res_file))
        inputs.append(str(res_file))
        print(f"compiled icon {ICON.relative_to(ROOT)}")

    exe = out_dir / EXE_NAME
    call(gcc, *GCC_FLAGS, "-o", str(exe), *inputs)
    print(f"linked {exe}")
    return exe


def run_exe(exe: Path, data: bytes) -> bytes:
    run = subprocess.run([str(exe)], input=data, capture_output=True, check=False)
    return run.stdout


def verify(exe: Path, inputs=SMOKE_INPUTS) -> list[str]:
    """Return a description of every input the exe answers wrongly."""
    failures = []
    for data in inputs:
        actual = run_exe(exe, data)
        expected = reference.expected_output(data)
        if actual != expected:
            failures.append(f"{data!r}: got {actual!r}, expected {expected!r}")
    return failures


def every_supported_input() -> tuple[bytes, ...]:
    return tuple(reference.encode(date) for date in reference.supported_dates())


def main(argv: list[str]) -> int:
    exhaustive = "--all" in argv
    try:
        exe = build(DIST, BUILD)
    except BuildError as error:
        print(f"build failed: {error}", file=sys.stderr)
        return 1
    inputs = SMOKE_INPUTS + every_supported_input() if exhaustive else SMOKE_INPUTS
    if exhaustive:
        print(f"checking {len(inputs)} inputs; this takes several minutes")
    failures = verify(exe, inputs)
    for failure in failures:
        print(f"WRONG {failure}", file=sys.stderr)
    if failures:
        return 1
    print(f"verified {len(inputs)} inputs against the oracle")
    print(f"done: {exe.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
