import pytest
from libs.utils import *
from libs.rust import setup_rust
from libs.kms import setup_kms_environment
from libs.kbs import setup_kbs_environment
from libs.fde import setup_fde_environment
from libs.tdx import clone_and_patch_tdx_repository, create_td_image
from libs.docker import setup_docker_environment


@pytest.fixture(scope="session", autouse=True)
def setup_environment():
    setup_docker_environment()
    setup_rust()
    setup_fde_environment()
    setup_kms_environment()
    setup_kbs_environment()
    clone_and_patch_tdx_repository()
    create_td_image()