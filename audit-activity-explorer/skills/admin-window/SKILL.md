---
name: admin-window
description: Read a long Kiteworks admin-log period safely. Splits it into 30-day windows, pages each window, paces calls, caps rows per run and reports how far back the log really reaches.
metadata:
  version: "0.1.0"
---

# Admin window

## When to use

Use this skill whenever a report needs `get_admin_activity` over a period longer than one call can answer, up to 12 months. The server answers 422 for a window longer than 30 days, and `searchText` answers 403, so all filtering happens on the rows after they are read.

## Windows

- A window is at most 30 days. Split the period into adjacent windows: the next start equals the previous end.
- Read oldest first. The union of the windows is exactly the requested period.
- Always pass both `startDateTime` and `endDateTime`.
- A row on a window boundary can appear twice. Count it once, keyed on `created`, `eventName`, `userId` and `description`.

## Paging

- Use `limit` 10000 (the server maximum; a smaller limit truncates without a `hasMore` flag) and step `offset` by the number of rows returned.
- Stop a window when a page returns fewer than `limit` rows.
- The answer carries `total`. When the rows read for a window are fewer than `total`, the window is truncated: mark it partial and say so in the limitations.

## Pacing

- One call per 3 seconds per method. Calls are sequential, never parallel.
- On "method rate limit reached", wait about 5 seconds and retry that call once. If it fails again, mark that window partial and continue with the next one.
- `search_users` pages 50 per page with `hasMore`; the same pacing applies.

## Row cap

- The default cap is 50000 rows per run.
- When the cap is reached, stop reading and state "row cap reached at N rows" in the report.

## Reach

Report the oldest `created` value actually returned, never the requested start. If the log holds less history than asked for, the reach shows it.

## Method and limits

The report prints these fields:

- windows run
- windows partial
- rows read
- cap hit
- oldest row
- rows with `data: {}` (rows about other users' objects carry empty data)

## Connector tools this skill uses

Calls: `get_admin_activity`

Named only: `search_users`

## Scripted callers

`scripts/admin_window.py` holds the same rules as pure functions for scripts (window splitting, call arguments, pacing, row cap, reach, summary). Example: `python scripts/admin_window.py windows --start 2026-07-01T00:00:00Z --end 2026-10-01T00:00:00Z`.
