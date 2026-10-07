# Language — simple English (B1–B2)

Both the plan and the report are written in simple English, around CEFR level B1–B2. Many readers
are not native English speakers, and the report is usually read in a hurry. This file is read at
the first write of prose; each SKILL file says when that is.

How to write it:

- One idea per sentence. Aim for 20 words or fewer. Split a long sentence instead of adding more
  commas and dashes.
- Use common words: "use" not "leverage", "for example" not "e.g.", "missing" not "silently absent".
- Say who does what: "the server returns an error", not "an error is returned".
- No idioms, no metaphors, no jokes: a reader who does not know the idiom reads a different fact.
- Short paragraphs. Use a bullet list when the content is a list.

Some text must stay exactly as it is, because a reader or a tool copies it:

- tool names, argument names, and full JSON payloads;
- ids, names and keys of real entities;
- error codes (`PERMISSION_DENIED`), statuses (`PASS` / `FAIL` / `OBSERVED` / `BLOCKED`), property
  names, HTTP paths;
- every fixed label the contracts define. Do not reword them, and do not translate them into
  simpler words, because `check-layout.sh` and the comparison of two reports match them by their
  exact text: the ten report section names, the artifact labels (`exists (status: <x>)`,
  `soft-deleted (status: <x>, still gettable)`, `hard-deleted (id no longer resolves)`), the
  finding-block field names (`Case:` / `Tool:` / `Part:`, and `Steps to reproduce`, `Expected`,
  `Actual`, `Isolation`, and the per-step `Request:` / `Response:` lines), the note-block field
  names (`Case:` / `Tool:` / `Part:`, and `What was seen`, `Why it is not a finding`,
  `Suggested action`), the `Also record:` label of a case row's `Expected` cell, the hypothesis
  verdicts (`CONFIRMED` / `REFUTED` / `UNPROVEN`) and the overall status (`GREEN` / `RED` /
  `BLOCKED`);
- text quoted from an acceptance criterion or from a tool description. Quote it as written, even if
  the English is hard. Add your own plain sentence after the quote if the quote needs one.

Simple English is about the wording, never about the content. Never drop a fact, a number, a
condition or a caveat to make a sentence shorter: a dropped caveat changes what the report claims.
If a precise term is needed, keep the term and explain it in one short sentence.

Some terms of this domain are above B1–B2 and are still required, because no simpler word means the
same thing: *soft delete*, *hard delete*, *envelope*, *confirm token*, *preview leg*, *replica*,
*rate limit*, *role scope*, *grey box*, *hypothesis*. Use them. Explain each one in one short
sentence the first time the report uses it, then use it plainly after that. Do not invent a vaguer
word for them.

| Instead of | Write |
|---|---|
| "the clone drops the description silently" | "the clone loses the description. There is no error and no warning." |
| "a per-replica limiter makes the cut-off untestable" | "each replica counts the calls on its own, so we cannot test the exact limit" |
| "an error that misdirects the caller" | "an error message that points the user to the wrong cause" |
| "the case is invalidated" | "the case is not valid any more" |
| "the determination case establishes the semantics" | "this case shows what the delete really does" |

In a plan, case rows are never simplified for language reasons; that rule is in
[`plan-template.md`](plan-template.md#cases-are-data-prose-is-commentary).
