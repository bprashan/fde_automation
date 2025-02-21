import os
import sys
import pytest
sys.path.append(os.path.join(os.path.dirname(__file__), '../libs'))
from fde import *
from kbs import run_kbs
from utils import set_environment_variables, run_command

@pytest.mark.usefixtures("setup_environment")
class TestClass:

    def encrypt_base_image(self):
        """Encrypts the base image using a temporary FDE key."""
        base_image_path = os.environ["BASE_IMAGE_PATH"]
        kbs_cert_path =  os.environ["KBS_CERT_PATH"]
        tmp_fde_key = generate_tmp_fde_key()
        encrypt_image(tmp_fde_key, kbs_cert_path, base_image_path)

    def fetch_td_quote_and_encryption_keys(self):
        """Fetches the TD quote and encryption keys, and sets them as environment variables."""
        quote = get_td_measurement()
        set_environment_variables(data=quote)
        encryption_keys = retrieve_encryption_key()
        set_environment_variables(data=encryption_keys)
        return quote, encryption_keys

    def encrypt_and_verify_image(self):
        """Encrypts the image using the FDE key and verifies the TD encrypted image."""
        encrypt_image(os.environ["FDE_KEY"], kbs_cert_path, base_image_path, os.environ["KEY_ID"], os.environ["KBS_URL"])
        assert verify_td_encrypted_image(), "TD encrypted image verification failed"

    def test_e2e_fde_workflow(self):
        """Tests the end-to-end FDE workflow."""
        assert run_kbs(), "Failed to run KBS"
        encrypt_base_image()
        fetch_td_quote_and_encryption_keys()
        encrypt_and_verify_image()

    def test_fde_workflow_with_incorrect_vault_token(self):
        """Tests the FDE workflow with an incorrect Vault token."""
        original_root_token = os.environ["VAULT_CLIENT_TOKEN"]
        set_environment_variables("VAULT_CLIENT_TOKEN", "hvs.XXXXXXXXXXXXXXXXXXXXXXXX")
        try:
            result = run_kbs()
            assert result is False, "Expected kbs container logs to have error messages, but it looks clean"
        finally:
            set_environment_variables("VAULT_CLIENT_TOKEN", original_root_token)

    def test_fde_workflow_with_kv_secret_engine_disabled(self):
        """Tests the FDE workflow with the KV secret engine disabled."""
        disable_command = ["vault", "secrets", "disable", "keybroker"]
        enable_command = ["vault", "secrets", "enable", "-path=keybroker", "kv"]
        try:
            run_command(disable_command)
            result = run_kbs()
            assert result is False, "Expected kbs container logs to have error messages, but it looks clean"
        finally:
            run_command(enable_command)

    def test_fde_workflow_with_insecure_kbs_url(self):
        """Tests the FDE workflow with an insecure KBS URL."""
        assert run_kbs(), "Failed to run KBS"
        set_environment_variables(key="KBS_URL", data=f"http://{get_ip_address()}:9443")
        encrypt_base_image()
        _, encryption_keys = fetch_td_quote_and_encryption_keys()
        search_text="Client sent an HTTP request to an HTTPS server."
        assert search_text in encryption_keys, "Expecting error on sending HTTP request to an HTTPS server."

    def test_fde_workflow_with_incorrect_vault_token(self):
        """Tests the FDE workflow with an incorrect Vault token followed by a correct Vault token, without deleting the certificate file"""
        original_root_token = os.environ["VAULT_CLIENT_TOKEN"]
        set_environment_variables("VAULT_CLIENT_TOKEN", "hvs.XXXXXXXXXXXXXXXXXXXXXXXX")
        try:
            result = run_kbs()
            assert result is False, "Expected the KBS container logs to contain error messages, but they appear clean."
            set_environment_variables("VAULT_CLIENT_TOKEN", original_root_token)
            result = run_kbs()
            assert result is False, "Expected the KBS container logs to show error messages with the original root token and a corrupted certificate file, but they appear clean.""
        finally:
            set_environment_variables("VAULT_CLIENT_TOKEN", original_root_token)
