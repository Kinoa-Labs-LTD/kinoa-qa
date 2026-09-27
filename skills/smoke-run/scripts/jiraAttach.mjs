#!/usr/bin/env node
/**
 * Attach files to a Jira issue.
 *
 * The Atlassian MCP can write comments and descriptions but cannot upload files, so evidence
 * screenshots could not reach a ticket without a human step. This closes that gap: the QA skills
 * (see skills/smoke-run in the kinoa-qa plugin) shell out to this after capturing evidence.
 *
 *   node <plugin>/skills/smoke-run/scripts/jiraAttach.mjs KING-22355 ./a.png ./b.png
 *
 * Credentials come from the environment — never from the repo:
 *   JIRA_EMAIL      your Atlassian account email
 *   JIRA_API_TOKEN  an API token from id.atlassian.com → Security → API tokens
 *   JIRA_BASE_URL   optional site URL, defaults to https://kinoadev.atlassian.net
 *   JIRA_CLOUD_ID   optional, defaults to the Kinoa cloud id (used for the api.atlassian.com gateway)
 *   JIRA_HOST       optional: "site" | "gateway" | "auto" (default). Scoped tokens need "gateway";
 *                   classic unscoped tokens need "site". Auto tries site then gateway.
 *
 * Token type matters, and not in the obvious way:
 *
 *   Scoped token, CLASSIC scopes   ← use this. Grant read:jira-work + write:jira-work.
 *   Scoped token, GRANULAR scopes  ← does NOT work for uploads. See below.
 *   Classic unscoped token         ← works, but carries your entire Jira access.
 *
 * GRANULAR-scoped tokens (write:attachment:jira and friends) authenticate correctly and work for GET
 * and PUT, but Atlassian's gateway rejects every POST with 401 "Unauthorized; scope does not match",
 * whatever scopes are granted. Attachment upload is a POST, so it always fails. This is an Atlassian
 * bug confirmed against Jira Cloud in April 2026, not a problem with this script:
 *   https://community.developer.atlassian.com/t/401-scope-does-not-match-issue-when-uploading-an-attachment/93805
 * The documented workaround is a token with CLASSIC scopes.
 *
 * Auth is Basic (email:token) in all cases. Scoped tokens go through the api.atlassian.com gateway;
 * classic unscoped tokens use the site URL. This script tries the site URL, falls back to the
 * gateway, and reports which worked. Verified working 11 Aug 2026 with a scoped token holding the
 * classic scopes, via the gateway. All Atlassian tokens now expire within a year.
 *
 * Put the values in ~/.zshrc — NOT ~/.zprofile, which only login shells read. Never commit them.
 */

import fs from 'node:fs';
import path from 'node:path';

const SITE_URL = (process.env.JIRA_BASE_URL ?? 'https://kinoadev.atlassian.net').replace(/\/+$/, '');
const CLOUD_ID = process.env.JIRA_CLOUD_ID ?? 'd1d385cd-174f-488e-a86f-f70f777a885a';
const GATEWAY_URL = `https://api.atlassian.com/ex/jira/${CLOUD_ID}`;
const EMAIL = process.env.JIRA_EMAIL;
const TOKEN = process.env.JIRA_API_TOKEN;
const HOST_MODE = (process.env.JIRA_HOST ?? 'auto').toLowerCase();

const SCOPE_BUG_URL =
    'https://community.developer.atlassian.com/t/401-scope-does-not-match-issue-when-uploading-an-attachment/93805';

const MIME = {
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
    '.pdf': 'application/pdf',
    '.txt': 'text/plain',
    '.json': 'application/json',
    '.har': 'application/json',
    '.zip': 'application/zip',
    '.webm': 'video/webm',
    '.mp4': 'video/mp4'
};

function fail(message) {
    console.error(`\n✗ ${message}\n`);
    process.exit(1);
}

const [issueKey, ...files] = process.argv.slice(2);

