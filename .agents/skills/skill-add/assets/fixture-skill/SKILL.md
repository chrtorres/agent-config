---
name: fixture-skill
description: Exercise resource indexing with a synthetic binary fixture; this is test input for the skill-add kit.
---

# Synthetic Packaging Fixture

The file `assets/object.bin` contains byte values from zero through thirty-one. It is synthetic input, not an executable or a private object.

Copy this fixture into scratch storage, verify its existing `references/bundle-index.json` with the parent kit's verifier, then change a byte and confirm that verification reports the object as changed. Regenerate the index only when intentionally accepting the updated resource set.

Do not install this fixture into model discovery directories except in an isolated test directory. It exists to test packaging rather than supply an operational workflow.
