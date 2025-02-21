import subprocess
import os
from utils import get_ip_address, clone_repo, run_command_with_popen, set_environment_variables, run_command
import shutil
import time

dir_name = "ita-kbs"

class KBSEnvConfig:
    def __init__(self, **kwargs):
        self.config = {
            "LOG_LEVEL": "DEBUG",
            "KEY_MANAGER": "VAULT",
            "ADMIN_USERNAME": os.getenv("ADMIN_USERNAME", "test"),
            "ADMIN_PASSWORD": os.getenv("ADMIN_PASSWORD", "test@123456"),
            "HTTP_READ_HEADER_TIMEOUT": 2,
            "BEARER_TOKEN_VALIDITY_IN_MINUTES": 2,
            "TRUSTAUTHORITY_API_URL": "https://api.trustauthority.intel.com",
            "TRUSTAUTHORITY_API_KEY": os.getenv("TRUSTAUTHORITY_API_KEY", "ZBixzqA3As2abpQsxgWin2wprwwZ6kiWuJjkr0103"),
            "TRUSTAUTHORITY_BASE_URL": os.getenv("TRUSTAUTHORITY_BASE_URL", "https://portal.trustauthority.intel.com"),
            "AUTHENTICATION_DEFEND_MAX_ATTEMPTS": 2,
            "AUTHENTICATION_DEFEND_INTERVAL_MINUTES": 2,
            "AUTHENTICATION_DEFEND_LOCKOUT_MINUTES": 2,
            "SAN_LIST": f"127.0.0.1,{get_ip_address()}",
            "VAULT_SERVER_IP": "127.0.0.1",
            "VAULT_SERVER_PORT": 8200,
            "VAULT_CLIENT_TOKEN": os.getenv("VAULT_CLIENT_TOKEN", "hvs.************************")
        }
        self.config.update(kwargs)

    def create_env_file(self, file_name="kbs.env"):
        content = "\n".join([f"{key}={value}" for key, value in self.config.items()])
        with open(file_name, 'w') as file:
            file.write(content)

def build_kbs():
    run_command_with_popen(['make', 'docker'], cwd=f"{os.getcwd()}/{dir_name}")

def setup_directories():
    """Create the required directories."""
    directories = [
        "data/users",
        "data/keys",
        "data/keys-transfer-policy",
        "data/certs/tls",
        "data/certs/signing-keys"
    ]

    for directory in directories:
        full_path = os.path.join(dir_name, directory)
        os.makedirs(full_path, exist_ok=True)
        print(f"Directory created: {full_path}")

def run_kbs_container(env_file, container_name):
    """Run the KBS Docker container with the specified environment file and container name."""
    # Stop and remove any existing container with the specified name
    try:
        subprocess.run(["docker", "rm", "-f", container_name], check=True)
        print(f"Existing Docker container '{container_name}' removed.")
    except subprocess.CalledProcessError:
        print(f"No existing Docker container named '{container_name}' to remove.")

    # Define the Docker run command
    command = [
        "docker", "run", "-d", "--restart", "unless-stopped", "--name", container_name,
        "--env-file", env_file,
        "--net=host",
        "-v", f"{os.getcwd()}/{dir_name}/data/certs:/etc/kbs/certs",
        "-v", "/etc/hosts:/etc/hosts",
        "-v", f"{os.getcwd()}/{dir_name}/data:/opt/kbs",
        "trustauthority/key-broker-service:v1.2.0"
    ]
    try:
        # Run the command
        subprocess.run(command, check=True)
        print(f"Docker container '{container_name}' started successfully.")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while starting the Docker container '{container_name}': {e}")

def get_docker_logs(container_name):
    """Fetch and display logs for the specified Docker container."""
    command = ["docker", "logs", container_name]
    return run_command(command)

def setup_kbs_environment():
    clone_repo("https://github.com/intel/trustauthority-kbs.git", dir_name, branch="v1.2.0")
    build_kbs()
    setup_directories()

def run_kbs():
    env_file_path = f"{os.getcwd()}/{dir_name}/kbs.env"
    print(env_file_path)
    config = KBSEnvConfig(TRUSTAUTHORITY_API_KEY="aeKQBT22ux7tZVB1uLyQN58Z1M9J0Bwg8LAQgLpl")
    config.create_env_file(env_file_path)
    container_name = "kbs"
    run_kbs_container(env_file_path, container_name)
    time.sleep(20)
    logs = get_docker_logs(container_name)

# Check for error messages in logs
    error_messages = ["error", "permission denied", "invalid token", "key create failed"]
    if any(error_message in logs for error_message in error_messages):
        print("Error detected in Docker logs. Exiting execution.")
        return False
    set_environment_variables(key="KBS_URL", data=f"https://{get_ip_address()}:9443")
    set_environment_variables(key="KBS_ENV", data=env_file_path)
    set_environment_variables(key="KBS_CERT_PATH", data=f"{os.getcwd()}/{dir_name}/data/certs/tls/tls.crt")
    return True