import os
import sys
import pytest
import random
import string
import subprocess
sys.path.append(os.path.join(os.path.dirname(__file__), '../libs'))
from fde import *
from kbs import run_kbs, check_error_messages, get_docker_logs
from utils import set_environment_variables, run_command, get_ip_address
from kms import login_to_vault

@pytest.mark.usefixtures("setup_environment")
class TestClass:

    def generate_random_token(self, length=24):
        return 'hvs.' + ''.join(random.choices(string.ascii_letters + string.digits, k=length))

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

    def run_command_with_unset_env(self, cmd, unset_var):
        original_env = os.environ.copy()
        if unset_var in os.environ:
            del os.environ[unset_var]
        try:
            print("before runing the subpriocess")
            result = subprocess.Popen(cmd, text=True, env=os.environ)
            return result.returncode
        finally:
            os.environ.clear()
            os.environ.update(original_env)

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

    @pytest.mark.parametrize("kbs_url", [
        f"http://{get_ip_address()}:9443",  # Insecure URL
        "https://incorrect-url:9443"        # Incorrect URL
    ])
    def test_fde_workflow_with_various_kbs_urls(self, kbs_url):
        """Tests the FDE workflow with various KBS URLs."""
        assert run_kbs(), "Failed to run KBS"
        original_kbs_url = os.environ["KBS_URL"]
        set_environment_variables(key="KBS_URL", data=kbs_url)
        try:
            self.encrypt_base_image()
            quote_set_success, keys_set_success = self.fetch_td_quote_and_encryption_keys()
            assert quote_set_success, "Failed to generate TD measurement"
            assert not keys_set_success, f"Unexpected success for URL: {kbs_url}"
        finally:
            set_environment_variables("KBS_URL", original_kbs_url)


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


    def test_fde_workflow_with_vault_login_with_incorrect_token(self):
        """Tests the FDE workflow with vault login authentication with incorrect Vault token """
        for i in range(5):
            invalid_token = self.generate_random_token()
            result = login_to_vault(invalid_token)
            assert not result, f"Iteration {i+1}: Expected an error when trying to login with invalid token '{invalid_token}'"

    @pytest.mark.parametrize("unset_var", [
        "KBS_ENV",
        "KBS_URL",
        "KBS_CERT_PATH",
        "MRSIGNERSEAM",
        "MRSEAM",
        "MRTD",
        "QUOTE",
        "SEAMSVN"
    ])
    def test_fde_workflow_with_missing_parameters_retrieve_encryption_key(self, unset_var):
        cmd = [
            './retrieve_encryption_key.sh',
            '-k', os.environ.get("KBS_ENV", ""),
            '-u', os.environ.get("KBS_URL", ""),
            '-c', os.environ.get("KBS_CERT_PATH", ""),
            '-g', os.environ.get("MRSIGNERSEAM", ""),
            '-s', os.environ.get("MRSEAM", ""),
            '-t', os.environ.get("MRTD", ""),
            '-q', os.environ.get("QUOTE", ""),
            '-v', os.environ.get("SEAMSVN", "")
        ]

        returncode = self.run_command_with_unset_env(cmd, unset_var)
        assert returncode != 0

    @pytest.mark.parametrize("unset_var", [
        "TMP_FDE_KEY",
        "KBS_CERT_PATH",
        "BASE_IMAGE_PATH"
    ])
    def test_fde_workflow_with_missing_parameters_encrypt_base_image(self, unset_var):
        cmd = [
            'sudo', 'tools/image/fde-encrypt_image.sh',
            '-k', os.environ.get("TMP_FDE_KEY", ""),
            '-c', os.environ.get("KBS_CERT_PATH", ""),
            '-p', os.environ.get("BASE_IMAGE_PATH", "")
        ]

        returncode = self.run_command_with_unset_env(cmd, unset_var)
        assert returncode != 0
