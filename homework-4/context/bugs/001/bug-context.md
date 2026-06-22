# Bug Report — Bookmark Manager CLI

**Reported by**: QA / users
**Affected app**: `src/` (Bookmark Manager CLI)
**Priority**: High

## Symptom 1 — Pagination drops the last bookmark on every page

When listing bookmarks with `node src/index.js list <page> <pageSize>`, the last
bookmark of every page is missing from the output, even though it clearly exists
in `data/bookmarks.json`. Confirmed by adding 10 bookmarks and listing page 1 with
page size 10 — only 9 show up.

## Symptom 2 — Removing a bookmark by id never works

Running `node src/index.js remove <id>` (with an id printed by the `list` or `add`
command) always reports the bookmark as "removed" but the bookmark count does not
change and the bookmark is still present afterwards. This happens for every id,
every time.

## Symptom 3 — Possible security issue in the "check URL" feature

The `check` command (`node src/index.js check <url>`) is meant to ping a host to
see if it's reachable. A security-conscious teammate flagged that the command
appears to build a shell command directly from the URL the user types in, which
looks like it could allow arbitrary command execution if a malicious URL/string is
passed in (e.g. something containing `&` or `;`). This needs to be confirmed and
fixed if real.

## Ask

Please investigate the codebase, confirm root causes for symptoms 1 and 2, confirm
or refute the security concern in symptom 3, and produce a fix.
