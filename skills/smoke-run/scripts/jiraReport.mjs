#!/usr/bin/env node
/**
 * Post a smoke-run report to Jira as native ADF (coloured verdict panels, status lozenges,
 * a GATE marker on gate steps) instead of plain Markdown.
 *
 *   node <plugin>/skills/smoke-run/scripts/jiraReport.mjs run.json
 *   node <plugin>/skills/smoke-run/scripts/jiraReport.mjs run.json --update 30253    # edit an existing comment in place
 *   node <plugin>/skills/smoke-run/scripts/jiraReport.mjs run.json --dry-run         # validate and print, post nothing
 *
 * The point is not the formatting. It is that three things stop depending on the model getting
 * them right, and start being checked:
 *
 *   - the conformance verdict is COMPUTED from the step outcomes, never supplied;
 *   - the feature verdict is CHECKED against the gate steps, and a plan tagging none is refused;
 *   - the counts must sum to the number of steps, or nothing is posted;
 *   - every `fail` must carry a screenshot, or nothing is posted;
 *   - an untracked failure is called out — a defect with no issue key is a defect nobody acts on.
 *
 * Credentials are the same as <plugin>/skills/smoke-run/scripts/jiraAttach.mjs — JIRA_EMAIL / JIRA_API_TOKEN in ~/.zshrc.
 * See that file's header for token type and why a granular-scoped token cannot be used.
 *
 * Input JSON:
 * {
 *   "issue": "KING-22281",
 *   "date": "11 Aug 2026",
 *   "env": "TEST",                              // TEST | PREPROD
 *   "driver": "model-driven (Playwright MCP)",
 *   "featureVerdict": "live",                   // live | partially live | not live
 *   "gateNote": "All gate steps satisfied — deeper testing can proceed.",
 *   "grounding": {"liveConfirmedOnly": 8, "total": 13},   // optional but strongly wanted
 *   //   how many expected results came ONLY from observed behaviour. Those steps cannot detect a
 *   //   day-one defect, and the report says so rather than letting a green imply more than it means.
 *   "steps": [
 *     { "n": 1, "gate": true, "title": "…", "outcome": "pass", "evidence": "…" },
 *     { "n": 2, "gate": true, "title": "…", "outcome": "fail", "evidence": "…",
 *       "screenshot": "step-02-dropdown-no-placeholder.png",
 *       "blocking": false,          // did this failure stop later steps? default true
 *       "known": "KING-22420" }     // already-filed defect. Still a fail, still red.
 *   ],
 *   "notAttempted": "none — all 13 steps accounted for",
 *   "raised": ["KING-22355 — soft-deleted field still blocks export"],
 *   "openQuestions": ["…"],
 *   "environmentLeft": "…",
 *   "correction": "…",   // optional: this report restates a verdict a PREVIOUS run got wrong.
 *   //   Rendered as a warning panel at the top. Use it when re-posting a past run whose verdict
 *   //   no longer holds — a known-false PASS left standing is worse than an edited history.
 *   "artifact": "https://claude.ai/code/artifact/…"   // the mirror; both formats cross-link
 * }
 */

import fs from 'node:fs';

const SITE_URL = (process.env.JIRA_BASE_URL ?? 'https://kinoadev.atlassian.net').replace(/\/+$/, '');
const CLOUD_ID = process.env.JIRA_CLOUD_ID ?? 'd1d385cd-174f-488e-a86f-f70f777a885a';
const GATEWAY = `https://api.atlassian.com/ex/jira/${CLOUD_ID}`;
const EMAIL = process.env.JIRA_EMAIL;
const TOKEN = process.env.JIRA_API_TOKEN;

