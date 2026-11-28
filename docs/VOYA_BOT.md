# VOYA-bot

VOYA-bot is the web crawler for **VOYA**, a budget-first trip planner
([tripvoya.live](https://tripvoya.live)). It helps travelers see what a day
out will cost by reading the opening hours and admission prices that places
publish on their own websites.

**Contact:** smartmeloncode@gmail.com
**Run by:** the VOYA team

## What it reads

- Only the official website of a museum, park, attraction or venue, and only
  pages about visiting: hours, tickets, admission, plan your visit.
- At most 3 pages per site per visit.
- Mainly the machine-readable data many sites already publish for search
  engines (schema.org opening hours and offers).

## What it keeps

- Facts only: opening hours, admission price and currency, or "free".
- The page address, the date it was read, and a short quote (300 characters
  at most) showing where each fact came from.
- It does **not** keep page text, photos, reviews, menus or personal data.

## How it behaves

- It follows your `robots.txt`. To block it, add:

  ```text
  User-agent: VOYA-bot
  Disallow: /
  ```

- One request every 10 seconds per site at most, with a 15-second timeout.
- It identifies itself as
  `VOYA-bot/0.1 (+https://github.com/therealadarsh/VOYA/blob/dev/docs/VOYA_BOT.md)`.
- It only visits sites a person at VOYA has reviewed first, including the
  site's terms of use.
- It checks a site again about once a month, to keep prices current.

## Opting out or correcting a price

Email smartmeloncode@gmail.com with your website's address. We reply to
confirm the request comes from your site, then stop crawling it. Facts we
stored from your site are removed within 6 months of that confirmation. If
a price or opening time VOYA shows is wrong, send the correct one and we
will fix it.

VOYA always shows prices as estimates, with the source and the date they
were checked, and links travelers to your website.
