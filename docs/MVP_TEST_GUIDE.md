# MVP test guide

Run `make run` and open http://localhost:8000 (a phone-sized window works
best). For a production-shaped check, use `scripts/smoke.sh` (it needs Docker)
and, after a deploy, the list at the bottom.

## Checks before you click around

```sh
make verify RUN=
make e2e RUN=
bash scripts/smoke.sh
```

`make verify` skips the browser. `make e2e` installs Chromium if it is missing,
then plans New York, presses Another on one slot, saves, signs in, logs a
spend, asks the built-in helper, sends feedback, and opens Privacy, Terms, and
the invite gate. It runs at a phone width and a desktop width. `scripts/smoke.sh`
builds the image. If Docker is not running it says so and stops.

## Try these
1. **A tight day:** Chicago, 1 day, $150, 2 adults, Food + Architecture,
   "Some wiggle room". Look at "You could keep about $…", the hidden-cost line
   and the range bars.
2. **Hard limit versus wiggle room:** plan the same trip both ways. A hard
   limit plans more cautiously.
3. **Too little money:** New York, 2 days, $200. VOYA says how much more is
   needed and suggests free ideas.
4. **Worth it?:** New York, 2 days, $700, booked lodging $0, Art + Views. Add
   an upgrade, then Undo.
5. **Around a fixed plan:** San Francisco, a "Ball game" at 13:00 for 3 hours
   costing $90. The day fills in around it.
6. **Day trip:** Indiana Dunes, starting from Chicago by train. Toggle
   "Include" on the getting-there card.
7. **Ask VOYA:** "It's raining, what now?", "Make it $20 cheaper", "Find
   something I'd like", "Why is dinner so expensive?". Apply an option, then
   Undo.
8. **Discover:** from Chicago, $120. Then "Plan this" on a card.
9. **Track spend:** Save trip, sign in (any email, 18+), log a big lunch
   against a stop, and watch the status and "Ways to get back under".
10. **Memory and data:** Remember, Forget, Export, Delete my data.

## Intentionally missing in the MVP
- **Real price data:** the demo catalog is synthetic.
- **Live email:** development sign-in returns a token. Production
  (`VOYA_DEV_SIGNIN=0` plus SMTP settings) sends a magic link. The SMTP
  account is not configured in this repo.
- **Receipt photos, community price sharing, rewards, ads/subscriptions,
  native app, other currencies and languages.**
- **A live host:** the container and [`docs/DEPLOY.md`](DEPLOY.md) are ready.
  Deploying needs the owner's hosting account.

## Classic picks

Plan New York for one day. Under the priced lines, **Classic picks** shows a
morning, an afternoon, and an evening. Press **Another** on one of them. Only
that slot should change. The picks say the price is not yet checked. They do
not change the est. total.

## After a deploy

1. Open `/healthz` and `/readyz`. Both should say ok.
2. Open `/privacy`. It should load without the invite code.
3. Open the site. A wrong invite code is refused. The real code shows the planner.
4. Plan New York. You should see **est.**, **Demo prices**, **Preview**, and **Classic picks**.
5. Ask whoever runs the host to confirm `/metrics` is 401 without the metrics token.

## Reporting feedback
Note what you tried, what you expected, and what happened. A trace ID (the
`X-Trace-Id` response header) lets the exact request be replayed.
