import os
import sys
import pytest
sys.path.append(os.path.join(os.path.dirname(__file__), '../libs'))
from fde import *
from kbs import run_kbs
from utils import set_environment_variables

@pytest.mark.usefixtures("setup_environment")
class TestClass:

    def test_e2e_fde_workflow(self):
        # Add assertions to verify End to End FDE workflow
        run_kbs()
        generate_rsa_key_pair()
        tmp_fde_key = generate_tmp_fde_key()
        base_image_path = os.environ["BASE_IMAGE_PATH"]
        kbs_cert_path =  os.environ["KBS_CERT_PATH"]
        encrypt_image(tmp_fde_key, kbs_cert_path, base_image_path)

        quote = get_td_measurement()
        set_environment_variables(data=quote)
        encryption_keys = retrieve_encryption_key()
        set_environment_variables(data=encryption_keys)
        encrypt_image(os.environ["FDE_KEY"], kbs_cert_path, base_image_path, os.environ["KEY_ID"], os.environ["KBS_URL"])
        assert verify_td_encrypted_image()