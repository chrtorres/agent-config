---
name: git-github-workflow
description: Work safely with Git repositories and GitHub-hosted collaboration, including inspection, branching, commits, synchronization, pull requests, review evidence, and handoff without exposing credentials or overwriting user work.
---

# Git and GitHub workflow

Use this skill when a task involves a Git repository or a GitHub-hosted project. Keep local repository operations, remote collaboration, and release-impacting actions distinct. The skill does not grant permission to push, merge, delete branches, close issues, or change repository settings.

## Establish scope and repository state

Read applicable workspace instructions before changing files. Identify the repository root, applicable nested instructions, current branch or detached state, remotes, worktree state, upstream tracking, and the user's requested outcome. Treat pre-existing changes as user-owned; do not discard, stage, amend, or reformat them without understanding their scope.

Use read-only checks first:

```sh
git rev-parse --show-toplevel
git status --short --branch
git remote -v
git log --oneline --decorate -n 10
git diff --stat
git diff --check
```

Inspect the relevant files, recent commits, branch relationship, and repository instructions before selecting a change strategy. If the directory is not the intended repository, stop and resolve the path rather than operating on a neighboring project.

## Choose a safe change path

Translate the request into a small, observable change and identify its acceptance checks. Preserve unrelated edits and avoid broad cleanup. Prefer a task branch when the user wants an isolated change or when the current branch is shared; use the repository's naming conventions and discover the base branch rather than assuming a name.

Before creating a commit, review the exact staged diff. Stage only intended paths, inspect staged and unstaged changes separately, and keep generated files, credentials, dependency caches, and machine-specific runtime state out of commits unless the repository explicitly requires a sanitized fixture.

Do not use destructive commands such as `git reset --hard`, broad checkout/restore, force-push, branch deletion, or history rewriting without explicit approval and a verified target. If recovery matters, record the current revision and preserve a patch or ref before an authorized rewrite.

## Implement and commit locally

Make the smallest necessary edit. Run focused tests and repository checks appropriate to the changed area. For documentation or configuration-only changes, still validate formatting, links, syntax, and the affected invocation when practical.

Review before committing:

```sh
git diff
git diff --cached
git status --short
```

Use a concise imperative commit subject that describes the change. Do not amend an existing commit unless the user asks for it or the workflow explicitly requires it. After committing, verify the commit identity, summary, changed paths, parent, and clean-or-expected worktree state with read-only commands.

## Synchronize with a remote

Treat remote operations as external state changes. Fetching is normally read-only; pushing changes shared history and requires the user's authorization. Before a push, verify the destination remote, current branch, upstream, commit range, and whether the remote has advanced. Prefer a normal push of a task branch. Explain divergence and ask before rebasing, merging, force-pushing, or changing the upstream.

Use a configured GitHub client such as `gh` only when available and authorized. Check authentication without printing tokens or credential material. Prefer structured, inspectable commands; quote user-provided titles, labels, paths, and descriptions safely. Never place secrets in command arguments, commit messages, issue bodies, pull requests, logs, or skill resources.

## Create or update GitHub collaboration artifacts

For a pull request, provide a clear title, summary, implementation notes, test results, limitations, and any follow-up work. Confirm the source and target branches, repository identity, commit range, and working tree before creating or updating it. Keep generated review text free of local usernames, absolute paths, hostnames, tokens, and private logs.

For issues, comments, labels, reviews, merges, releases, or branch deletion, distinguish preparation from execution. Prepare text or commands locally when authorization is missing; do not perform the external mutation by inference. When reviewing a pull request, inspect the actual diff, changed files, checks, discussion context, and merge state, and report observed evidence separately from assumptions.

## Validate and hand off

Classify each check as pass, fail, blocked, or not tested. A successful local test does not prove remote checks, permissions, branch protection, or deployment success. Capture the commands, repository revision, relevant test results, and external artifact links in task-local evidence; keep credentials and private runtime output outside the repository.

Report:

- repository and branch identity, summarized without exposing private credentials;
- files or commits changed and the reason for each material change;
- checks run and their observed outcomes;
- remote or GitHub actions performed, prepared, or intentionally not performed;
- remaining blockers, required approvals, and the next safe action.

Generalize reusable instructions. Discover repository names, branch names, account identities, URLs, commit IDs, issue numbers, ports, paths, and service identifiers at use time or represent them with placeholders such as `<repository>`, `<branch>`, `<commit>`, `<issue-number>`, and `<remote-url>`.

## Reproduction resources

This skill has no bundled repository, Git metadata, credentials, or live GitHub artifacts. Reproduction requires a target Git repository and, for remote collaboration, an authorized GitHub account or equivalent hosted Git service access. Use the installed Git client; use the GitHub CLI only when present and authenticated. Keep fresh diffs, logs, pull-request text, and run-specific reports in task evidence rather than this shared skill.

Read [comparison-and-disposition.md](references/comparison-and-disposition.md) for the capture decision, generalized-value policy, and resource inventory.

## Validation and delivery

Validate the skill by checking frontmatter, internal links, clean placeholder usage, and the bundle index. From the skill-add skill directory, run:

```sh
python3 scripts/bundle.py index <target-skill-directory>
python3 scripts/bundle.py verify <target-skill-directory>
```

When linking the skill into a model discovery directory, use the skill-add linker and verify that the link resolves to this canonical directory. This skill's invocation name is `git-github-workflow`.
