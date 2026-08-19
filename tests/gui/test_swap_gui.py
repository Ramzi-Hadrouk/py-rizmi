"""GUI tests for License Swap tab."""
import json
import pytest

from py_rizmi.core.keypair import KeyPairManager
from py_rizmi.core.swap_auth import create_swap_request
from py_rizmi.gui.views.swap_view import LicenseSwapTab


@pytest.fixture
def gui_resources(tmp_path):
    priv_path = tmp_path / "priv.pem"
    pub_path = tmp_path / "pub.pem"
    KeyPairManager.save_keypair(str(priv_path), str(pub_path))

    req_payload = create_swap_request("curr_lic_str", "new_lic_str")
    req_file = tmp_path / "request.json"
    req_file.write_text(json.dumps(req_payload.to_dict()))

    return priv_path, req_file


def test_swap_tab_sign_workflow(qtbot, gui_resources):
    priv_path, req_file = gui_resources

    tab = LicenseSwapTab()
    qtbot.addWidget(tab)

    tab.txt_req_path.setText(str(req_file))
    tab.txt_key_path.setText(str(priv_path))

    tab._on_sign()

    output_text = tab.txt_output.toPlainText()
    assert output_text != ""
    auth_dict = json.loads(output_text)
    assert "payload" in auth_dict
    assert "signature" in auth_dict
    assert tab.lbl_status.text() == "Signed successfully!"
