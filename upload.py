from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # Python 3.10
    except ModuleNotFoundError:
        print("ERROR: Python 3.10 需要先安装 tomli：")
        print("    py -m pip install tomli")
        sys.exit(1)


NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
NORMALIZE_RE = re.compile(r"[-_.]+")


@dataclass
class PackageInfo:
    dir_name: str
    path: Path
    name: str
    version: str
    dependencies: list[str]


def normalize_name(name: str) -> str:
    return NORMALIZE_RE.sub("-", name).lower()


def parse_requirement_name(requirement: str) -> str | None:
    requirement = requirement.strip()
    if not requirement:
        return None

    if ";" in requirement:
        requirement = requirement.split(";", 1)[0].strip()

    if "@" in requirement:
        left = requirement.split("@", 1)[0].strip()
        if left:
            return normalize_name(left)

    match = NAME_RE.match(requirement)
    if not match:
        return None
    return normalize_name(match.group(1))


def load_pyproject(pyproject_path: Path) -> PackageInfo:
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = data.get("project", {})

    name = project.get("name")
    version = project.get("version")
    dependencies = project.get("dependencies", [])

    if not name or not version:
        raise ValueError(f"Missing project.name or project.version in {pyproject_path}")

    return PackageInfo(
        dir_name=pyproject_path.parent.name,
        path=pyproject_path.parent,
        name=name,
        version=version,
        dependencies=dependencies,
    )


def discover_packages(packages_root: Path) -> dict[str, PackageInfo]:
    packages: dict[str, PackageInfo] = {}
    if not packages_root.exists():
        raise FileNotFoundError(f"Packages directory not found: {packages_root}")

    for child in sorted(packages_root.iterdir()):
        if not child.is_dir():
            continue
        pyproject = child / "pyproject.toml"
        if not pyproject.exists():
            continue

        pkg = load_pyproject(pyproject)
        normalized = normalize_name(pkg.name)
        if normalized in packages:
            raise ValueError(f"Duplicate normalized package name: {pkg.name}")
        packages[normalized] = pkg

    return packages


def topo_sort(packages: dict[str, PackageInfo]) -> list[PackageInfo]:
    deps_map: dict[str, set[str]] = {}
    reverse_map: dict[str, set[str]] = {}

    for pkg_name, pkg in packages.items():
        internal_deps: set[str] = set()
        for dep in pkg.dependencies:
            dep_name = parse_requirement_name(dep)
            if dep_name and dep_name in packages and dep_name != pkg_name:
                internal_deps.add(dep_name)

        deps_map[pkg_name] = internal_deps
        reverse_map.setdefault(pkg_name, set())
        for dep_name in internal_deps:
            reverse_map.setdefault(dep_name, set()).add(pkg_name)

    ready = sorted(name for name, deps in deps_map.items() if not deps)
    ordered: list[str] = []

    while ready:
        current = ready.pop(0)
        ordered.append(current)

        for dependent in sorted(reverse_map.get(current, set())):
            deps_map[dependent].discard(current)
            if not deps_map[dependent] and dependent not in ordered and dependent not in ready:
                ready.append(dependent)
        ready.sort()

    if len(ordered) != len(packages):
        unresolved = sorted(set(packages) - set(ordered))
        raise RuntimeError(f"Dependency cycle detected: {', '.join(unresolved)}")

    return [packages[name] for name in ordered]


def get_repo_urls(repository: str) -> tuple[str, str]:
    repository = repository.lower()
    if repository == "testpypi":
        return (
            "https://test.pypi.org/pypi/{name}/json",
            "https://test.pypi.org/legacy/",
        )
    return (
        "https://pypi.org/pypi/{name}/json",
        "https://upload.pypi.org/legacy/",
    )


def version_exists(package_name: str, version: str, repository: str) -> bool:
    json_url_tpl, _ = get_repo_urls(repository)
    url = json_url_tpl.format(name=package_name)

    req = Request(
        url,
        headers={"User-Agent": "python-library-upload-script/1.0"},
    )

    try:
        with urlopen(req, timeout=20) as resp:
            data = json.load(resp)
    except HTTPError as e:
        if e.code == 404:
            return False
        raise
    except URLError:
        raise

    releases = data.get("releases", {})
    if version in releases:
        return True

    info = data.get("info", {})
    return info.get("version") == version


def check_versions_in_parallel(
    packages: list[PackageInfo],
    repository: str,
    max_workers: int = 8,
) -> dict[str, bool]:
    if not packages:
        return {}

    results: dict[str, bool] = {}
    worker_count = min(max_workers, len(packages))

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_map = {
            executor.submit(version_exists, pkg.name, pkg.version, repository): pkg
            for pkg in packages
        }

        for future in as_completed(future_map):
            pkg = future_map[future]
            results[pkg.name] = future.result()

    return results


def run(cmd: list[str], cwd: Path) -> None:
    print(f"> {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(cwd))
    if result.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {result.returncode}")


def ensure_tool(module_name: str, install_hint: str) -> None:
    result = subprocess.run(
        [sys.executable, "-m", module_name, "--version"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        print(f"ERROR: Missing {module_name}. Install with:")
        print(f"    {install_hint}")
        sys.exit(1)


def process_package(pkg: PackageInfo, repository: str, already_exists: bool) -> None:
    print()
    print("=" * 60)
    print(f"Processing {pkg.name} ({pkg.version})")
    print("=" * 60)

    if already_exists:
        print(f"Skip: {pkg.name} {pkg.version} already exists on {repository}.")
        return

    dist_dir = pkg.path / "dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    run([sys.executable, "-m", "build"], cwd=pkg.path)
    run([sys.executable, "-m", "twine", "check", "dist/*"], cwd=pkg.path)
    run(
        [sys.executable, "-m", "twine", "upload", "dist/*"],
        cwd=pkg.path,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and upload all sub-packages.")
    parser.add_argument(
        "--repository",
        choices=["pypi", "testpypi"],
        default="pypi",
        help="Upload target repository",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    packages_root = root / "packages"

    ensure_tool("build", "py -m pip install --upgrade build twine")
    ensure_tool("twine", "py -m pip install --upgrade build twine")

    packages = discover_packages(packages_root)
    ordered = topo_sort(packages)

    print(f"Repository: {args.repository}")
    print("Upload order:")
    for pkg in ordered:
        print(f"  - {pkg.name} ({pkg.version})")

    print()
    print("Checking remote versions in parallel...")
    exists_map = check_versions_in_parallel(ordered, args.repository)

    for pkg in ordered:
        process_package(pkg, args.repository, exists_map[pkg.name])

    print()
    print("All packages processed successfully.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
        raise SystemExit(130)
    except Exception as exc:
        print(f"\nERROR: {exc}")
        raise SystemExit(1)