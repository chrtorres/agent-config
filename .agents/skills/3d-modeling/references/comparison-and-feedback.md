# Comparison and feedback provenance

## Initial capture

The user requested a new `3d-modeling` skill. No existing canonical skill with that name was present.

| Candidate | Outcome/user journey (25) | Inputs/scope (15) | Procedure (35) | Resources/dependencies (15) | Validation (10) | Score | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `full-stack-app-creation` | 0 | 0.25 | 0.25 | 0.25 | 0.25 | 18.75% | Application workflow with limited overlap in iterative previews. |
| `live-app-recreation` | 0 | 0.25 | 0.25 | 0.25 | 0.25 | 18.75% | Limited overlap in preview and presentation. |
| `safe-feature-uat` | 0.25 | 0.25 | 0.25 | 0.25 | 0.5 | 27.5% | Related human acceptance and feedback loop. |
| `verify-repository` | 0 | 0.25 | 0.25 | 0.5 | 0.5 | 25% | Related evidence discipline for repository verification. |

These scores use the original coverage factors with corrected arithmetic. All were below 75%, so the initial capture created a separate skill.

## Refinement capture

The user explicitly requested extending `3d-modeling`. The pre-update skill was compared with the incoming workflow for refining a multipart Blender object through approval. The factors below follow the same dimension order and weights as the initial comparison.

| Candidate | Coverage factors | Score | Evidence and decision |
| --- | --- | ---: | --- |
| `3d-modeling` | 1, 1, 0.75, 0.5, 0.5 | 78.75% | Its outcome and inputs already cover Blender revisions and approval. Steps 3–8 already cover constraints, new versions, previews and sign-off. Its Blender helpers cover model creation and rendering, and its tests cover dimensions and appearance. The example and checks lack mating geometry, assembly motion and retention. Extend this compatible skill with the missing methods and fixture. |
| `safe-feature-uat` | 0.25, 0, 0.25, 0, 0.25 | 17.5% | Its isolated candidates, observable outcomes, and human feedback apply in part. Its inputs, UAT form, and verification concern runnable applications. Keep it separate. |

## User feedback and implementation

1. Sanitized request: “Show a preview before any STL or Blend is approved; use create → review → confirm → continue to printing, and repeat after rejection with feedback.”
   - Change: added a mandatory rendered-preview gate, explicit approval state, version-preserving revision loop, and a printing boundary to `SKILL.md`.
   - Observed outcome: a Blender preview was rendered and inspected before this skill was captured.
   - Remaining limit: this skill cannot infer approval from a file existing; the user must explicitly approve the preview.

2. Sanitized paraphrase: The separate corner sockets made the frame too bulky. Make the rails interlock directly and consult industry guidance before revising.
   - Change: preserve the same envelope and rail profile, replace separate corners with integral stopped dovetails, and use the keyed vertical posts to block reverse slide. Use [assembly-refinement.md](assembly-refinement.md) for the source selection, assembly-order reasoning, and review procedure.
   - Historical outcome: the revised preview showed flush corners. Blender checked the assembled solids, sampled the insertion moves, and confirmed representative interference for the intended retention. The user approved the revised design after reviewing the views.
   - Remaining limit: the posts can pull free axially unless secured. Physical print units, printed fit, and load capacity remained open at design approval.