if (!issueKey || !files.length) {
    fail('Usage: node <plugin>/skills/smoke-run/scripts/jiraAttach.mjs <ISSUE-KEY> <file> [more files...]');
}
if (!/^[A-Z][A-Z0-9]+-\d+$/.test(issueKey)) {
    fail(`"${issueKey}" is not an issue key. Expected something like KING-22355.`);
}
if (!TOKEN || !EMAIL) {
    fail(
        'JIRA_EMAIL and JIRA_API_TOKEN must be set.\n' +
        '  1. Go to https://id.atlassian.com/manage-profile/security/api-tokens\n' +
        '  2. "Create API token with scopes" → Jira → choose the CLASSIC scopes:\n' +
        '       read:jira-work    view issues\n' +
        '       write:jira-work   create attachments\n' +
        '     Granular scopes (write:attachment:jira) look tighter but cannot upload —\n' +
        '     Atlassian rejects every POST with "scope does not match". See:\n' +
        `     ${SCOPE_BUG_URL}\n` +
        '  3. Add to ~/.zshrc (not ~/.zprofile — only login shells read that):\n' +
        '       export JIRA_EMAIL="you@kinoa.io"\n' +
        '       export JIRA_API_TOKEN="…"\n' +
        '  4. Open a new shell, or run: source ~/.zshrc'
    );
}

const missing = files.filter((f) => !fs.existsSync(f));
if (missing.length) {
    fail(`File(s) not found:\n  ${missing.join('\n  ')}`);
}

const hosts = HOST_MODE === 'site' ? [SITE_URL]
    : HOST_MODE === 'gateway' ? [GATEWAY_URL]
    : [SITE_URL, GATEWAY_URL];

const auth = `Basic ${Buffer.from(`${EMAIL}:${TOKEN}`).toString('base64')}`;

function buildForm(file) {
    const buf = fs.readFileSync(file);
    const type = MIME[path.extname(file).toLowerCase()] ?? 'application/octet-stream';
    const form = new FormData();
    // Jira requires the field name to be exactly "file".
    form.append('file', new Blob([buf], {type}), path.basename(file));
    return {form, size: (buf.length / 1024).toFixed(0)};
}

async function upload(file, host) {
    const {form, size} = buildForm(file);
    const res = await fetch(`${host}/rest/api/3/issue/${issueKey}/attachments`, {
        method: 'POST',
        headers: {
            Authorization: auth,
            // Required by Jira's XSRF check for attachment upload.
            'X-Atlassian-Token': 'no-check'
            // Content-Type is deliberately unset — fetch adds the multipart boundary.
        },
        body: form
    });
    return {res, size, body: await res.text()};
}

function explain(status, body, host) {
    if (/scope does not match/i.test(body)) {
        return '  Your token has GRANULAR scopes. Those cannot upload attachments — Atlassian\n' +
               '  rejects every POST with this error regardless of the scopes granted.\n' +
               '  Fix: create a token with the CLASSIC scopes read:jira-work + write:jira-work.\n' +
               `  Background: ${SCOPE_BUG_URL}`;
    }
    if (status === 401 || status === 403) {
        return '  Authentication failed. Check the token is current (they expire within a year)\n' +
               '  and that JIRA_EMAIL matches the account that created it.';
    }
    if (status === 404) {
        return `  ${issueKey} not found via ${host}, or not visible to this token.\n` +
               '  Check the issue key, and that the token grants read:jira-work.';
    }
    return null;
}

let failures = 0;
let workingHost = null;

for (const file of files) {
    const name = path.basename(file);
    const tryThese = workingHost ? [workingHost] : hosts;
    let last = null;

    for (const host of tryThese) {
        last = {...await upload(file, host), host};
        if (last.res.ok) {
            if (!workingHost) {
                workingHost = host;
                if (hosts.length > 1) {
                    const pin = host === SITE_URL ? 'site' : 'gateway';
                    console.log(`  (using ${pin} — pin it with JIRA_HOST=${pin} to skip the probe)`);
                }
            }
            break;
        }
        // Only a rejection at this host is worth retrying elsewhere.
        if (![401, 403, 404].includes(last.res.status)) break;
    }

    const {res, size, body, host} = last;

    if (!res.ok) {
        failures++;
        console.error(`✗ ${name} — HTTP ${res.status} ${res.statusText}\n  ${body.slice(0, 300)}`);
        const hint = explain(res.status, body, host);
        if (hint) console.error(hint);
        continue;
    }

    const [attachment] = JSON.parse(body);
    console.log(`✓ ${name} (${size} KB) → ${SITE_URL}/browse/${issueKey}  [id ${attachment?.id}]`);
}

if (failures) {
    fail(`${failures} of ${files.length} upload(s) failed.`);
}

console.log(`\nAttached ${files.length} file(s) to ${SITE_URL}/browse/${issueKey}`);
