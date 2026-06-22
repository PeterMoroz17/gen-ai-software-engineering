# Implementation Plan — Bookmark Manager CLI (Bug 001)

**Planner**: Bug Planner  
**Date**: 2026-06-22  
**Verified Research**: `context/bugs/001/research/verified-research.md` (Excellent quality)  
**Test Command**: `npm test`

---

## Overview

Three confirmed bugs will be fixed across two source files. All fixes are low-risk, localized changes with no API surface or data structure changes.

| Bug | Severity | Root Cause | Fix Location | Strategy |
|-----|----------|-----------|--------------|----------|
| Pagination off-by-one | Medium | `slice()` end index off by one | `src/bookmarks.js:15` | Remove `-1` from slice range |
| Remove by ID type mismatch | High | String CLI arg vs numeric bookmark ID | `src/bookmarks.js:19` | Convert string ID to number before comparison |
| Command injection in checkUrlReachable | Critical | Unescaped shell interpolation of user input | `src/bookmarks.js` (lines 1, 26–31) | Validate host with regex; switch from `exec` to `execFile` with array arguments |

---

## Fix 1: Pagination Off-by-One

**File**: `src/bookmarks.js`  
**Location**: Line 15  
**Symptom**: Returning `pageSize - 1` items per page instead of `pageSize` (last item dropped each page)

### Before
```javascript
function listBookmarks(list, page = 1, pageSize = 10) {
  const start = (page - 1) * pageSize;
  return list.slice(start, start + pageSize - 1);
}
```

### After
```javascript
function listBookmarks(list, page = 1, pageSize = 10) {
  const start = (page - 1) * pageSize;
  return list.slice(start, start + pageSize);
}
```

**Rationale**: The `slice(start, end)` method returns elements from index `start` up to (but not including) index `end`. The `- 1` makes the end index exclusive by one too many positions. For page 1 with size 10, `slice(0, 10)` includes indices 0–9 (10 items); the original `slice(0, 9)` includes only 0–8 (9 items). Removing the `- 1` restores the correct range.

**Test after**: `npm test` — verify pagination tests return exactly `pageSize` items per page.

---

## Fix 2: Remove by ID Type Mismatch

**File**: `src/bookmarks.js`  
**Location**: Line 19  
**Symptom**: Removing a bookmark by ID never works; the filter always returns the unchanged list

### Before
```javascript
function removeBookmark(list, id) {
  return list.filter((bookmark) => bookmark.id !== id);
}
```

### After
```javascript
function removeBookmark(list, id) {
  return list.filter((bookmark) => bookmark.id !== Number(id));
}
```

**Rationale**: The `id` parameter is a string (passed from `process.argv.slice(2)` in `src/index.js:23`). The `bookmark.id` is numeric (set as a number in `addBookmark()` and preserved from JSON). The strict inequality `!==` comparison always evaluates to `true` when comparing a number to a string (e.g., `5 !== "5"` is `true`). Converting `id` to a number with `Number(id)` makes the types match, so the comparison works correctly: `5 !== 5` is `false` (the bookmark is filtered out).

**Test after**: `npm test` — verify that removing a bookmark by ID actually removes it and decrements the list length.

---

## Fix 3: Command Injection in checkUrlReachable

**File**: `src/bookmarks.js`  
**Locations**: Line 1 (import) and lines 26–31 (function)  
**Symptom**: Host from user input (URL) is interpolated directly into shell command; shell metacharacters (`; $ | & > <` backticks, etc.) are interpreted as commands

### Step 3a: Update Import Statement

**Before** (line 1):
```javascript
const { exec } = require("child_process");
```

**After** (line 1):
```javascript
const { execFile } = require("child_process");
```

**Rationale**: `execFile` executes a program directly without spawning a shell, so it treats all arguments as literal strings. This prevents shell interpretation of metacharacters.

### Step 3b: Update checkUrlReachable Function

**Before** (lines 26–31):
```javascript
function checkUrlReachable(url, callback) {
  const host = extractHost(url);
  exec(`ping -n 1 ${host}`, (error, stdout) => {
    callback(error ? false : true, stdout);
  });
}
```

**After** (lines 26–34):
```javascript
function checkUrlReachable(url, callback) {
  const host = extractHost(url);
  // Validate host to prevent command injection: allow only alphanumeric, dots, hyphens, colons
  if (!/^[a-zA-Z0-9.\-:]+$/.test(host)) {
    callback(false);
    return;
  }
  execFile("ping", ["-n", "1", host], (error, stdout) => {
    callback(error ? false : true, stdout);
  });
}
```

**Rationale**:
1. **Host validation regex** `/^[a-zA-Z0-9.\-:]+$/` restricts the host to safe characters: alphanumerics, dots (domain names), hyphens (subdomains), colons (IPv6 ports). This whitelist blocks all shell metacharacters and command-injection attempts like `example.com; rm -rf /` or `example.com$(cat /etc/passwd)`.
2. **Early return on invalid host**: If validation fails, return immediately with `callback(false)` to avoid executing ping with malicious input.
3. **execFile with array arguments**: Replace `exec()` with `execFile("ping", ["-n", "1", host], ...)`. The arguments are passed as an array, not interpolated into a shell string, so even if regex validation is somehow bypassed, shell interpretation cannot occur.

**Test after**: `npm test` — verify that valid hosts pass the check and malicious hosts (e.g., `example.com; whoami`) are rejected.

---

## Execution Steps

1. **Apply Fix 1**: In `src/bookmarks.js` line 15, change `start + pageSize - 1` to `start + pageSize`.
2. **Apply Fix 2**: In `src/bookmarks.js` line 19, change `bookmark.id !== id` to `bookmark.id !== Number(id)`.
3. **Apply Fix 3a**: In `src/bookmarks.js` line 1, change `const { exec }` to `const { execFile }`.
4. **Apply Fix 3b**: In `src/bookmarks.js` lines 26–31, replace the entire `checkUrlReachable` function with the validated version using `execFile`.
5. **Run tests**: Execute `npm test` to verify all fixes.

---

## Expected Test Results

After all fixes are applied:
- ✓ **Pagination tests pass**: `listBookmarks()` returns exactly `pageSize` items per page, including the last item.
- ✓ **Removal tests pass**: `removeBookmark()` successfully removes bookmarks by numeric ID when passed a string ID.
- ✓ **Security tests pass**: `checkUrlReachable()` accepts valid hostnames/IPs but rejects malicious input containing shell metacharacters.
- ✓ **No regressions**: Existing functionality remains unchanged.

---

## Code Changes Summary

**File**: `src/bookmarks.js`  
**Lines changed**: 1, 15, 19, 26–34 (8 lines total, including new validation lines in function)  
**Risk level**: Low (all changes are localized, no API changes, no data structure changes)
