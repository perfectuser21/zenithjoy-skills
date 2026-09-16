# Report Contract

## Atomic Evidence Schema

Use one line per verified item:

`Evidence ID | Source | Observed at | Owner | Object | Status | Delta | Blocker | Next action | Evidence reference`

Evidence IDs use the report date and a short sequence, for example `E-20260821-001`.

## Capability Line Schema

`Capability ID | Status | Evidence IDs | Yesterday/result | Current state | Today/next | Owner | Freshness | Confidence`

Do not hide individual red or amber work items inside prose. List them beneath the capability line.

## Value Stream Schema

For each Value Stream, state:

- status and affected Capability IDs
- value produced or blocked
- flow constraint
- next measurable transition

## Portfolio Schema

For each Portfolio, state:

- status and affected Value Streams
- outcome movement
- largest risk
- decision or resource need

## Company Conclusion

Write last and keep it to:

1. Overall state and why, citing Portfolio/Capability IDs.
2. Three most important outcomes since the previous report.
3. Three highest-priority actions for today.
4. Decisions required from the owner.
5. Data-quality gaps that reduce confidence.

## Output Order

1. Header: date, cutoff, evidence window, data completeness.
2. Evidence Ledger.
3. Capability Lines grouped by Value Stream.
4. Value Stream rollups.
5. Portfolio rollups.
6. Company Conclusion.

This order is mandatory. The report may provide navigation links, but it must not move the executive conclusion above its supporting layers.
