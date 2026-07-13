# Semantic invariants

1. **ARD remains ternary.** Action, Rule, and Directive are mutually exclusive decomposition categories.
2. **Evidence is orthogonal.** Evidence references ARD elements and runtime events; it is not `decomposition.evidence[]`.
3. **Action remains atomic.** Branching and orchestration belong to planning plus Rule evaluation.
4. **Rule remains a judgment.** Runtime bindings point to named deterministic evaluators; textual Rule content is never executed.
5. **Directive remains context/knowledge.** Directives may guide planning and completion but are not direct tool calls.
6. **Runtime contract is additive.** Existing Skill documents remain valid without a runtime contract.
7. **Event stream is authoritative.** Run status and Evidence summaries are projections.
8. **Compensation is semantic.** A compensating action restores an acceptable business state, not necessarily the original bytes.
9. **Framework isolation.** MCP, OpenAI Agents SDK, and LangGraph details stay in adapters.
