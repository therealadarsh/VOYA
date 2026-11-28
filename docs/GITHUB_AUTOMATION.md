# GitHub automation (owner setup)

**Scope:** merge assistance for PRs into `dev` only. Agents and bots do **not**
receive a token that can merge. The **`auto-merge`** label on a PR is treated as
the owner’s intent to merge after CI passes.

Workflow: [`.github/workflows/auto-merge.yml`](../.github/workflows/auto-merge.yml).

---

## 1. Repository settings (GitHub UI)

Do these on [github.com/therealadarsh/VOYA](https://github.com/therealadarsh/VOYA)
(or your fork’s settings if you are rehearsing elsewhere).

| Setting | Where | Recommended |
|---|---|---|
| **Automatically delete head branches** | **Settings → General → Pull Requests** | **On** — removes the branch after merge (works with `gh pr merge --delete-branch` and normal merges). |
| **Allow auto-merge** (optional) | Same section | **Off** for this repo’s model — we use the label workflow, not GitHub’s built-in auto-merge queue. |
| **Restrict who can push to matching branches** | **Settings → Rules → Rulesets** (or classic branch protection on `dev`) | Only trusted people; require PRs for `dev`. |

---

## 2. Required status checks (ruleset)

Add a **ruleset** (or branch protection rule) on **`dev`** so merges cannot land
without CI:

| Required check name | Job in `.github/workflows/ci.yml` |
|---|---|
| `verify` | `make verify` |
| `postgres` | `tests/test_p1_nyc.py` against Postgres 16 |
| `docker` | `scripts/smoke.sh` (builds the image, then checks health, the invite gate, and `/metrics`) |
| `e2e` | `make e2e` (Playwright). **Add this as a required check** on `dev` when you next edit the ruleset. |

**Steps (rulesets UI):**

1. **Settings → Rules → Rulesets → New ruleset → New branch ruleset**
2. **Target:** branch `dev` (repeat later for `uat` / `prod` if you want the same bar).
3. **Require pull request before merging** — on.
4. **Require status checks to pass** — add **`verify`**, **`postgres`**, **`docker`**, and **`e2e`** (exact names from the CI workflow job `name:` / check run title). The owner should add `e2e` as a required check; agents do not change the ruleset.
5. **Block force pushes** — on for `dev`.
6. Save. Open a test PR and confirm the checks appear as “required”.

The auto-merge workflow calls `gh pr checks --required --watch`, so it waits only
for checks GitHub marks as required on that branch.

---

## 3. How to merge a PR safely (owner checklist)

Use this instead of approving in the UI when you are happy with the diff and want
CI to finish the merge.

1. Open the PR (same-repo branch only — **fork PRs are ignored** by the workflow).
2. Confirm base branch is **`dev`**.
3. Wait until **verify**, **postgres**, **docker**, and **`e2e`** are green (or let the workflow wait).
4. Add label **`auto-merge`** (repo **collaborators** can add labels; external contributors cannot).
5. The **Auto merge** workflow runs, waits for required checks, then runs  
   `gh pr merge --merge --delete-branch`.
6. Confirm on the PR: merged state, head branch deleted (if “delete head branches” is on).

**To cancel:** remove the `auto-merge` label before the merge step completes (or close the PR).

**Re-runs:** Pushing new commits (`synchronize`) with the label still present re-triggers wait-and-merge after checks pass.

---

## 4. Security notes

| Topic | Policy |
|---|---|
| **Owner approval** | No automatic merge without the **`auto-merge`** label. There is no “auto-approve” step. |
| **Forks** | Workflow runs only when `head.repo` is the same repository (no merge from untrusted forks). |
| **Token scope** | Workflow uses `GITHUB_TOKEN` with `contents: write` (merge and delete the branch), `pull-requests: write`, and `checks`/`statuses: read`, only inside Actions. |
| **Grok / cloud agents** | Do **not** give Grok, Cursor Cloud, or other agents a PAT or app token with `contents: write` or merge rights. They may open PRs and push branches; **only you** add `auto-merge` in the GitHub UI (or via `gh` on your machine). |
| **prod / uat** | Auto-merge targets **`dev` only** by default. Enable stricter human review before extending the workflow to `uat` or `prod`. |

---

## 5. Optional: label create once

If the label does not exist: **Issues → Labels → New label** — name `auto-merge`,
description e.g. “Owner OK to merge when required CI is green”, color of your choice.

---

## 6. Related docs

- [`REVIEW_GUIDE.md`](REVIEW_GUIDE.md) — what to check in a PR before labeling.
- [`AGENTIC_ENGINEERING.md`](AGENTIC_ENGINEERING.md) — build-time CI and auto-merge register row.