const test = require("node:test");
const assert = require("node:assert/strict");
const { addBookmark, listBookmarks, removeBookmark, checkUrlReachable, extractHost } = require("../src/bookmarks");

test("addBookmark adds a bookmark with an incrementing id", () => {
  const list = [];
  const b1 = addBookmark(list, { url: "https://a.com", title: "A" });
  const b2 = addBookmark(list, { url: "https://b.com", title: "B" });
  assert.equal(list.length, 2);
  assert.equal(b1.id, 1);
  assert.equal(b2.id, 2);
});

test("addBookmark requires url and title", () => {
  const list = [];
  assert.throws(() => addBookmark(list, { url: "", title: "A" }));
});

test("listBookmarks returns bookmarks for a page within a single full page", () => {
  const list = [];
  addBookmark(list, { url: "https://a.com", title: "A" });
  addBookmark(list, { url: "https://b.com", title: "B" });
  const page = listBookmarks(list, 1, 10);
  assert.ok(page.length > 0);
  assert.equal(page[0].title, "A");
});

test("listBookmarks returns exactly pageSize items on a full page (pagination fix)", () => {
  const list = [];
  for (let i = 0; i < 15; i++) {
    addBookmark(list, { url: `https://example${i}.com`, title: `Title ${i}` });
  }
  const page = listBookmarks(list, 1, 10);
  assert.equal(page.length, 10, "First page should return exactly 10 items");
  assert.equal(page[0].id, 1);
  assert.equal(page[9].id, 10);
});

test("listBookmarks returns remaining items on partial last page (pagination fix)", () => {
  const list = [];
  for (let i = 0; i < 15; i++) {
    addBookmark(list, { url: `https://example${i}.com`, title: `Title ${i}` });
  }
  const page = listBookmarks(list, 2, 10);
  assert.equal(page.length, 5, "Second page should return remaining 5 items");
  assert.equal(page[0].id, 11);
  assert.equal(page[4].id, 15);
});

test("removeBookmark removes bookmark by numeric ID (type mismatch fix)", () => {
  const list = [];
  addBookmark(list, { url: "https://a.com", title: "A" });
  addBookmark(list, { url: "https://b.com", title: "B" });
  addBookmark(list, { url: "https://c.com", title: "C" });
  const updated = removeBookmark(list, 2);
  assert.equal(updated.length, 2);
  assert.equal(updated[0].id, 1);
  assert.equal(updated[1].id, 3);
  assert.ok(!updated.some((b) => b.id === 2), "Bookmark with id 2 should be removed");
});

test("checkUrlReachable rejects invalid hosts with command injection characters", (t, done) => {
  const invalidHosts = [
    "https://example.com;ls",
    "https://example.com|cat /etc/passwd",
    "https://example.com&whoami",
    "https://example.com`whoami`",
    "https://example.com$(whoami)",
    "https://example.com>output.txt",
    "https://example.com<input.txt",
  ];

  let completed = 0;
  invalidHosts.forEach((url) => {
    checkUrlReachable(url, (reachable) => {
      assert.equal(reachable, false, `URL ${url} should be rejected`);
      completed++;
      if (completed === invalidHosts.length) {
        done();
      }
    });
  });
});

test("checkUrlReachable accepts valid hostnames (command injection fix)", (t, done) => {
  const validHosts = [
    "https://example.com",
    "https://google.com",
    "https://sub.example.com",
    "https://localhost:3000",
  ];

  let completed = 0;
  validHosts.forEach((url) => {
    checkUrlReachable(url, (reachable) => {
      assert.ok(typeof reachable === "boolean", `URL ${url} should return a boolean`);
      completed++;
      if (completed === validHosts.length) {
        done();
      }
    });
  });
});
