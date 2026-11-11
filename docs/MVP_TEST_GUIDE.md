# MVP test guide

Run `make run` and open http://localhost:8000 (a phone-sized window works
best).

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
- **Emailed magic links:** sign-in returns a token directly in dev mode.
- **Receipt photos, community price sharing, rewards, ads/subscriptions,
  native app, other currencies and languages.**
- **Deployment:** runs locally; see the plan for AWS.

## Reporting feedback
Note what you tried, what you expected, and what happened. A trace ID (the
`X-Trace-Id` response header) lets the exact request be replayed.
