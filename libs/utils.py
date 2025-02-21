import subprocess
import os
import sys
import socket
import shutil

def run_command(command, shell=False, cwd=None, env=None):
    """Run a shell command."""
    try:
        print(f"Executing command : {command}")
        result = subprocess.run(command, shell=shell, check=True, capture_output=True, text=True, cwd=cwd, env=env)
        print(result.stdout.strip())
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {command}")
        print(f"Return code: {e.returncode}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        sys.exit(1)

def run_command_with_popen(command, cwd=None):
    """Run a command in a subprocess and print the output in real-time."""
    print(f"Executing command : {command}")
    process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Print the output in real-time
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output.strip())

    # Print any remaining errors
    stderr = process.communicate()[1]
    if stderr:
        print(stderr.strip())

def set_environment_variables(key=None, data=None):
    """Set environment variables for a specific key and from a string of key-value pairs."""
    if key and data:
        os.environ[key] = data.strip('"')
        print(f"Set environment variable: {key}={data.strip('\"')}")

    if data:
        elements = data.split()
        for element in elements:
            if '=' in element:
                key, value = element.split('=', 1)
                os.environ[key] = value.strip('"')
                print(f"Set environment variable: {key}={value.strip('\"')}")

def get_ip_address():
    """Retrieve the actual IP address of the machine."""
    try:
        # Connect to an external server to get the local IP address
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
        return ip_address
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def clone_repo(repo_url, clone_dir, branch=None):
    """Clone a git repository into a specified directory."""
    if os.path.exists(clone_dir):
        shutil.rmtree(clone_dir)

    clone_command = ["git", "clone"]
    if branch:
        clone_command.extend(["-b", branch])
    clone_command.extend([repo_url, clone_dir])

    run_command(clone_command)

def remove_host_from_known_hosts(host, port, known_hosts_file='/home/sdp/.ssh/known_hosts'):
    # Construct the host string
    host_string = f'[{host}]:{port}'

    # Run the ssh-keygen command to remove the host entry
    subprocess.run(['ssh-keygen', '-f', known_hosts_file, '-R', host_string])

    print(f"Removed {host_string} from {known_hosts_file}")

def delete_file(file_path):
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"Successfully deleted the file: {file_path}")
        except Exception as e:
            print(f"Failed to delete the file: {file_path}. Reason: {e}")
    else:
        print(f"The file does not exist: {file_path}")

def delete_directory_with_sudo(directory_path):
    if os.path.exists(directory_path):
        try:
            # Execute the command to remove the directory with sudo
            run_command(['sudo', 'rm', '-rf', directory_path])
            print(f"Successfully deleted the directory: {directory_path}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to delete the directory: {directory_path}. Reason: {e}")
    else:
        print(f"The directory does not exist: {directory_path}")