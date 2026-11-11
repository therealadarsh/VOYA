# AGENTS.md: start here (for any AI coding tool)

Read automatically by many AI coding tools. `CLAUDE.md`, `GEMINI.md` and
`.cursor/rules/voya.mdc` point here.

## Read first, in this order
1. `docs/PROGRESS.md`: what's done, what's next, what's blocked.
2. The last 2 entries of `docs/SESSION_LOG.md`: what the previous session did.
3. `.voya-private/PLAN.md` and `.voya-private/CURSOR_PROMPT.md`, if present:
   the owner's plan and build brief. This folder is **gitignored and local
   only**.
4. `DECISIONS.md`, `docs/CONCEPT_MAP.md`, `README.md`.

## The private folder (`.voya-private/`)
- It holds the owner's plan, business decisions, prompts and private notes.
- **Never commit it, and never copy its contents into tracked files, commit
  messages or code comments.** The GitHub repo may be public.
- **If `PLAN.md` is missing,** don't build. Run the kickoff interview below
  in the chat, then write `.voya-private/PLAN.md` from the answers.
- **When the owner gives feedback or new ideas:**
  - ask clarifying questions in the chat (at most 4 at a time, each with a
    recommended option);
  - update `.voya-private/PLAN.md` and add one dated line to its Changelog;
  - then build.
- Prompts, question lists, answers and transcripts never go in tracked files.
  `.gitignore` blocks the usual names; don't work around it.

## Session logging (mandatory)
Do this at the end of every session, before stopping for any reason (task
done, the owner says stop, about to hit a context or usage limit, handing
off to another tool):
1. **Append an entry to `docs/SESSION_LOG.md`** using its template. Keep it
   technical; no business strategy.
2. **Update `docs/PROGRESS.md`:** Done / Known limits / Next / Blocked, plus
   the "Last updated" line (date, branch, commit).
3. **Update the "Status" line in `README.md`** so it matches PROGRESS.md.
4. **Optional:** a private session summary (strategy, the owner's ideas) in
   `.voya-private/SESSION_NOTES.md`.
5. Commit with the message `log: session summary <date>` and push.

If you're close to a limit, write the log **first**, then continue.

## Kickoff interview (only when `.voya-private/PLAN.md` is missing)
Ask in the chat, at most 4 questions per message, each multiple choice with a
recommended option. Never ask about income.

**Topics:**
1. Product and first users.
2. MVP features.
3. Platform.
4. Launch area.
5. Data sources and budget (terms first; no forbidden scraping).
6. Budget-fit logic.
7. Ranking.
8. Hidden costs.
9. Accounts and age rules.
10. Runtime AI and its cap.
11. Hosting.
12. Law and privacy.
13. Build mode.
14. Timeline.
15. Business model (may be "later").

Then write the plan, show a 10-line summary, and wait for "go".

## Non-negotiables
- **Never invent prices, fares, taxes, hours or statistics.** Real data needs
  a `source` and `observed_at`; test data is marked `synthetic: true`.
- **Never write the word "guarantee".** Every estimate is labeled "est.".
- **Coordinates at no more than 3 decimal places** anywhere they are stored,
  logged, prompted or sent.
- **The AI proposes; deterministic code computes money, checks the budget and
  applies changes.**
- **Follow every data source's terms.** No scraping of sites whose terms
  forbid it. Cache only what the terms allow, and record that in
  `docs/DATA_SOURCES.md`.
- **Tests use fakes:** no network, no tokens.
- **Secrets only in environment variables** (`.env` is gitignored; see
  `.env.example`). Never commit, log or put keys into prompts or traces.
- **Don't weaken tests to make them pass.**
- **Don't edit `reference/`** (a read-only clone fetched by
  `scripts/fetch_reference.sh`).

## Commands
```sh
uv sync
make run     # http://localhost:8000
make test
```
