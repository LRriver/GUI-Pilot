#!/usr/bin/env python3
"""Local submission validator used by SUBMISSION_SOP.md."""

from __future__ import annotations

import argparse
import ast
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import zipfile


MAX_ZIP_BYTES = 20 * 1024 * 1024
ALLOWED_TOP_LEVEL = {"doc", "src"}
REQUIRED_FILES = {
    "src/agent.py",
    "src/agent_base.py",
    "src/requirements.txt",
}
BLOCKED_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".git",
    "output",
}
BLOCKED_SUFFIXES = {".pyc", ".pyo", ".log"}
LOCAL_MODULES = {"agent", "agent_base", "utils"}
PACKAGE_MAP = {"PIL": "pillow", "cv2": "opencv-python"}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def warn(warnings: list[str], message: str) -> None:
    warnings.append(message)


def norm_pkg(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_requirements(path: pathlib.Path) -> set[str]:
    packages: set[str] = set()
    if not path.exists():
        return packages
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        name = re.split(r"[<>=~!;\[]", line, maxsplit=1)[0].strip()
        if name:
            packages.add(norm_pkg(name))
    return packages


def walk_files(submission_dir: pathlib.Path) -> list[pathlib.Path]:
    return [p for p in submission_dir.rglob("*") if p.is_file()]


def check_structure(submission_dir: pathlib.Path, errors: list[str]) -> None:
    if not submission_dir.exists():
        fail(errors, f"submission dir missing: {submission_dir}")
        return
    top = {p.name for p in submission_dir.iterdir() if p.name != ".DS_Store"}
    if top != ALLOWED_TOP_LEVEL:
        fail(errors, f"top-level entries must be exactly {sorted(ALLOWED_TOP_LEVEL)}, got {sorted(top)}")
    for rel in REQUIRED_FILES:
        if not (submission_dir / rel).is_file():
            fail(errors, f"required file missing: {rel}")
    doc_files = list((submission_dir / "doc").glob("*")) if (submission_dir / "doc").exists() else []
    if not any(p.suffix.lower() in {".md", ".txt", ".pdf", ".docx"} for p in doc_files):
        fail(errors, "doc/ must contain a design document")


def check_blocked_artifacts(submission_dir: pathlib.Path, errors: list[str]) -> None:
    for path in submission_dir.rglob("*"):
        rel = path.relative_to(submission_dir).as_posix()
        if path.is_dir():
            if path.name in BLOCKED_DIR_NAMES or path.name.startswith("output"):
                fail(errors, f"blocked directory present: {rel}")
        elif path.suffix in BLOCKED_SUFFIXES or path.name == ".DS_Store":
            fail(errors, f"blocked file present: {rel}")


def check_compile(submission_dir: pathlib.Path, errors: list[str]) -> None:
    for path in (submission_dir / "src").rglob("*.py"):
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except Exception as exc:
            fail(errors, f"compile failed for {path.relative_to(submission_dir)}: {exc}")


def imported_roots(py_file: pathlib.Path) -> set[str]:
    roots: set[str] = set()
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    except SyntaxError:
        return roots
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.level == 0:
                roots.add(node.module.split(".")[0])
    return roots


def check_requirements(submission_dir: pathlib.Path, errors: list[str], warnings: list[str]) -> None:
    src_dir = submission_dir / "src"
    declared = parse_requirements(src_dir / "requirements.txt")
    imported: set[str] = set()
    stdlib = getattr(sys, "stdlib_module_names", set())
    for path in src_dir.rglob("*.py"):
        imported.update(imported_roots(path))
    third_party: set[str] = set()
    for root in sorted(imported):
        if root in LOCAL_MODULES or root in stdlib or root.startswith("_"):
            continue
        third_party.add(norm_pkg(PACKAGE_MAP.get(root, root)))
    missing = third_party - declared
    if missing:
        fail(errors, f"requirements.txt missing direct imports: {sorted(missing)}")
    unused = declared - third_party
    if unused:
        warn(warnings, f"requirements.txt has packages not directly imported by src: {sorted(unused)}")
    if len(declared) > 6:
        warn(warnings, f"requirements.txt declares many packages ({len(declared)}); keep dependencies small")


def run_import_checks(submission_dir: pathlib.Path, errors: list[str]) -> None:
    src_dir = submission_dir / "src"
    snippets = [
        ("path-import", "from agent import Agent; a=Agent(); print(a.__class__.__name__)"),
        ("cwd-import", "import agent; print(agent.Agent.__name__)"),
    ]
    for name, code in snippets:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(src_dir)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        cwd = src_dir if name == "cwd-import" else submission_dir
        proc = subprocess.run(
            [sys.executable, "-B", "-c", code],
            cwd=str(cwd),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
        )
        if proc.returncode != 0:
            fail(errors, f"{name} failed: {proc.stderr.strip() or proc.stdout.strip()}")


def check_zip(zip_path: pathlib.Path, errors: list[str]) -> None:
    if not zip_path.exists():
        fail(errors, f"zip missing: {zip_path}")
        return
    size = zip_path.stat().st_size
    if size > MAX_ZIP_BYTES:
        fail(errors, f"zip too large: {size} bytes > {MAX_ZIP_BYTES}")
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = [name for name in zf.namelist() if name and not name.endswith("/")]
            top = {name.split("/", 1)[0] for name in names}
            if top != ALLOWED_TOP_LEVEL:
                fail(errors, f"zip top-level entries must be doc/src, got {sorted(top)}")
            for rel in REQUIRED_FILES:
                if rel not in names:
                    fail(errors, f"zip required file missing: {rel}")
            for name in names:
                parts = name.split("/")
                if name.startswith("/") or ".." in parts:
                    fail(errors, f"unsafe zip path: {name}")
                if any(part in BLOCKED_DIR_NAMES or part.startswith("output") for part in parts):
                    fail(errors, f"blocked zip artifact: {name}")
                if pathlib.PurePosixPath(name).suffix in BLOCKED_SUFFIXES or parts[-1] == ".DS_Store":
                    fail(errors, f"blocked zip file: {name}")
    except zipfile.BadZipFile as exc:
        fail(errors, f"invalid zip: {exc}")


def check_pip_download(submission_dir: pathlib.Path, timeout: int, errors: list[str]) -> None:
    requirements = submission_dir / "src" / "requirements.txt"
    with tempfile.TemporaryDirectory(prefix="moon-pip-") as tmp:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "-r",
                str(requirements),
                "-d",
                tmp,
                "--timeout",
                str(timeout),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=max(timeout + 30, 60),
        )
        if proc.returncode != 0:
            fail(errors, "pip download failed:\n" + (proc.stderr.strip() or proc.stdout.strip()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission-dir", default="submission")
    parser.add_argument("--zip", dest="zip_path", required=True)
    parser.add_argument("--check-pip-download", action="store_true")
    parser.add_argument("--pip-timeout", type=int, default=60)
    args = parser.parse_args()

    submission_dir = pathlib.Path(args.submission_dir).resolve()
    zip_path = pathlib.Path(args.zip_path).resolve()
    errors: list[str] = []
    warnings: list[str] = []

    check_structure(submission_dir, errors)
    check_blocked_artifacts(submission_dir, errors)
    check_compile(submission_dir, errors)
    check_requirements(submission_dir, errors, warnings)
    run_import_checks(submission_dir, errors)
    check_zip(zip_path, errors)
    if args.check_pip_download:
        check_pip_download(submission_dir, args.pip_timeout, errors)

    if warnings:
        print("WARNINGS:")
        for item in warnings:
            print(f"- {item}")
    if errors:
        print("FAIL:")
        for item in errors:
            print(f"- {item}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
