#Shared Skill Tree
The `agent-config/` directory is the central home for reusable agent skills. Paths below are relative to `agent-config/`. Calling models should reference skills here through symlinks in their own skill-discovery directories.
# Layout
- `.agents/skills/<skill-name>/` contains each shared skill.
- Each skill directory contains a 'SKILL. nd' whose 'name" matches the directory.
- "templates/SKILL.md° is a starter template, not an active skill.
- Keep model-specific configuration and symlinks outside this directory.
Do not duplicate a skill into a calling model's directory. Link to the shared skill directory so its "SKILL.md' and supporting resources stay together.
* Capturing a Completed Task as a Skill
When a task produces a repeatable workflow, ask the assistant to capture the solution as a reusable skill. The skill should explain the general method, not just record the one task's result.
1. Copy •templates/SKILL.md' to
`.agents/skills/<skill-name>/SKILL.md`.
2. Replace every placeholder. Use a lowercase, hyphenated skill name that matches the directory name, and write a description that says when to use it.
3. Keep the procedure actionable and generalize task-specific paths, values, and assumptions. Add supporting files inside the skill directory only when the workflow needs them.
- **Hardcoded values need user approval.** Do not put environment-specific values in a skill, whether in the procedure, examples, or commands, without the user's explicit approval. This covers provider-, platform-, account-, organization-, and environment-specific identifiers and names, such as account, organization, project, workspace, resource, object, group, service, network, repository, branch, run, address, and role or permission-assignment identifiers. Use placeholders such as `<account-id>`, `<project-id>`, `<resource-id>`, `<service-name>`, or `<role-id>`, and tell the user which values you generalized. If a concrete value would help—for example, in a worked example—list the values and ask before including them. Never include secrets or tokens.
Review the skill against the completed task and check that its frontmatter name" exactly matches the directory name.
5. Link the new skill directory from each calling model's skill-discovery location. The skill can then be invoked by its discovered name for similar work.
