# Commenting checklist

Use this checklist during review. It is a decision aid, not a requirement to comment every matching line.

## Comment when a reader might infer the wrong behavior

- A calculation uses a domain-specific denominator, unit, threshold, or sentinel value.
- A collection or normalization step intentionally deduplicates aliases, shared resources, or repeated observations.
- A value is unknown or unavailable by design rather than zero, empty, or healthy.
- A cache, snapshot, timestamp, or persistence rule has a non-obvious freshness or ownership contract.
- A bitmask, positional field, serialized format, or external API rule is difficult to identify from local code.
- A branch exists for a security boundary, authorization step, untrusted input, race, cancellation, retry, or stale response.
- A missing feature or omitted action is an explicit safety/product constraint and could otherwise look accidental.

## Keep the comment useful

- Put it immediately before the relevant branch or transformation.
- Say why, what invariant, or what external contract—not merely what the next line does.
- Keep it concise enough to remain true as surrounding implementation changes.
- Name limitations when the code deliberately cannot know something.
- Match the surrounding language and comment conventions.

## Do not add noise

Avoid comments that only translate syntax, repeat a descriptive function name, praise the code, record a temporary debugging thought, or promise behavior not enforced by code or tests. If the code is confusing because it is unnecessarily complex, report that separately instead of disguising the complexity with a long comment.
