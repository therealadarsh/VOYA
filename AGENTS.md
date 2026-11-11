# AGENTS.md: start here (for any AI coding tool)

Read automatically by many AI coding tools. `CLAUDE.md`, `GEMINI.md` and
`.cursor/rules/voya.mdc` point here.

## How this project is run

1. **`docs/PLAN.md` is the single source of truth.** It is written from the
   owner's answers and replaces every earlier prompt or brief. Follow it.
2. **No plan yet?** If `docs/PLAN.md` is missing, don't build anything. Run
   the **kickoff interview** below, then write `docs/PLAN.md` from the
   answers.
3. **Changes go through questions, then the plan.** When the owner gives
   feedback or a new idea:
   - ask any clarifying questions in the chat;
   - update `docs/PLAN.md` (the affected sections plus one dated line in its
     Changelog);
   - then build.
4. **Ask; don't store.**
   - Prompts, question lists, answer files and chat transcripts are never
     written to the repo. They live in the chat only.
   - `.gitignore` blocks the usual names. Don't work around it.
   - The plan records *decisions*, not conversations.
5. **Privacy of the plan.** `docs/PLAN.md` contains business decisions.
   - Commit it only while the GitHub repo is **private**.
   - If you can't confirm that, ask the owner before committing it.
   - Never copy strategy into code comments, commit messages or public docs.

## Kickoff interview (only when `docs/PLAN.md` is missing)

**How to ask:**
- At most 4 questions per message.
- Multiple choice with a recommended option first, plus a free-text option.
- Explain in one line why each question matters.
- Ask follow-ups when an answer is unclear or contradicts an earlier one.
- Stop when every topic below has a decision, or an explicit "decide for me"
  / "later".

**Topics, in order:**
1. **Product and first users:** who it's for and what problem it solves
   (never ask about income; budget only).
2. **MVP features:** what must exist for the owner to test, and what waits.
3. **Platform:** web, installable, native; offline needs.
4. **Launch area:** cities, parks, regions.
5. **Data sources and one-time data budget:** honour each source's terms;
   never scrape where forbidden.
6. **Owner logic: budget fit:** how firm budgets work; what to do with spare
   money.
7. **Owner logic: ranking:** how places are picked.
8. **Owner logic: hidden costs:** which taxes, tips, fees and transport go in
   the total by default.
9. **Accounts:** when to ask for sign-in; age rules; what's paid later.
10. **Runtime AI:** provider and monthly cap.
11. **Hosting:** provider, region, cost alarm.
12. **Law and privacy:** regions served.
13. **Build mode:** autonomous versus checkpoints; who verifies.
14. **Timeline and goal.**
15. **Business model** (may be "later").

**Then write `docs/PLAN.md`** with these sections:
1. Summary.
2. Owner decisions (locked; one subsection per topic).
3. Scope: MVP versus later.
4. Domain model.
5. Features with example input and output.
6. Situations and their expected behaviour.
7. Architecture.
8. Milestones.
9. Definition of done and verification.
10. Changelog.

Show the owner a 10-line summary, and start building only after they say
"go".

## Non-negotiables

- **Never invent prices, fares, taxes, hours or statistics.** Real data needs
  a `source` and `observed_at`; test data is marked `synthetic: true`.
- **Never write the word "guarantee".** Every estimate is labeled "est.".
- **Coordinates at no more than 3 decimal places** anywhere they are stored,
  logged, prompted or sent.
- **The AI proposes; deterministic code computes money, checks the budget and
  applies changes.**
- **Tests use fakes:** no network, no tokens.
- **Secrets only in environment variables** (`.env` is gitignored; see
  `.env.example`). Never commit, log or put keys into prompts or traces.
- **Don't weaken tests to make them pass.**
- **Don't edit `reference/`** (a read-only clone fetched by
  `scripts/fetch_reference.sh`).

## Commands

```sh
uv sync
uv run pytest
```
