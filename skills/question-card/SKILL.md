---
name: question-card
description: Use whenever asking the user to choose between options, make a decision, or approve a direction, including every AskUserQuestion call and every checkbox or multi-select question, and whenever a reply would end in "want me to", "should I" or "X or Y?".
---

# Question Card

Every question that offers options or asks for a decision goes in a Question Card: real
alternatives with trade-offs on each, the least framing needed to decide, and a typeable
line for an answer you did not think of.

## The rules

1. **Several genuinely different options.** Drop to two only when the choice truly is
   binary, and say why there is no third. Never pad with an invented option. Small /
   medium / large of one idea is one option, not three. **No upper limit:** never drop a
   real option to fit the tool's four-option cap; draw the card in the message body
   instead (see below). A dropped option is worse than padding, because the user cannot
   ask for what they were never shown.
2. **Plain labels, readable cold.** No jargon, and no opaque references: no internal IDs,
   queue names, def names, ticket IDs, codenames or private names (for example `Q7` or `The Foo Item`).
   If an identifier matters, put it in the option body after a plain description.
3. **Every option says WHY, then trade-offs both directions** (owner, 2026-10-23). Lead each
   description with the motivation: why someone would pick this, the goal it serves. Then what it
   buys and what it costs,
   including build cost and risk where they differ. An option with only upsides is
   advocacy, including the recommended one.
4. **A real write-in line the user can type on.** The client draws it; you cannot. So:
   - **Never put a `preview` on any option.** A single preview switches the client to a
     side-by-side layout that removes the write-in line (only "Chat about this", which
     aborts, remains). Option count is not the cause. Mockups go above the card.
   - Never author your own `Other` / `Type:` option: selecting a label submits the label,
     it is not a text field. Never promise "Other is available" in prose instead.
   - If a preview-free card still shows no write-in, stop using the tool for that
     question and ask in the message body (exception 1 below).
5. **Always mark one recommendation, with exactly one line of why**, on that option only.
   When the pick is essentially arbitrary (the options are equivalent, or it is the
   user's personal preference and you lack the information to judge), still mark one,
   and say so in that line: "Essentially a coin flip: ..." or "Your preference; I lack
   the information to judge, defaulting to ...".
6. **The card carries its own context (owner, 2026-10-20 and 2026-10-21).** In focus mode
   the card may be the only thing the user reads, so the question text itself must teach what
   they need to decide: what was learned, in plain words, and a one-line definition of every
   term an option uses (a tool, a component, a path name). Never name something they have not
   been shown and had explained. A one-phrase question with summaries elsewhere is the
   failure. When a decision answers someone else's message, quote that message's operative
   text (who, when, the exact ask) in the question text.
7. **Above the card, only what changes the answer.** What is being decided (if the
   question text does not carry it) and any constraint that would surprise them. Test
   each sentence: would deleting it change the choice? No restating their request, no
   recap of your work; costs live on the options. If the framing shows the question is
   wrong or void, fix it or say so instead of asking.
8. **The real local time on its own line immediately above the card**, read from
   `date "+%a %b %-d, %-I:%M %p %Z"` at the moment of asking, never guessed or reused
   from session start. If the host's zone is not the owner's, prefix `TZ=<owner's zone>`.
9. **Never ask a question buried in prose.** The trigger is "am I asking for a
   decision", not "does this feel like a question". The commonest break is a question
   closing a long report, where it reads as a sign-off: before sending, scan the last two
   sentences for "want me to", "should I", "shall I", or "or" joining two courses of
   action. Any hit means a card was owed.
10. **If the user must LOOK at something first, the card waits for a "yes" (owner, 2026-10-23).** The
    card covers the screen, so a write-up, image, save or mockup they are meant to study is hidden
    the moment the card opens. When the decision depends on anything graphical or long (art,
    a picture, a table, a long write-up): ① send the explanation and the visuals as ordinary
    messages, ② end that message with one line: *"After you read that, are you ready for a
    question card?"*, ③ **send no card and take no further action on the decision until they
    say yes.** Text-only decisions that fit in the question text need no pause.

**Prose exceptions: exactly two, both announced as a question.** (1) The tool cannot
render a write-in on a preview-free card. (2) More than four real options: the
body-rendered card below. Neither is a shortcut for when a card feels heavy.

## Mockups

When shapes compare faster than paragraphs (a layout, screen, data shape, ladder of
states), draw them in the message body above the card, labelled with the option labels'
own words, then send the card with no previews. Such a mockup counts as information that
changes the answer, so rule 6 allows the longer lead-in.

## More than four options: the card in the message body

Write it as a numbered list with every other rule intact, and say any number, or
something else, may be answered. Prefer the tool when four options genuinely cover the
space, since its write-in is more reliable.

```
Fri Sep 25, 11:04 AM PDT

Pick a number, or say something else:

1. **Plain label** - what it buys; what it costs.
2. **Plain label** - what it buys; what it costs.
...
6. **Plain label** <- recommended - one line of why.
```

## Checkbox cards: surface the combinations you know about

If two options interact (reinforce, partly cancel, cost less together), add an option
after the singles that names the combination in words (never `1+3`) and states the
interaction, e.g. `Fix the diagnosis, then point at it` - *the pointer is only worth
adding once its target is correct; together they cost barely more than the fix alone.*
With the four-option cap, surface the one the user is most likely to miss; more
interactions than fit means the question should be split.

## When to ask

As soon as the work needs the answer: not earlier (the question has not formed), not
after building on a guess. Batch only small, independent choices whose answers will not
redirect the work. Timing never justifies downgrading a card to prose.

## Checklist

- [ ] Several genuinely different options; two only if binary, and say why; none dropped to fit four
- [ ] Real local time from `date` on its own line above the card
- [ ] Asked in a card (or one of the two announced prose exceptions)
- [ ] No `preview` on any option; no hand-made "Other"
- [ ] Labels readable cold: no jargon, IDs or codenames
- [ ] Every option opens with WHY (its motivation), then what it buys and what it costs
- [ ] One recommendation, one line of why; says so if the pick is essentially arbitrary
- [ ] Question text teaches what the user needs: findings in plain words, every term an option uses defined
- [ ] Lead-in only what changes the answer; mockups above the card
- [ ] Anything the user must look at was shown first, and the "ready for a question card?" pause was honoured
- [ ] Checkbox cards: interactions surfaced as a named combination option

## Growing this skill

When the user corrects how a question was put, add a ruling to
`references/DECISIONS.md` (their wording, the reason; mark reversed entries `SUPERSEDED`)
and fold the rule into the rules or checklist above. Read that file when two rules seem
to conflict, before concluding a rule is wrong, or for an edge case the rules do not
cover.
