const fs = require("fs");
const path = require("path");
const {
  addBookmark,
  listBookmarks,
  removeBookmark,
  checkUrlReachable,
} = require("./bookmarks");

const DATA_FILE = path.join(__dirname, "..", "data", "bookmarks.json");

function loadBookmarks() {
  if (!fs.existsSync(DATA_FILE)) return [];
  return JSON.parse(fs.readFileSync(DATA_FILE, "utf8"));
}

function saveBookmarks(list) {
  fs.mkdirSync(path.dirname(DATA_FILE), { recursive: true });
  fs.writeFileSync(DATA_FILE, JSON.stringify(list, null, 2));
}

function main() {
  const [command, ...args] = process.argv.slice(2);
  const bookmarks = loadBookmarks();

  switch (command) {
    case "add": {
      const [url, title] = args;
      const bookmark = addBookmark(bookmarks, { url, title });
      saveBookmarks(bookmarks);
      console.log(`Added bookmark #${bookmark.id}: ${bookmark.title}`);
      break;
    }
    case "list": {
      const page = Number(args[0]) || 1;
      const pageSize = Number(args[1]) || 10;
      const page_ = listBookmarks(bookmarks, page, pageSize);
      page_.forEach((b) => console.log(`#${b.id} ${b.title} (${b.url})`));
      break;
    }
    case "remove": {
      const id = Number(args[0]);
      const updated = removeBookmark(bookmarks, id);
      saveBookmarks(updated);
      console.log(`Removed bookmark #${id} (now ${updated.length} remaining)`);
      break;
    }
    case "check": {
      const url = args[0];
      checkUrlReachable(url, (reachable) => {
        console.log(`${url} reachable: ${reachable}`);
      });
      break;
    }
    default:
      console.log("Usage: node src/index.js <add|list|remove|check> [args]");
      process.exitCode = 1;
  }
}

main();
