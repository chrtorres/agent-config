---
name: product-refinement
description: Refine an existing model or application in one session using a measured baseline, focused design and QA checklists, explicit decisions, and isolated regression evidence.
---

# Product refinement

Use this workflow when a revision spans user journeys, visual quality, implementation and verification. Work in one session. Apply only the relevant role checklists and preserve one compact decision record. Follow the host workflow for artifact formats, runtime contracts and approval.

## Procedure

1. Inspect the previous version and its known issues. Capture one real baseline for each affected view or workflow. Record the reproduction steps and measured result. Reuse valid baseline observations from the same artifact.
2. Collect user references and preserve their provenance. Record which claims are photographed, measured or inferred. Inspect each image before citing it. Consult the source's terms and request limits.
3. Complete the [decision record](assets/refinement-record.md). Use the [role checklists](references/role-checklists.md) to resolve the user journey, visual targets, interface contract, motion and checks. Merge overlapping observations. Keep one owner for each decision and one test for each meaningful acceptance criterion.
4. Implement the narrowest end-to-end change first. Publish the local interface or asset descriptor early when it unblocks integration. Compare the first real render or response to the baseline and references before building secondary features.
5. Use an isolated copy for regressions and deliberate fault injection. Measure actual behavior, exercise recovery, inspect screenshots if applicable and verify the delivered artifacts by hash. Retain failure evidence alongside passing reruns.
6. Hand off the runnable artifact, evidence, remaining limitations and the approval state for the exact version.

## Reproduction resources

- [Decision record template](assets/refinement-record.md) and [synthetic completed example](assets/example-refinement.md)
- [Role checklists](references/role-checklists.md) and [capture provenance](references/provenance.md)
- [Record validator](scripts/check_refinement.py) and [behavioral tests](tests/test_check_refinement.py)
- [Shared viewer smoke runner](../smoke-test/SKILL.md) for asset delivery and [isolated app verification](../full-stack-app-creation/SKILL.md) for real interface behavior

## Validation and delivery

Run `python3 -B scripts/check_refinement.py <decision-record>` from this skill directory. Run `python3 -B -m unittest discover -s tests -v` for portable positive, missing-section and incomplete-record cases. The record check covers structure. Execute the host workflow's tests to establish actual behavior. Keep logs and screenshots in the project evidence directory.
