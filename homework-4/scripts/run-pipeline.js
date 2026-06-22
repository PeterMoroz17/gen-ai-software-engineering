#!/usr/bin/env node
/*
 * Single-command orchestrator for the 4-agent pipeline (+ 2 helper steps).
 * Shells out to the real `claude` CLI in headless mode once per stage,
 * loading each stage's model + instructions (and skill files, where the
 * task requires it) from the markdown files in agents/ and skills/.
 *
 * Every stage uses --permission-mode bypassPermissions so the whole run is
 * truly non-interactive (acceptEdits still gates Bash/test execution, which
 * is what breaks single-command, no-manual-steps execution).
 */
const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const ROOT = path.join(__dirname, "..");
const BUG_ID = "001";
const CTX_DIR = path.join(ROOT, "context", "bugs", BUG_ID);
const SCREENSHOTS_DIR = path.join(ROOT, "docs", "screenshots");

// On Windows the `claude` CLI may be a native claude.exe (the official
// installer) or an npm-created claude.cmd shim, depending on how it was
// installed; spawnSync resolves bare command names through the Windows
// process-creation API directly and does not always fall back across
// extensions. Probe the real PATH at startup instead of hardcoding one
// extension, so this works regardless of install method.
function resolveClaudeBin() {
  if (process.platform !== "win32") return "claude";
  for (const candidate of ["claude.exe", "claude.cmd", "claude"]) {
    const probe = spawnSync(candidate, ["--version"], { encoding: "utf8" });
    if (!probe.error) return candidate;
  }
  throw new Error(
    "Could not resolve the `claude` CLI on PATH (tried claude.exe, claude.cmd, claude)."
  );
}
const CLAUDE_BIN = resolveClaudeBin();

const transcript = [];

function log(line) {
  console.log(line);
  transcript.push(line);
}

function readFile(relPath) {
  // Normalize CRLF to LF so the frontmatter regexes below (which match \n)
  // work regardless of which line endings the markdown file was saved with.
  return fs.readFileSync(path.join(ROOT, relPath), "utf8").replace(/\r\n/g, "\n");
}

function stripFrontmatter(markdown) {
  return markdown.replace(/^---\n[\s\S]*?\n---\n/, "").trim();
}