const OUTCOMES = {
    pass: {label: 'PASS', colour: 'green'},
    fail: {label: 'FAIL', colour: 'red'},
    blocked: {label: 'BLOCKED', colour: 'yellow'}
};
const FEATURE = {
    'live': {label: 'LIVE', colour: 'green', panel: 'success'},
    'partially live': {label: 'PARTIALLY LIVE', colour: 'yellow', panel: 'warning'},
    'not live': {label: 'NOT LIVE', colour: 'red', panel: 'error'}
};
const CONFORMANCE = {
    passed: {label: 'PASSED', colour: 'green', panel: 'success'},
    blocked: {label: 'BLOCKED', colour: 'yellow', panel: 'warning'},
    failed: {label: 'FAILED', colour: 'red', panel: 'error'}
};

function fail(message) {
    console.error(`\n✗ ${message}\n`);
    process.exit(1);
}

// ---------- input ----------

const args = process.argv.slice(2);
const file = args.find((a) => !a.startsWith('--'));
const dryRun = args.includes('--dry-run');
const updateIdx = args.indexOf('--update');
const updateId = updateIdx >= 0 ? args[updateIdx + 1] : null;

if (!file) fail('Usage: node <plugin>/skills/smoke-run/scripts/jiraReport.mjs <run.json> [--update <commentId>] [--dry-run]');
if (!fs.existsSync(file)) fail(`No such file: ${file}`);
if (!dryRun && (!EMAIL || !TOKEN)) {
    fail('JIRA_EMAIL and JIRA_API_TOKEN must be set — see <plugin>/skills/smoke-run/scripts/jiraAttach.mjs for how.');
}

let run;
try {
    run = JSON.parse(fs.readFileSync(file, 'utf8'));
} catch (e) {
    fail(`${file} is not valid JSON: ${e.message}`);
}

// ---------- validation: the reason this script exists ----------

const problems = [];

if (!/^[A-Z][A-Z0-9]+-\d+$/.test(run.issue ?? '')) problems.push('"issue" must be an issue key.');
if (!Array.isArray(run.steps) || !run.steps.length) problems.push('"steps" must be a non-empty array.');
if (!FEATURE[run.featureVerdict]) {
    problems.push(`"featureVerdict" must be one of: ${Object.keys(FEATURE).join(', ')}.`);
}

for (const s of run.steps ?? []) {
    const at = `step ${s.n ?? '?'}`;
    if (!OUTCOMES[s.outcome]) problems.push(`${at}: outcome must be pass, fail or blocked.`);
    if (!s.title) problems.push(`${at}: missing "title".`);
    if (s.outcome !== 'pass' && !s.evidence) problems.push(`${at}: a non-pass step needs "evidence".`);

    // The rule that a report cannot be posted without: a failure you cannot see is not evidence.
    if (s.outcome === 'fail' && !s.screenshot && !s.screenshotWaived) {
        problems.push(
            `${at}: a "fail" needs a "screenshot" naming the attached file ` +
            '(e.g. step-02-dropdown-no-placeholder.png). If a screenshot genuinely cannot be ' +
            'produced, set "screenshotWaived" to the reason — that is itself a finding.'
        );
    }
    if (s.screenshot && !/^step-\d{2}[a-z]?-[a-z0-9-]+\.(png|jpg|webp)$/.test(s.screenshot)) {
        problems.push(
            `${at}: screenshot "${s.screenshot}" should be named step-NN-what-it-shows.png ` +
            '— the number ties it to the step, the words say what a reader is looking at.'
        );
    }
}

if (problems.length) {
    fail('Report rejected:\n  - ' + problems.join('\n  - '));
}

// ---------- computed, never supplied ----------

const counts = {pass: 0, fail: 0, blocked: 0};
for (const s of run.steps) counts[s.outcome]++;

const conformance = counts.fail ? 'failed' : counts.blocked ? 'blocked' : 'passed';
const total = counts.pass + counts.fail + counts.blocked;
if (total !== run.steps.length) {
    fail(`Counts do not sum: ${total} outcomes for ${run.steps.length} steps.`);
}

const gate = run.steps.filter((s) => s.gate);
const gateSteps = gate.map((s) => s.n);

