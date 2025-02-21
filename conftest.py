import pytest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'libs'))
from rust import setup_rust
from kms import setup_kms_environment
from kbs import setup_kbs_environment
from fde import setup_fde_environment, generate_rsa_key_pair
from tdx import clone_and_patch_tdx_repository, create_td_image
from docker import setup_docker_environment

@pytest.fixture(scope="session", autouse=True)
def setup_environment():
    delete_directory_with_sudo("TDXSampleUseCases")

    print("Setting up Docker environment")
    setup_docker_environment()

    print("Setting up Rust environment")
    setup_rust()

    print("Setting up FDE environment")
    setup_fde_environment()

    print("Setting up KMS environment")
    setup_kms_environment()

    print("Setting up KBS environment")
    setup_kbs_environment()

    print("Cloning and patching TDX repository")
    clone_and_patch_tdx_repository()

    print("Creating TD image")
    create_td_image()

    print("Generate RSA key pair")
    generate_rsa_key_pair()

@pytest.failure(autouse=True)
def cleanup():
    file_path = "TDXSampleUseCases/full-disk-encryption/ita-kbs/data/certs/tls/tls.crt"
    delete_file(file_path)
