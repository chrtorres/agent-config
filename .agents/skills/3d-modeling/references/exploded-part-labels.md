# Labeled exploded review

Use this pattern when a multipart model must be inspected by someone who cannot reliably identify every mesh from shape alone.

## Contract

Export one uniquely named top-level GLB node per inspectable part. Keep node names stable between revisions. Add a `parts` array to review metadata:

```json
{"parts":[{"node":"housing","label":"Housing","offset":[0,0,24]},{"node":"wheel_left","label":"Left wheel","offset":[-24,0,0]}]}
```

Offsets are translations in the GLB parent coordinate system and model units. Reject duplicate nodes, missing geometry, malformed offsets, and fewer than two parts for an exploded review.

## Review behavior

Explode should move every listed part and hide unlisted assembly guides. Each visible part gets a numbered callout, leader line, and keyboard-readable part-key entry. Selecting a callout or key entry isolates the corresponding part. Reassemble restores original transforms and guides and hides the labels/key UI. Narrow layouts must keep labels usable without making the canvas impossible to operate.

Run the multipart browser smoke test after changing this contract. Check loading, movement, per-part visibility, framing, repeated reassembly, callout coverage, leader lines, key coverage, and desktop/narrow layouts. Retain screenshots and pass-count evidence outside this shared skill.