// The feature verdict is derivable from the gate steps, so derive it and refuse a contradiction
// rather than printing whatever was supplied.
if (!gate.length) {
    fail(
        'No step is tagged as a gate, so the feature verdict cannot be derived.\n' +
        '  The plan needs [GATE] on the minimal steps that prove the feature is live —\n' +
        '  see /kinoa-qa:smoke-plan (skills/smoke-plan/SKILL.md). Fix the plan, do not guess a verdict.'
    );
}
const gatePassed = gate.filter((s) => s.outcome === 'pass').length;
const derived = gatePassed === gate.length ? 'live' : gatePassed ? 'partially live' : 'not live';
if (derived !== run.featureVerdict) {
    fail(
        `featureVerdict says "${run.featureVerdict}" but the gate steps say "${derived}".\n` +
        `  ${gatePassed} of ${gate.length} gate steps passed ` +
        `(${gateSteps.join(', ')}).\n` +
        '  Every gate passing is "live"; some passing is "partially live"; none is "not live".'
    );
}

const failing = run.steps.filter((s) => s.outcome === 'fail');
const known = failing.filter((s) => s.known).length;
const untracked = failing.filter((s) => !s.known);

// ---------- ADF ----------

const text = (t, ...marks) => marks.length
    ? {type: 'text', text: t, marks: marks.map((m) => ({type: m}))}
    : {type: 'text', text: t};
const para = (...content) => ({type: 'paragraph', content});
const lozenge = (label, colour) => ({type: 'status', attrs: {text: label, color: colour}});
const cell = (content, header = false) => ({
    type: header ? 'tableHeader' : 'tableCell', attrs: {}, content: [content]
});
const row = (...cells) => ({type: 'tableRow', content: cells});
const panel = (panelType, ...content) => ({type: 'panel', attrs: {panelType}, content});

const f = FEATURE[run.featureVerdict];
const c = CONFORMANCE[conformance];

const table = [row(
    cell(para(text('#')), true),
    cell(para(text('Step')), true),
    cell(para(text('Outcome')), true),
    cell(para(text('Evidence')), true)
)];

for (const s of run.steps) {
    const num = [text(String(s.n), 'strong')];
    if (s.gate) num.push(text(' '), lozenge('GATE', 'blue'));

    const evidence = [];
    if (s.outcome === 'fail') {
        // Both annotations exist because a bare "fail" cannot say whether the run stopped, or
        // whether anybody is going to act on it.
        const tags = [];
        if (s.blocking === false) tags.push('non-blocking');
        if (s.known) tags.push(`known ${s.known}`);
        if (tags.length) evidence.push(text(`(${tags.join(', ')}) `, 'strong'));
    }
    if (s.evidence) evidence.push(text(s.evidence));
    if (s.screenshot) {
        evidence.push(text(s.evidence ? ' — ' : ''), text(s.screenshot, 'code'));
    }
    if (s.screenshotWaived) {
        evidence.push(text(` — no screenshot: ${s.screenshotWaived}`, 'em'));
    }

    table.push(row(
        cell(para(...num)),
        cell(para(text(s.title))),
        cell(para(lozenge(OUTCOMES[s.outcome].label, OUTCOMES[s.outcome].colour))),
        cell(para(...(evidence.length ? evidence : [text('—')])))
    ));
}

const content = [];

if (run.correction) {
    content.push(panel('warning', para(
        text('Corrected  ', 'strong'), text(run.correction)
    )));
}

content.push(
    {
        type: 'heading', attrs: {level: 3},
        content: [text(`Smoke run — ${run.date} · ${run.env} · ${run.driver}`)]
    },
    panel(f.panel, para(
        text('Feature verdict  ', 'strong'), lozenge(f.label, f.colour),
        text(`  ${run.gateNote ?? `Gate steps: ${gateSteps.join(', ') || 'none tagged'}.`}`)
    )),
    panel(c.panel, para(
        text('Conformance  ', 'strong'), lozenge(c.label, c.colour),
        text(`  ${counts.pass} pass / ${counts.fail} fail${known ? ` (${known} known)` : ''} / ` +
             `${counts.blocked} blocked. ` +
             'A conformance failure means a value disagrees with a written spec, not that the ' +
             'feature is broken. A known, filed defect is still a failure — this never goes green ' +
             'or yellow because someone has seen it before.')
    )),
    {type: 'table', attrs: {isNumberColumnEnabled: false, layout: 'default'}, content: table}
);

