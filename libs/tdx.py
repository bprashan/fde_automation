import subprocess
import shutil
import os
import fileinput
import sys
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
    run_command(["git", "apply", os.path.basename(patch_file)], cwd=repo_name)

def create_directory(directory):
    """Create a directory if it doesn't exist."""
    os.makedirs(directory, exist_ok=True)

def generate_rsa_keys():
    data_directory = "data"
    create_directory(data_directory)
    """Generate RSA private and public keys."""
    private_key_path = os.path.join(directory, "private.pem")
    public_key_path = os.path.join(directory, "public.pem")

    # Generate the private key
    gen_private_key_command = ["openssl", "genrsa", "-out", private_key_path, "3072"]
    subprocess.run(gen_private_key_command, check=True)

    # Generate the public key
    gen_public_key_command = ["openssl", "rsa", "-in", private_key_path, "-outform", "PEM", "-pubout", "-out", public_key_path]
    subprocess.run(gen_public_key_command, check=True)

def create_td_image():
    """Navigate to the guest-tools/image directory and run the create-td-image.sh script."""
    # Define the directory and script
    directory = "tdx/guest-tools/image"
    script = "./create-td-image.sh"

    # Run the script with sudo
    run_command_with_popen(["sudo", script], cwd=directory)
    set_environment_variables(key="BASE_IMAGE_PATH", data=f"{os.getcwd()}/tdx/guest-tools/image/tdx-guest-ubuntu-24.04-generic.qcow2")

def generate_tmp_fde_key():
    """Generate a temporary FDE key."""
    result = subprocess.run(["openssl", "rand", "-base64", "32"], capture_output=True, text=True, check=True)
    return result.stdout.strip()

def encrypt_image(fde_key, kbs_cert_path, base_image_path, key_id=None, kbs_url=None):
    """Encrypt the image using the FDE key and KBS certificate path."""
    command = [
        "sudo", "tools/image/fde-encrypt_image.sh", "-k", fde_key, "-c", kbs_cert_path, "-p", base_image_path
    ]
    
    if key_id:
        command.extend(["-i", key_id])
    if kbs_url:
        command.extend(["-u", kbs_url])
    
    run_command(command)

def execute_td_command(ssh_command, sleep_duration=120):
    """Execute the TD command and SSH command."""
    td_command = (
        'sudo TD_IMG=tools/image/td-guest-ubuntu-24.04-encrypted.img '
        'tdx/guest-tools/run_td.sh -d false -f tools/image/OVMF_FDE.fd'
    )

    process = subprocess.Popen(td_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    print(f"Sleeping for {sleep_duration} seconds to allow the TD guest to boot...")
    time.sleep(sleep_duration)

    if process.poll() is None:
        print("TD guest is still running.")
        result = run_command(ssh_command, shell=True)

        if result:
            print(result)
            print('Shutting down the TD guest...')
            safe_shut_down_command = "sshpass -p 123456 ssh -o StrictHostKeyChecking=no -p 10022 root@localhost 'sudo shutdown now'"
            run_command(safe_shut_down_command, shell=True)
            return result
    else:
        print("TD guest boot failure...")

def get_td_measurement():
    """Get the TD measurement."""
    ssh_command = "sshpass -p 123456 ssh -o StrictHostKeyChecking=no -p 10022 root@localhost 'sudo /sbin/fde-quote-gen'"
    return execute_td_command(ssh_command)

def retrieve_encryption_key():
    """Retrieve the encryption key."""
    required_vars = [
        "KBS_ENV", "KBS_URL", "KBS_CERT_PATH", "MRSIGNERSEAM",
        "MRSEAM", "MRTD", "QUOTE", "SEAMSVN"
    ]

    for var in required_vars:
        if var not in os.environ:
            raise EnvironmentError(f"Environment variable {var} is not set")

    command = [
        './retrieve_encryption_key.sh',
        '-k', os.environ["KBS_ENV"],
        '-u', os.environ["KBS_URL"],
        '-c', os.environ["KBS_CERT_PATH"],
        '-g', os.environ["MRSIGNERSEAM"],
        '-s', os.environ["MRSEAM"],
        '-t', os.environ["MRTD"],
        '-q', os.environ["QUOTE"],
        '-v', os.environ["SEAMSVN"]
    ]

    return run_command(command)

def verify_td_encrypted_image():
    ssh_command = "sshpass -p 123456 ssh -o StrictHostKeyChecking=no -p 10022 root@localhost 'sudo blkid'"
    result = execute_td_command(ssh_command)
    if 'TYPE="crypto_LUKS"' in result:
        return True
    else:
        return False
