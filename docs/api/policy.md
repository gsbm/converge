# converge.policy

Admission, trust, governance, and safety. **AdmissionPolicy** implementations (Open, Whitelist, Token) control who can join a pool; pools use them when joining. **TrustModel** maintains per-agent scores and supports discovery trust thresholds. **GovernanceModel** implementations (Democratic, Dictatorial) resolve disputes. **Safety** provides ResourceLimits, ActionPolicy (allowlist of actions), and validate_safety for resource checks. The **StandardExecutor** (runtime) accepts an optional **safety_policy** (ResourceLimits, ActionPolicy) to enforce action allowlists and task resource limits. Pools can set **trust_model** and **trust_threshold**; **PoolManager.join_pool** rejects agents whose trust score is below the threshold.

```{eval-rst}
.. automodule:: converge.policy.admission
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.policy.trust
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.policy.governance
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: converge.policy.safety
   :members:
   :undoc-members:
   :show-inheritance:
```
