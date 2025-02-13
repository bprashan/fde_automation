import subprocess
import os
import time
from utils import run_command, clone_repo, run_command_with_popen, remove_host_from_known_hosts

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

def build_project():
    """Navigate to the full-disk-encryption directory and build the project."""
    run_command(["make", "clean"])
    run_command(["make"])

def setup_fde_environment():
    repo_url = "https://github.com/IntelConfidentialComputing/TDXSampleUseCases.git"
    repo_name = repo_url.split('/')[-1].replace('.git', '')
    update_and_install_packages()
    clone_repo(repo_url, repo_name)
    fde_dir = os.path.join(repo_name, "full-disk-encryption")
    os.chdir(fde_dir)
    print(f"Changed working directory to {os.getcwd()}")
    build_project()

def generate_rsa_key_pair(directory='data', key_size=3072):
    # Create the directory if it doesn't exist
    os.makedirs(directory, exist_ok=True)

    # Paths for the private and public keys
    private_key_path = os.path.join(directory, 'private.pem')
    public_key_path = os.path.join(directory, 'public.pem')

    # Generate the RSA private key
    subprocess.run(['openssl', 'genrsa', '-out', private_key_path, str(key_size)])

    # Extract the public key from the private key
    subprocess.run(['openssl', 'rsa', '-in', private_key_path, '-outform', 'PEM', '-pubout', '-out', public_key_path])

    print(f"RSA key pair generated successfully in '{directory}'.")

def generate_tmp_fde_key():
    """Generate a temporary FDE key."""
    result = subprocess.run(["openssl", "rand", "-base64", "32"], capture_output=True, text=True, check=True)
    return result.stdout.strip()

def encrypt_image(fde_key, kbs_cert_path, base_image_path, key_id=None, kbs_url=None):
    """Encrypt the image using the FDE key and KBS certificate path."""
    command = [
        "sudo", "./tools/image/fde-encrypt_image.sh", "-k", fde_key, "-c", kbs_cert_path, "-p", base_image_path
    ]

    if key_id:
        command.extend(["-i", key_id])
    if kbs_url:
        command.extend(["-u", kbs_url])

    run_command_with_popen(command)

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
        remove_host_from_known_hosts('localhost', 10022)
        result = run_command(ssh_command, shell=True)

        if result:
            print(result)
            print('Shutting down the TD guest...')
            remove_host_from_known_hosts('localhost', 10022)
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