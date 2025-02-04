import subprocess
import re
import os
from utils import set_environment_variables


def is_vault_installed():
    """Check if Vault is already installed."""
    try:
        result = subprocess.run(["vault", "--version"], capture_output=True, text=True, check=True)
        print(f"Vault is already installed: {result.stdout}")
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        return False

def setup_vault():
    """Install HashiCorp Vault if it is not already installed."""
    if is_vault_installed():
        print("HashiCorp Vault is already installed. Skipping installation.")
        return

    try:
        # Update the package list
        subprocess.run(["sudo", "apt-get", "update"], check=True)

        # Install necessary dependencies
        subprocess.run(["sudo", "apt-get", "install", "-y", "gnupg", "software-properties-common"], check=True)

        # Add the HashiCorp GPG key
        subprocess.run(["wget", "-O-", "https://apt.releases.hashicorp.com/gpg"], check=True)
        subprocess.run(["gpg", "--dearmor", "-o", "/usr/share/keyrings/hashicorp-archive-keyring.gpg"], check=True)

        # Add the official HashiCorp Linux repository
        subprocess.run(["sudo", "apt-add-repository", "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main"], check=True)

        # Update the package list again
        subprocess.run(["sudo", "apt-get", "update"], check=True)

        # Install Vault
        subprocess.run(["sudo", "apt-get", "install", "-y", "vault"], check=True)

        print("HashiCorp Vault installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")

def kill_existing_vault_process(port=8200):
    """Check if any process is listening on the specified port and kill it."""
    check_command = ["lsof", "-i", f":{port}"]
    check_process = subprocess.run(check_command, capture_output=True, text=True)
    
    if check_process.returncode == 0:
        # Extract the PID and kill the process
        pid = re.search(r'\n(\S+)\s+(\d+)', check_process.stdout).group(2)
        kill_command = ["sudo", "kill", "-9", pid]
        kill_process = subprocess.run(kill_command, capture_output=True, text=True)
        
        if kill_process.returncode == 0:
            print(f"Successfully killed the existing Vault process with PID: {pid}")
        else:
            print("Failed to kill the existing Vault process.")
            print(kill_process.stderr)
    else:
        print(f"No existing Vault process found on port {port}.")

def start_vault_server():
    """Kill any existing Vault process and start the Vault server in development mode."""
    kill_existing_vault_process()
    process = subprocess.Popen(["vault", "server", "-dev"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return process

def get_vault_root_token(process):
    """Extract the root token from the Vault server's output."""
    root_token = None
    while True:
        line = process.stdout.readline()
        if not line:
            break
        print(line.strip())  # Print each line for debugging purposes
        match = re.search(r'Root Token: (\S+)', line)
        if match:
            root_token = match.group(1)
            break

    return root_token

def login_to_vault(root_token):
    """Log in to Vault using the root token."""
    os.environ['VAULT_ADDR'] = 'http://127.0.0.1:8200'
    
    login_command = ["vault", "login", root_token]
    login_process = subprocess.run(login_command, capture_output=True, text=True)
    
    if login_process.returncode == 0:
        print("Successfully logged in to Vault.")
        return True
    else:
        print("Failed to log in to Vault.")
        print(login_process.stderr)
        return False

def enable_secrets_engine():
    """Enable the KV secrets engine at the specified path."""
    enable_command = ["vault", "secrets", "enable", "-path=keybroker", "kv"]
    enable_process = subprocess.run(enable_command, capture_output=True, text=True)
    
    if enable_process.returncode == 0:
        print("Successfully enabled the KV secrets engine at path 'keybroker'.")
    else:
        print("Failed to enable the KV secrets engine.")
        print(enable_process.stderr)

def setup_kms_environment():
    setup_vault()
    process = start_vault_server()
    root_token = get_vault_root_token(process)
    
    if root_token:
        # print(f"Root Token: {root_token}")
        if login_to_vault(root_token):
            enable_secrets_engine()
            set_environment_variables(key="VAULT_CLIENT_TOKEN", data=root_token)
    else:
        print("Root Token not found in the output.")

# this is testing usage can be removed after final validation
setup_kms_environment()