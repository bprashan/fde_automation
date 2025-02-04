import subprocess

def check_rust_installed():
    try:
        result = subprocess.run(["rustc", "--version"], capture_output=True, text=True, check=True)
        print("Rust is already installed:", result.stdout)
        return True
    except subprocess.CalledProcessError:
        print("Rust is not installed.")
        return False

def setup_rust():
    # Check if Rust is already installed
    if not check_rust_installed():
        # Run the Rust installation script
        subprocess.run("curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y", shell=True)

        # Source the environment variables
        subprocess.run("source $HOME/.cargo/env", shell=True)