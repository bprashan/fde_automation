import shutil
import os
import fileinput
from utils import run_command, clone_repo, set_environment_variables, run_command_with_popen

def update_tdx_config(tdx_dir):
    """Update the TDX_SETUP_ATTESTATION value in the setup-tdx-config file."""
    config_file = os.path.join(tdx_dir, "setup-tdx-config")

    # Use fileinput to modify the file in place
    with fileinput.FileInput(config_file, inplace=True) as file:
        for line in file:
            print(line.replace('TDX_SETUP_ATTESTATION=0', 'TDX_SETUP_ATTESTATION=1'), end='')

def clone_and_patch_tdx_repository():
    """Clone a Git repository, copy a patch file, and apply the patch."""
    repo_url = "https://github.com/canonical/tdx.git"
    patch_file = "patches/run_td_sh.patch"
    repo_name = repo_url.split('/')[-1].replace('.git', '')

    clone_repo(repo_url, repo_name, branch="2.1")

    update_tdx_config(repo_name)

    # Copy the patch file to the repository directory
    shutil.copy(patch_file, repo_name)

    # Apply the patch
    run_command(["git", "apply", os.path.basename(patch_file)], cwd=f"{os.getcwd()}/{repo_name}")

def create_td_image():
    """Navigate to the guest-tools/image directory and run the create-td-image.sh script."""
    # Define the directory and script
    directory = "tdx/guest-tools/image"
    script = "./create-td-image.sh"

    # Run the script with sudo
    run_command_with_popen(["sudo", script], cwd=directory)
    set_environment_variables(key="BASE_IMAGE_PATH", data=f"{os.getcwd()}/tdx/guest-tools/image/tdx-guest-ubuntu-24.04-generic.qcow2")