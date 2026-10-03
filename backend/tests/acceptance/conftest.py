import pytest

from tests.acceptance.harness import TENANT, TENANT_B, Client


def _login_all(tenant, roles):
    out = {}
    for role in roles:  # sequential: concurrent first logins race on the LoginAttempt MERGE
        out[role] = Client(role, tenant)
    return out


@pytest.fixture(scope="session")
def users():
    return _login_all(TENANT, ["requester", "reviewer", "team_member", "operator",
                               "policy_editor", "rule_admin", "source_reader",
                               "operator_source", "outsider_requester", "outsider_reviewer"])


@pytest.fixture(scope="session")
def other_tenant_users():
    return _login_all(TENANT_B, ["requester", "reviewer", "operator", "policy_editor"])