const line = (label, value) => para(text(`${label}: `, 'strong'), text(value));

if (run.grounding?.total) {
    const {liveConfirmedOnly: only, total: all} = run.grounding;
    content.push(panel(only / all > 0.5 ? 'warning' : 'info', para(
        text('Grounding  ', 'strong'),
        text(`${only} of ${all} expected results are grounded on observed behaviour only, with no ` +
             'written source. Those steps cannot detect a day-one defect — they assert what the ' +
             'build was seen to do. Where that proportion is high, the finding is about the spec, ' +
             'not the test.')
    )));
}

if (run.notAttempted) content.push(line('Not attempted (counted in blocked)', run.notAttempted));
for (const r of run.raised ?? []) content.push(line('Raised', r));
for (const q of run.openQuestions ?? []) content.push(line('Open question', q));
if (run.environmentLeft) content.push(line('Environment left', run.environmentLeft));

if (run.artifact) {
    content.push(para(
        text('Readable version: ', 'strong'),
        {type: 'text', text: run.artifact, marks: [{type: 'link', attrs: {href: run.artifact}}]},
        text(' — same content, embedded screenshots.')
    ));
}

const doc = {type: 'doc', version: 1, content};

// ---------- output ----------

console.log(`✓ ${run.steps.length} steps · ${counts.pass} pass / ${counts.fail} fail / ${counts.blocked} blocked`);
console.log(`  feature: ${run.featureVerdict}   conformance: ${conformance} (computed)`);
console.log(`  gate steps: ${gateSteps.join(', ') || 'NONE TAGGED — smoke-run cannot derive a feature verdict'}`);
const shots = run.steps.filter((s) => s.screenshot).length;
console.log(`  screenshots referenced: ${shots}`);
if (run.grounding?.total) {
    console.log(`  grounded on observed behaviour only: ${run.grounding.liveConfirmedOnly}/${run.grounding.total}`);
}
if (untracked.length) {
    console.log(`\n  ⚠ ${untracked.length} failure(s) carry no issue key: ` +
                `step ${untracked.map((s) => s.n).join(', ')}.`);
    console.log('    File them and add "known": "<KEY>" — an untracked failure is one nobody acts on.');
}

if (dryRun) {
    console.log('\n--dry-run: nothing posted. ADF document:\n');
    console.log(JSON.stringify(doc, null, 2));
    process.exit(0);
}

const auth = 'Basic ' + Buffer.from(`${EMAIL}:${TOKEN}`).toString('base64');
const url = updateId
    ? `${GATEWAY}/rest/api/3/issue/${run.issue}/comment/${updateId}`
    : `${GATEWAY}/rest/api/3/issue/${run.issue}/comment`;

const res = await fetch(url, {
    method: updateId ? 'PUT' : 'POST',
    headers: {Authorization: auth, 'Content-Type': 'application/json', Accept: 'application/json'},
    body: JSON.stringify({body: doc})
});

if (!res.ok) {
    const body = await res.text();
    console.error(`\n✗ HTTP ${res.status} ${res.statusText}\n  ${body.slice(0, 400)}`);
    if (/ATTACHMENT_VALIDATION_ERROR/.test(body)) {
        console.error('  An inline image was rejected. Jira needs a media-services id, which the\n' +
                      '  attachment API does not return — reference screenshots by filename instead.');
    }
    process.exit(1);
}

const out = await res.json();
console.log(`\n✓ ${updateId ? 'Updated' : 'Posted'} → ${SITE_URL}/browse/${run.issue}?focusedCommentId=${out.id}`);
if (!run.artifact) {
    console.log('  No "artifact" URL in the report — publish the mirror and re-run with --update ' +
                `${out.id} so the two formats cross-link.`);
}
