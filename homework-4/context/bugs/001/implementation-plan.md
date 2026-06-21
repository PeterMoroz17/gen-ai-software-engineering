# Implementation Plan — Bookmark Manager CLI (Bug 001)

**Author**: Bug Planner  
**Date**: 2026-06-20  
**Status**: Ready to execute  
**Test command**: `npm test`

---

## Overview

Three confirmed bugs will be fixed across two files. All fixes are low-risk, localized changes that do not affect the API surface or data structures.

| Bug | Severity | File | Root Cause | Fix Strategy |
|-----|----------|------|-----------|--------------|
| Pagination off-by-one | Medium | `src/bookmarks.js` | `slice()` end index is one short | Remove `-1` from slice range |
| Remove by ID type mismatch | High | `src/index.js` | CLI arg is string, ID is numeric | Convert arg to number at call site |
| Command injection in checkUrlReachable | Critical | `src/bookmarks.js` | Unescaped shell interpolation | Validate host with regex; use `execFile` with argument array |

---

## Fix 1: Pagination Off-by-One (`src/bookmarks.js:15`)

**Problem**: `listBookmarks` returns one fewer item per page than requested because `slice()` receives an exclusive end index that is one position too early.

**File**: `src/bookmarks.js`

**Before** (line 15):
```javascript
function listBookmarks(list, page = 1, pageSize = 10) {
  const start = (page - 1) * pageSize;
  return list.slice(start, start + pageSize - 1);
}
```

**After** (line 15):
```javascript
function listBookmarks(list, page = 1, pageSize = 10) {
  const start = (page - 1) * pageSize;
  return list.slice(start, start + pageSize);
}
```

**Rationale**: The `slice(start, end)` method returns elements from index `start` up to (but not including) index `end`. For a page of size 10 starting at index 0, the range should be `slice(0, 10)` to include indices 0–9. The `-1` made the range `slice(0, 9)`, excluding index 9 and returning only 9 items.

**Test command after change**: `npm test`

---

## Fix 2: Remove by ID Type Mismatch (`src/index.js:42`)

**Problem**: The CLI argument is a string, but bookmarks store numeric IDs. The strict inequality `!==` comparison always fails, so no bookmark is ever removed.

**File**: `src/index.js`

**Before** (lines 41–46):
```javascript
case "remove": {
  const id = args[0];
  const updated = removeBookmark(bookmarks, id);
  saveBookmarks(updated);
  console.log(`Removed bookmark #${id} (now ${updated.length} remaining)`);
  break;
}
```

**After** (lines 41–46):
```javascript
case "remove": {
  const id = Number(args[0]);
  const updated = removeBookmark(bookmarks, id);
  saveBookmarks(updated);
  console.log(`Removed bookmark #${id} (now ${updated.length} remaining)`);
  break;
}
```

**Rationale**: Convert the string argument to a number before passing to `removeBookmark`, matching the type of the stored numeric ID. This follows the same pattern already used in the `list` case (`const page = Number(args[0]) || 1`).

**Test command after change**: `npm test`

---

## Fix 3: Command Injection in `checkUrlReachable` (`src/bookmarks.js`)

**Problem**: The host is interpolated directly into a shell command without validation, allowing command injection via shell metacharacters.

**Files**: `src/bookmarks.js` (lines 1 and 26–31)

### Step 3a: Update the import statement

**Before** (line 1):
```javascript
const { exec } = require("child_process");
```

**After** (line 1):
```javascript
const { execFile } = require("child_process");
```

**Rationale**: Use `execFile` instead of `exec` to avoid spawning a shell. `execFile` executes a program directly with arguments as an array, preventing shell interpretation of metacharacters.

### Step 3b: Update the `checkUrlReachable` function

**Before** (lines 26–31):
```javascript
function checkUrlReachable(url, callback) {
  const host = extractHost(url);
  exec(`ping -n 1 ${host}`, (error, stdout) => {
    callback(error ? false : true, stdout);
  });
}
```

**After** (lines 26–35):
```javascript
function checkUrlReachable(url, callback) {
  const host = extractHost(url);
  // Validate host to prevent command injection
  const hostPattern = /^[a-zA-Z0-9.-]+(?::\d+)?$/;
  if (!hostPattern.test(host)) {
    callback(false);
    return;
  }
  execFile("ping", ["-n", "1", host], (error, stdout) => {
    callback(error ? false : true, stdout);
  });
}
```

**Rationale**: 
1. Add host validation with a strict regex that allows only alphanumeric characters, dots, hyphens, and optional port numbers. This whitelist blocks all shell metacharacters (`;`, `|`, `$`, backticks, `&`, `>`, `<`, etc.).
2. Return early with `callback(false)` if the host fails validation.
3. Use `execFile("ping", ["-n", "1", host], ...)` instead of `exec()` to pass arguments as an array, preventing shell interpretation even if the regex validation is bypassed.

**Test command after change**: `npm test`

---

## Execution Checklist

- [ ] Apply Fix 1: Remove `-1` from `listBookmarks` slice (src/bookmarks.js:15)
- [ ] Apply Fix 2: Add `Number()` conversion to remove command (src/index.js:42)
- [ ] Apply Fix 3a: Update `child_process` import to use `execFile` (src/bookmarks.js:1)
- [ ] Apply Fix 3b: Add host validation and use `execFile` in `checkUrlReachable` (src/bookmarks.js:26–35)
- [ ] Run `npm test` to verify all fixes
- [ ] Verify no test regressions

---

## Expected Test Results

After all fixes are applied, the test suite should:
- ✓ Pass pagination tests (all items on a page are returned)
- ✓ Pass removal tests (bookmarks are successfully removed by ID)
- ✓ Pass security tests (command injection attempts are blocked; valid hosts are reachable)
- ✓ No breaking changes to existing functionality

