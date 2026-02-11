# converge.policy

Admission, trust, governance, and safety. **AdmissionPolicy** implementations (Open, Whitelist, Token) control who can join a pool; pools use them when joining. **TrustModel** maintains per-agent scores and supports discovery trust thresholds. **GovernanceModel** implementations resolve disputes: **Democratic** (majority vote), **Dictatorial** (single leader), **Bicameral** (two chambers must agree), **Veto** (majority with a veto counterpower), **Empirical** (evidence-weighted votes). **Safety** provides ResourceLimits, ActionPolicy (allowlist of actions), and validate_safety for resource checks. The **StandardExecutor** (runtime) accepts an optional **safety_policy** (ResourceLimits, ActionPolicy) to enforce action allowlists and task resource limits. Pools can set **trust_model** and **trust_threshold**; **PoolManager.join_pool** rejects agents whose trust score is below the threshold.

## Custom governance models

You can define your own governance by subclassing **GovernanceModel** and implementing **resolve_dispute(context) -> Any**:

1. **Subclass** `converge.policy.governance.GovernanceModel`.
2. **Implement** `resolve_dispute(self, context: Any) -> Any`. The `context` is whatever the caller provides when resolving a dispute (e.g. a dict with `"votes"`, `"weights"`, or custom keys). Return the chosen outcome, or `None` for no decision / deadlock.
3. **Use the model** either by passing it when creating a pool: `pool_manager.create_pool({"id": "my-pool", "governance_model": my_model})`, or by calling `my_model.resolve_dispute(context)` yourself when a dispute arises.

The pool stores the instance on `pool.governance_model` (if provided at creation). Built-in models (Democratic, Dictatorial, Bicameral, Veto, Empirical) document their expected context shape in their docstrings; your custom model can define any contract you need.

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
