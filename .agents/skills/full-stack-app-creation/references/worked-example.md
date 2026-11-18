# Worked example: a local monitoring application

This is a concrete example of the general full-stack creation workflow, not a requirement that future apps monitor systems or use this stack.

The initial idea combined cautious Linux diagnosis with an interactive graphical interface. The resulting vertical slice uses a Python backend, explicit HTTP APIs, a buildless browser frontend, in-memory state, and JSON exports. It includes real host integration and separately labeled fixtures.

The complete reproduction set is described in [resources.md](resources.md). Domain-specific boundaries and interpretation live in [diagnostic-contract.md](diagnostic-contract.md); the example architecture and observable test outcomes are in [architecture-and-qa.md](architecture-and-qa.md). Historical visual/report examples are under [example-evidence](example-evidence/README.md).

The example supplied lessons applicable to broader app creation: translate intent into observable journeys, separate behavior from presentation, test actual backend exchanges and exported bytes, preserve cancellation and source identity, inspect responsive screenshots, declare dependencies, and scope source manifests to authored files. Its read-only diagnostic policy, five profiles, thresholds, theme, and runtime are example-specific.

The original system-monitoring-suite skill remains a specialized domain workflow. This general skill can be invoked independently and contains the complete example resources without requiring that sibling skill.
