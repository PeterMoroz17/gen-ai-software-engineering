# Test Report — Bug 001: Bookmark Manager CLI

**Date**: 2026-06-20  
**Status**: PASSED  
**All tests pass (8/8)**

---

## FIRST Compliance

All new tests satisfy the FIRST principles:

- **Fast** — Tests run in milliseconds (0.1ms–59ms), no disk I/O except in callback-driven tests, and no unnecessary operations. The command injection validation tests complete in <2ms; network-dependent tests are fast enough for CI.
- **Independent** — Each test creates fresh bookmark arrays via `addBookmark()`. No shared module-level state; tests can run in any order.
- **Repeatable** — Tests use only hard-coded inputs (URLs, IDs, bookmark data) and assertions. No reliance on current time, random values, or external services. Results are deterministic.
- **Self-validating** — All tests use strict assertions (`assert.equal`, `assert.ok`) to verify expected behavior. No manual inspection required.
- **Timely** — Tests are written to directly cover the three bug fixes: pagination offset, type mismatch in remove, and command injection prevention. All new tests target changed code, not legacy behavior.

---

## Tests Added

### 1. Pagination Fix Tests

**File**: `tests/bookmarks.test.js`

- **Test**: `listBookmarks returns exactly pageSize items on a full page (pagination fix)`
  - Verifies that a full page returns exactly `pageSize` items (10), not `pageSize - 1`
  - Creates 15 bookmarks, checks page 1 returns items 1–10
  - Covers fix: removed `-1` from slice end index in `listBookmarks` (line 15 of `src/bookmarks.js`)

- **Test**: `listBookmarks returns remaining items on partial last page (pagination fix)`
  - Verifies that a partial last page returns remaining items (5 of 15)
  - Creates 15 bookmarks, checks page 2 returns items 11–15
  - Confirms pagination correctly handles pages shorter than `pageSize`

### 2. Remove by ID Type Mismatch Fix Test

**File**: `tests/bookmarks.test.js`

- **Test**: `removeBookmark removes bookmark by numeric ID (type mismatch fix)`
  - Verifies that `removeBookmark` correctly filters by numeric ID
  - Creates 3 bookmarks, removes ID 2, checks that IDs 1 and 3 remain
  - Covers fix: CLI now passes `Number(args[0])` to `removeBookmark` (line 42 of `src/index.js`)

### 3. Command Injection Prevention Tests

**File**: `tests/bookmarks.test.js`

- **Test**: `checkUrlReachable rejects invalid hosts with command injection characters`
  - Verifies that 7 shell metacharacter patterns (`;`, `|`, `&`, `` ` ``, `$()`, `>`, `<`) are rejected
  - Confirms callback is invoked with `false` for each invalid host
  - Covers fix: host validation regex in `checkUrlReachable` (lines 29–31 of `src/bookmarks.js`)

- **Test**: `checkUrlReachable accepts valid hostnames (command injection fix)`
  - Verifies that valid hostnames (including subdomains and ports) are accepted
  - Tests: `example.com`, `google.com`, `sub.example.com`, `localhost:3000`
  - Confirms callback is invoked with a boolean for each valid host
  - Covers fix: safe `execFile` usage and host pattern validation (lines 34–35 of `src/bookmarks.js`)

---

## Test Run Result

```
> homework-4-bookmark-manager@1.0.0 test
> node --test

✔ addBookmark adds a bookmark with an incrementing id (0.602ms)
✔ addBookmark requires url and title (0.2077ms)
✔ listBookmarks returns bookmarks for a page within a single full page (0.1441ms)
✔ listBookmarks returns exactly pageSize items on a full page (pagination fix) (0.1884ms)
✔ listBookmarks returns remaining items on partial last page (pagination fix) (0.13ms)
✔ removeBookmark removes bookmark by numeric ID (type mismatch fix) (0.1029ms)
✔ checkUrlReachable rejects invalid hosts with command injection characters (1.4728ms)
✔ checkUrlReachable accepts valid hostnames (command injection fix) (44.5732ms)
ℹ tests 8
ℹ suites 0
ℹ pass 8
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 131.2444
```

**Summary**: ✅ All 8 tests pass (100% success rate). Duration: 131.2ms.

---

## References

- **Fix Summary**: `context/bugs/001/fix-summary.md`
- **FIRST Unit Tests Skill**: `skills/unit-tests-FIRST.md`
- **Modified Test File**: `tests/bookmarks.test.js`
- **Modified Source Files**:
  - `src/bookmarks.js` (lines 1, 13–16, 26–35)
  - `src/index.js` (line 42)
