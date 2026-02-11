# Process model

## Task flow (system-wide)

1. **Task submitted**: A task is created and submitted to the task manager (optionally persisted in a store).
2. **Pool formation**: Pools are created (with optional admission policy and governance model). Agents join or leave via decisions.
3. **Negotiation**: Agents negotiate (e.g. via NegotiationProtocol: propose, counter, accept, reject). Consensus (majority/plurality) and bidding/delegation protocols are available for coordination.
4. **Execution**: The runtime executes decisions: send messages, submit/claim/report tasks, join/leave/create pools, and **coordination decisions** (SubmitBid, Vote, Propose, AcceptProposal, RejectProposal, Delegate, RevokeDelegation) when the executor is configured with the corresponding protocols and votes_store. The executor applies decisions to the network and managers.
5. **Evaluation**: Task results are reported; trust and metrics can be updated.
6. **Trust update**: Trust model scores can be updated from outcomes (see `converge.policy.trust`).
7. **Archival**: Tasks and pool state can be persisted via the store; replay and metrics support inspection.

## Governance

- **Pools** enforce local rules: admission policy (who can join) and governance model (how disputes are resolved). No universal authority; the system is designed for decentralized or federated operation.
- **Network** and transport enforce delivery and optional verification; discovery is query-based over descriptors (topics, capabilities).

## Failure handling

The system must handle:

- Agent crashes
- Malicious or faulty agents
- Runaway coordination loops
- Deadlocks and resource exhaustion

Mechanisms include: pool-level admission and governance, task-level timeouts and assignment rules, resource quotas and action allowlists (see `converge.policy.safety`: `ResourceLimits`, `ActionPolicy`, `validate_safety`), and observability (logging, tracing, metrics, replay) for diagnosis. The executor logs errors for failed decision execution and continues with the next decision.

## Autonomy and scope

Agents cannot expand scope, create external side effects, or self-replicate beyond what is explicitly allowed by task and pool policy. Decisions are executed only through the executor and fallback; there is no implicit autonomy escalation.