function parseFrontmatter(markdown) {
  const match = markdown.match(/^---\n([\s\S]*?)\n---\n/);
  const fm = {};
  if (match) {
    for (const line of match[1].split("\n")) {
      const idx = line.indexOf(":");
      if (idx === -1) continue;
      fm[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
    }
  }
  return fm;
}

function runClaude({ label, model, systemPrompt, userPrompt, disallowedTools }) {
  log(`\n=== STAGE: ${label} (model: ${model}) ===`);
  const args = [
    "-p",
    userPrompt,
    "--model",
    model,
    "--append-system-prompt",
    systemPrompt,
    "--permission-mode",
    "bypassPermissions",
  ];
  if (disallowedTools) {
    args.push("--disallowedTools", disallowedTools);
  }
  const result = spawnSync(CLAUDE_BIN, args, {
    cwd: ROOT,
    encoding: "utf8",
    maxBuffer: 1024 * 1024 * 50,
  });
  if (result.error) {
    log(`STAGE FAILED TO START: ${result.error.message}`);
    process.exit(1);
  }
  if (result.stdout) log(result.stdout.trim());
  if (result.stderr) log(`[stderr]\n${result.stderr.trim()}`);
  if (result.status !== 0) {
    log(`STAGE EXITED WITH CODE ${result.status}`);
    process.exit(result.status);
  }
  log(`=== STAGE COMPLETE: ${label} ===`);
}

function assertFileExists(relPath, stageLabel) {
  const fullPath = path.join(ROOT, relPath);
  if (!fs.existsSync(fullPath)) {
    log(`STAGE "${stageLabel}" DID NOT PRODUCE EXPECTED OUTPUT: ${relPath}`);
    process.exit(1);
  }
}

function loadAgent(file) {
  const raw = readFile(path.join("agents", file));
  return { frontmatter: parseFrontmatter(raw), body: stripFrontmatter(raw) };
}

function loadSkill(file) {
  return stripFrontmatter(readFile(path.join("skills", file)));
}

function main() {
  fs.mkdirSync(CTX_DIR, { recursive: true });
  fs.mkdirSync(path.join(CTX_DIR, "research"), { recursive: true });
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });

  log(`Pipeline started ${new Date().toISOString()}`);

  // Stage 0: Bug Researcher (helper step, not a graded agent)
  runClaude({
    label: "Bug Researcher",
    model: "claude-haiku-4-5-20251001",
    systemPrompt:
      "You are the Bug Researcher. Investigate a bug report against the real " +
      "source code and write a factual research report. Every claim you make " +
      "must cite an exact file:line and, where relevant, quote the exact source " +
      "line(s). Do not propose a fix yet -- only document root causes.",
    userPrompt:
      `Read context/bugs/${BUG_ID}/bug-context.md, then investigate src/bookmarks.js ` +
      `and src/index.js to find the root cause of every symptom listed. Write your ` +
      `findings to context/bugs/${BUG_ID}/research/codebase-research.md with one ` +
      `section per symptom, each citing exact file:line references and exact quoted ` +
      `source snippets.`,
    disallowedTools: "Edit",
  });
  assertFileExists(`context/bugs/${BUG_ID}/research/codebase-research.md`, "Bug Researcher");

  // Stage 1: Research Verifier (required agent)
  const researchVerifier = loadAgent("research-verifier.agent.md");
  const qualitySkill = loadSkill("research-quality-measurement.md");
  runClaude({
    label: "Research Verifier",
    model: researchVerifier.frontmatter.model,
    systemPrompt: `${researchVerifier.body}\n\n---\n\n${qualitySkill}`,
    userPrompt:
      `Verify context/bugs/${BUG_ID}/research/codebase-research.md against the real ` +
      `source files per your instructions, then write context/bugs/${BUG_ID}/research/verified-research.md.`,
    disallowedTools: "Edit,Bash",
  });
  assertFileExists(`context/bugs/${BUG_ID}/research/verified-research.md`, "Research Verifier");

  // Stage 2: Bug Planner (helper step, not a graded agent)
  runClaude({
    label: "Bug Planner",
    model: "claude-haiku-4-5-20251001",
    systemPrompt:
      "You are the Bug Planner. Turn verified research into a precise, " +
      "mechanically-executable implementation plan. For every file to change, " +
      "give the EXACT before code snippet and EXACT after code snippet (so an " +
      "executor can apply them as a literal find-and-replace), plus the test " +
      "command to run after each change.",
    userPrompt:
      `Read context/bugs/${BUG_ID}/research/verified-research.md (and the underlying ` +
      `codebase-research.md if needed) and write context/bugs/${BUG_ID}/implementation-plan.md. ` +
      `Use \`npm test\` as the test command. Plan a fix for all three confirmed issues: ` +
      `the pagination off-by-one, the remove-by-id type mismatch, and the command-injection ` +
      `risk in checkUrlReachable (validate/allow-list the host instead of interpolating raw ` +
      `input into a shell string, e.g. using execFile with an argument array, or a strict regex).`,
    disallowedTools: "Edit",
  });
  assertFileExists(`context/bugs/${BUG_ID}/implementation-plan.md`, "Bug Planner");

  // Stage 3: Bug Fixer (required agent)
  const bugFixer = loadAgent("bug-fixer.agent.md");
  runClaude({
    label: "Bug Fixer",
    model: bugFixer.frontmatter.model,
    systemPrompt: bugFixer.body,
    userPrompt:
      `Execute context/bugs/${BUG_ID}/implementation-plan.md exactly, run \`npm test\` ` +
      `after each change, and write context/bugs/${BUG_ID}/fix-summary.md per your instructions.`,
  });
  assertFileExists(`context/bugs/${BUG_ID}/fix-summary.md`, "Bug Fixer");

  // Stage 4: Security Verifier (required agent) -- report only, Edit disallowed
  const securityVerifier = loadAgent("security-verifier.agent.md");
  runClaude({
    label: "Security Verifier",
    model: securityVerifier.frontmatter.model,
    systemPrompt: securityVerifier.body,
    userPrompt:
      `Review the code changed per context/bugs/${BUG_ID}/fix-summary.md for security ` +
      `issues and write context/bugs/${BUG_ID}/security-report.md per your instructions. ` +
      `Do not edit any source file.`,
    disallowedTools: "Edit,Bash",
  });
  assertFileExists(`context/bugs/${BUG_ID}/security-report.md`, "Security Verifier");

  // Stage 5: Unit Test Generator (required agent)
  const testGenerator = loadAgent("unit-test-generator.agent.md");
  const firstSkill = loadSkill("unit-tests-FIRST.md");
  runClaude({
    label: "Unit Test Generator",
    model: testGenerator.frontmatter.model,
    systemPrompt: `${testGenerator.body}\n\n---\n\n${firstSkill}`,
    userPrompt:
      `Read context/bugs/${BUG_ID}/fix-summary.md, add FIRST-compliant unit tests for the ` +
      `changed behavior to tests/, run \`npm test\`, and write context/bugs/${BUG_ID}/test-report.md ` +
      `per your instructions.`,
  });
  assertFileExists(`context/bugs/${BUG_ID}/test-report.md`, "Unit Test Generator");

  log(`\nPipeline finished ${new Date().toISOString()}`);
  fs.writeFileSync(
    path.join(SCREENSHOTS_DIR, "pipeline-run-transcript.txt"),
    transcript.join("\n")
  );
  log(`Transcript saved to docs/screenshots/pipeline-run-transcript.txt`);
}

main();
