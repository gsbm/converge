"""Tests for converge.policy.admission."""

from converge.policy.admission import OpenAdmission, TokenAdmission, WhitelistAdmission


def test_admission_policies():
    open_policy = OpenAdmission()
    assert open_policy.can_admit("agent1", {})

    whitelist = WhitelistAdmission(["agent1", "agent2"])
    assert whitelist.can_admit("agent1", {})
    assert not whitelist.can_admit("agent3", {})

    token_policy = TokenAdmission("secret_key")
    assert token_policy.can_admit("agent1", {"token": "secret_key"})
    assert not token_policy.can_admit("agent1", {"token": "wrong_key"})
    assert not token_policy.can_admit("agent1", {})


def test_admission_abstract():
    from converge.policy.admission import AdmissionPolicy

    class MyPolicy(AdmissionPolicy):
        def can_admit(self, a, c):
            return super().can_admit(a, c)

    p = MyPolicy()
    p.can_admit("a", {})
