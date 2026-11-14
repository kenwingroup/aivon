// Tasks replaced the four-panel Kanban page in 0.422.0. Keep its permission
// escape hatch covered in the current page, rather than asserting retired DOM.
"use strict";
const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");
const root = path.join(__dirname, "../..");
const read = f => fs.readFileSync(path.join(root, f), "utf8");
const js = read("dashboard/tasks.js");
const consoleJs = read("dashboard/console.js");
const py = read("server/tasks.py");
const vi = JSON.parse(read("dashboard/i18n/vi.json"));
assert.match(consoleJs, /kanban:\s*"tasks"/);
assert.match(consoleJs, /window\.AivonTasks\.mount/);
assert.match(js, /it\.src === "kanban" && it\.st === "ask" && it\.blockKind === "capability"/);
assert.match(js, /data-act="grant"/);
assert.match(js, /if \(!window\.confirm\(tw\("kanban.confirm_grant"\)\)\) return/);
assert.match(js, /postForm\("\/kanban\/task\/grant", \{ brain: b, id: it\.ref \}\)/);
assert.match(py, /@router\.post\("\/kanban\/task\/grant"\)/);
assert.match(py, /block_kind"\) or ""\) != "capability"/);
assert.match(vi["kanban.confirm_grant"], /KHÔNG hoàn tác/);
// Real model behavior for task grouping, attention and history is exercised here too.
require("./test_tasks_page_model.js");
console.log("ok current Tasks routing and explicit capability grant");
