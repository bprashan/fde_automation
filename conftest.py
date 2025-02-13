import pytest
import sys
import os
#from libs.utils import *
sys.path.append(os.path.join(os.path.dirname(__file__), 'libs'))
from rust import setup_rust
from kms import setup_kms_environment
from kbs import setup_kbs_environment
from fde import setup_fde_environment
from tdx import clone_and_patch_tdx_repository, create_td_image
from docker import setup_docker_environment

@pytest.fixture(scope="session", autouse=True)
def setup_environment():
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