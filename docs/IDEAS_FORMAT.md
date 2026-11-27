# Idea bank format

Edit `data/ideas/<area>.json` by hand. NYC is `data/ideas/nyc.json`.
The shipped NYC file is a **sample**. Replace it with your own picks when you
have them. Leave `curated_by` as `"sample"` until a pick is yours, then set
`"owner"`.

The file has no prices, hours, or statistics. A plan line gets a cost only
when the pick maps to a cited place. Until then the app shows "price not yet
checked".

## Top of the file

| Field | What to write |
|---|---|
| `synthetic` | `true` while the list is a sample. `false` only when every pick is yours and the `source`, `observed_at`, and `quote` describe that list. |
| `source` | Where the list came from, in one sentence. |
| `observed_at` | When you wrote it, as an ISO 8601 time with a timezone. |
| `quote` | A short line you can stand behind. No prices. |
| `area` | `nyc` for New York. The file name matches this. |
| `note` | Required while `synthetic` is true. The sample says `Sample; owner replaces with their own picks`. |
| `days` | Keys `"1"` through `"7"`. |

## A day

Each day has `morning`, `afternoon`, and `evening`. Each of those has
`options`: at least 2 and at most 6.

```json
"morning": {
  "options": [
    {
      "id": "nyc-d1-mo-bridge",
      "title": "Brooklyn Bridge walk",
      "place_ref": null,
      "tags": ["walk"],
      "indoor": false,
      "duration_min": 90,
      "why": "A walk across the Brooklyn Bridge.",
      "curated_by": "sample"
    }
  ]
}
```

| Field | Rule |
|---|---|
| `id` | Stable, unique in the file. Do not reuse an id for a different place. |
| `title` | The name a traveler sees. |
| `place_ref` | A catalog or places id, or `null`. The same place is not scheduled twice on one trip. |
| `tags` | Short words, a list. |
| `indoor` | `true` or `false`. |
| `duration_min` | A positive whole number of minutes for the sample length. |
| `why` | One sentence. |
| `curated_by` | `"sample"` or `"owner"`. |

Do not add `price`, `cost`, `fare`, `hours`, `rating`, or a coordinate with more
than 3 decimal places. `make verify` checks this file.

A new plan picks one option per slot from the plan id, so reloading shows the
same picks. **Another** on one slot moves only that slot.
