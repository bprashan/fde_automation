import os
import sys
import pytest
sys.path.append(os.path.join(os.path.dirname(__file__), '../libs'))
from fde import *
from kbs import run_kbs, check_error_messages, get_docker_logs
from utils import set_environment_variables, run_command, get_ip_address

@pytest.mark.usefixtures("setup_environment")
class TestClass:

    def encrypt_base_image(self):
        """Encrypts the base image using a temporary FDE key."""
        tmp_fde_key = generate_tmp_fde_key()
        encrypt_image(tmp_fde_key, os.environ["KBS_CERT_PATH"], os.environ["BASE_IMAGE_PATH"])

    def fetch_td_quote_and_encryption_keys(self):
        """Fetches the TD quote and encryption keys, and sets them as environment variables."""
        quote = get_td_measurement()
        quote_set_success = set_environment_variables(data=quote)
        encryption_keys = retrieve_encryption_key()
        keys_set_success = set_environment_variables(data=encryption_keys)
        return quote_set_success, keys_set_success

    def encrypt_and_verify_image(self):
        """Encrypts the image using the FDE key and verifies the TD encrypted image."""
        encrypt_image(os.environ["FDE_KEY"], os.environ["KBS_CERT_PATH"], os.environ["BASE_IMAGE_PATH"], os.environ["KEY_ID"], os.environ["KBS_URL"])
        assert verify_td_encrypted_image(), "TD encrypted image verification failed"

    def test_e2e_fde_workflow(self):
        """Tests the end-to-end FDE workflow."""
        assert run_kbs(), "Failed to run KBS"
        self.encrypt_base_image()
        quote_set_success, keys_set_success = self.fetch_td_quote_and_encryption_keys()
        assert quote_set_success, "Failed to generate TD measurement"
        assert keys_set_success, "Failed to generate encryption keys"
        self.encrypt_and_verify_image()

    def test_fde_workflow_with_incorrect_vault_token(self):
        """Tests the FDE workflow with an incorrect Vault token."""
        original_root_token = os.environ["VAULT_CLIENT_TOKEN"]
        set_environment_variables("VAULT_CLIENT_TOKEN", "hvs.XXXXXXXXXXXXXXXXXXXXXXXX")
        try:
            assert run_kbs(), "Failed to run KBS"
            self.encrypt_base_image()
            quote_set_success, keys_set_success = self.fetch_td_quote_and_encryption_keys()
            assert quote_set_success, "Failed to generate TD measurement"
            assert not keys_set_success, "Expecting an error when retrieving encryption keys due to an invalid vault token."
            assert check_error_messages(get_docker_logs()) is True, "Expecting kbs container logs to have error messages, but it looks clean"
        finally:
            set_environment_variables("VAULT_CLIENT_TOKEN", original_root_token)

    def test_fde_workflow_with_kv_secret_engine_disabled(self):
        """Tests the FDE workflow with the KV secret engine disabled."""
        disable_command = ["vault", "secrets", "disable", "keybroker"]
        enable_command = ["vault", "secrets", "enable", "-path=keybroker", "kv"]
        try:
            run_command(disable_command)
            assert run_kbs(), "Failed to run KBS"
            self.encrypt_base_image()
            quote_set_success, keys_set_success = self.fetch_td_quote_and_encryption_keys()
            assert quote_set_success, "Failed to generate TD measurement"
            assert not keys_set_success, "Expecting an error when retrieving encryption keys with the KV secret engine disabled."
            assert check_error_messages(get_docker_logs()) is True, "Expecting kbs container logs to have error messages, but it looks clean"
        finally:
            run_command(enable_command)

    def test_fde_workflow_with_insecure_kbs_url(self):
        """Tests the FDE workflow with an insecure KBS URL."""
        assert run_kbs(), "Failed to run KBS"
        set_environment_variables(key="KBS_URL", data=f"http://{get_ip_address()}:9443")
        self.encrypt_base_image()
        quote_set_success, keys_set_success = self.fetch_td_quote_and_encryption_keys()
        assert quote_set_success, "Failed to generate TD measurement"
        assert not keys_set_success, "Expecting error on sending HTTP request to an HTTPS server."


    def test_fde_workflow_with_incorrect_vault_token_and_corrupted_cert(self):
        """Tests the FDE workflow with an incorrect Vault token followed by a correct Vault token, without deleting the certificate file"""
        original_root_token = os.environ["VAULT_CLIENT_TOKEN"]
        set_environment_variables("VAULT_CLIENT_TOKEN", "hvs.XXXXXXXXXXXXXXXXXXXXXXXX")
        try:
            assert run_kbs(), "Failed to run KBS"
            self.encrypt_base_image()
            quote_set_success, keys_set_success = self.fetch_td_quote_and_encryption_keys()
            assert quote_set_success, "Failed to generate TD measurement"
            assert not keys_set_success, "Expecting an error when retrieving encryption keys due to an invalid vault token."
            assert check_error_messages(get_docker_logs()) is True, "Expecting kbs container logs to have error messages, but it looks clean"

            set_environment_variables("VAULT_CLIENT_TOKEN", original_root_token)
            assert run_kbs(), "Failed to run KBS"
            quote_set_success, keys_set_success = self.fetch_td_quote_and_encryption_keys()
            assert quote_set_success, "Failed to generate TD measurement"
            assert not keys_set_success, "Expecting an error when retrieving encryption keys due to an invalid vault token."
            assert check_error_messages(get_docker_logs()) is True, "Expecting kbs container logs to have error messages, but it looks clean"
        finally:
            set_environment_variables("VAULT_CLIENT_TOKEN", original_root_token)