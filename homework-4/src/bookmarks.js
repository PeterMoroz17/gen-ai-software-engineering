const { execFile } = require("child_process");

function addBookmark(list, { url, title }) {
  if (!url || !title) {
    throw new Error("Both url and title are required");
  }
  const nextId = list.length > 0 ? Math.max(...list.map((b) => b.id)) + 1 : 1;
  const bookmark = { id: nextId, url, title };
  list.push(bookmark);
  return bookmark;
}

function listBookmarks(list, page = 1, pageSize = 10) {
  const start = (page - 1) * pageSize;
  return list.slice(start, start + pageSize);
}

function removeBookmark(list, id) {
  return list.filter((bookmark) => bookmark.id !== Number(id));
}

function extractHost(url) {
  return url.replace(/^https?:\/\//, "").split("/")[0];
}

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

module.exports = {
  addBookmark,
  listBookmarks,
  removeBookmark,
  extractHost,
  checkUrlReachable,
};
