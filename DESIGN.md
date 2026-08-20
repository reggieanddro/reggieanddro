# DESIGN.md — Tombstone Classified

utc: 2026-08-20
authority: Jesse Niesen · FDE · USMC · TX DSHS #690
mode: Experience (profile) / Persuade (crisis skin)
anti-reference: aicrisiscoach.com AI-coaching brochure (live 2026-08-20). Blurple, gradients, Inter+Bebas "I Fix It" SaaS.

## Tokens
```
--bg: #0a0a0a
--fg: #eaeaea
--line: #2a2a2a
--muted: #777777
--accent: #c9ff3f
font: ui-monospace, "JetBrains Mono", "IBM Plex Mono", monospace
border: 1px solid var(--line)
radius: 0
gradient: BAN
purple/blurple/#6366f1/#7c3aed/#8b5cf6: BAN
```

## First viewport (order, no prose)
1. Identity one-liner (FDE, not coach)
2. GitHub graph / streak (jn skin only)
3. Tombstone grid (pinned Worlds = router)
4. Receipts slot (video or terminal). Claims without a path are omitted.

## Skins
| id | host | worlds shown |
|---|---|---|
| `acc` | aicrisiscoach.com | Deal Room, Liv Hana, Book |
| `jn` | jesseniesen.com | all 7 |
| `rad` | github.com/reggieanddro README | markdown table = same 7 |

`?skin=jn` or `data-skin="jn"`. Do not fork layout.

## Copy law
- FDE: 25+ years paying programmers → shipping own. Front line of TX hemp market.
- ≈14,000 = **licensed consumable-hemp retail stores** (KERA / Texas Tribune Aug 2026). THC ban live/in court. **Do not print “14k businesses burned.”**
- D8: no OpenRouter in this ship.

## Proof commands
```
grep -Ei 'gradient|#6366f1|#7c3aed|#8b5cf6' index.html | wc -l   # 0
grep -c 'class="tab"' index.html                                   # >= 1
python3 -c "import json; print(len(json.load(open('worlds.json'))))"  # 7
```
