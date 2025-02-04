import subprocess
import os
import shutil
from utils import run_command, clone_repo

def update_and_install_packages():
    """Update package lists and install specified packages."""
    update_command = ["sudo", "apt", "update"]
    install_command = [
        "sudo", "apt", "install", "-y", "build-essential", "pkg-config", "gpg", "wget", "openssl",
        "libcryptsetup-dev", "python3-venv", "libtdx-attest-dev"
    ]

    # Run the update command
    run_command(update_command)

    # Run the install command
    run_command(install_command)

def build_project(repo_name):
    """Navigate to the full-disk-encryption directory and build the project."""
    fde_dir = os.path.join(repo_name, "full-disk-encryption")
    run_command(["make", "clean"], cwd=fde_dir)
    run_command(["make"], cwd=fde_dir)

def setup_fde_environment():
    repo_url = "https://github.com/IntelConfidentialComputing/TDXSampleUseCases.git"
    repo_name = repo_url.split('/')[-1].replace('.git', '')
    update_and_install_packages()
    clone_repo(repo_url, repo_name)
    build_project(repo_name)


