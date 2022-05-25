#!/usr/bin/env python

import json
import os.path
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List

import requests

JSONDict = Dict[str, Any]

# The set of packages to build the repo around.
# This should always include streamlit and our target Python version.
BASE_PACKAGES = ["streamlit", "python=3.8"]

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))

# The directory that our Streamlit conda package is built into (the output
# of `make conda-distribution`).
STREAMLIT_PACKAGE_DIR = os.path.join(ROOT_DIR, "lib", "conda-recipe", "dist", "noarch")

# Directory to build the repo in.
CONDA_REPO_DIR = os.path.join(ROOT_DIR, "conda_repo")


def download_packages_to_cache() -> None:
    """Populate our local conda cache with our package dependencies."""
    command = [
        "conda",
        "create",
        # We're not creating an environment. Any name works here.
        "--name",
        "dummy-environment",
        # Look for the streamlit package in the location it gets built.
        "--channel",
        STREAMLIT_PACKAGE_DIR,
        "--strict-channel-priority",
        # Do not ask for confirmation.
        "--yes",
        # Download the repo's packages, but don't create the repo.
        "--download-only",
    ] + BASE_PACKAGES
    subprocess.run(command, check=True)


def get_conda_cache_dirs() -> List[str]:
    """Return a list of all conda cache directories."""
    result = subprocess.run(
        ["conda", "info", "--json"], check=True, stdout=subprocess.PIPE
    )
    conda_info = json.loads(result.stdout)
    return [path for path in conda_info["pkgs_dirs"] if Path(path).is_dir()]


def get_package_download_url(base_url: str, platform: str, dist_name: str) -> str:
    """Return the URL to download the given conda package from."""
    return f"{base_url}/{platform}/{dist_name}.tar.bz2"


def get_package_cache_path(cache_dir: str, dist_name: str) -> str:
    """Return the path that a given package should be downloaded to in a
    conda cache."""
    # `platform` is ignored - conda only downloads packages for the
    # current platform, and they all go in a flat cache directory.
    return os.path.join(cache_dir, f"{dist_name}.tar.bz2")


def get_package_repo_path(repo_root: str, platform: str, dist_name: str) -> str:
    """Return the path to write the given package to in a repo."""
    return os.path.join(repo_root, platform, f"{dist_name}.tar.bz2")


def get_package_list() -> List[JSONDict]:
    """Get the JSON manifest containing all packages for our repo."""
    print(
        "Solving conda environment and building package list (this can take a few minutes)..."
    )
    command = [
        "conda",
        "create",
        # We're not creating an environment. Any name works here.
        "--name",
        "dummy-environment",
        # Look for the streamlit package in the location it gets built.
        "--channel",
        STREAMLIT_PACKAGE_DIR,
        "--strict-channel-priority",
        # Do not ask for confirmation.
        "--yes",
        "--dry-run",
        # Retrieve results in JSON format.
        "--json",
    ] + BASE_PACKAGES
    result = subprocess.run(command, check=True, stdout=subprocess.PIPE)
    json_dict = json.loads(result.stdout)

    package_list = json_dict["actions"]["LINK"]
    print(f"conda environment solved ({len(package_list)} packages)")
    return package_list


def download_file(url: str, path: str) -> None:
    """Download the file at the given URL to the given path"""
    # Ensure the target directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)

    print(f"Downloading {url} -> {path}...")

    response = requests.get(url, stream=True)
    with open(path, "wb") as f:
        for data in response.iter_content():
            f.write(data)

    print(f"Download complete!")


def populate_repo_packages(package_infos: List[JSONDict], repo_root: str) -> None:
    """Populate the repo directory with its packages."""
    cache_dirs = get_conda_cache_dirs()

    for info in package_infos:
        repo_path = get_package_repo_path(
            repo_root=repo_root,
            platform=info["platform"],
            dist_name=info["dist_name"],
        )

        # If the package already exists in the repo, early-out.
        if Path(repo_path).is_file():
            print(f"{repo_path} exists already")
            continue

        # If the package exists in one of our cache directories,
        # copy it into place.
        copied_from_cache = False
        for cache_dir in cache_dirs:
            cache_path = get_package_cache_path(cache_dir, info["dist_name"])
            if Path(cache_path).is_file():
                print(f"Copying cached {cache_path} -> {repo_path}...")
                os.makedirs(os.path.dirname(repo_path), exist_ok=True)
                shutil.copyfile(src=cache_path, dst=repo_path)
                copied_from_cache = True
                break

        if copied_from_cache:
            continue

        # Fallback to downloading the package directly.
        package_url = get_package_download_url(
            base_url=info["base_url"],
            platform=info["platform"],
            dist_name=info["dist_name"],
        )
        download_file(package_url, repo_path)


def index_repo(repo_root: str) -> None:
    """Call `conda index` on the repo directory to finalize it."""
    subprocess.run(["conda", "index", repo_root], check=True)


packages = get_package_list()
populate_repo_packages(packages, CONDA_REPO_DIR)
index_repo(CONDA_REPO_DIR)
