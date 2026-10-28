# Accumulated rulings

Every rule in `SKILL.md` came from a correction. This file holds the corrections
themselves — the verbatim wording, the date, the reason, and the theories that were
tried and refuted along the way.

**You do not need to read this to use the skill.** `SKILL.md` is self-contained.
Read here when:

- A rule seems to conflict with another, and you need to know which is newer.
- You are about to argue a rule is wrong — check whether it was already argued and
  settled, and on what evidence.
- You are judging an edge case the rule does not obviously cover, and the original
  reason would tell you which way to fall.
- You are adding a new ruling, and need the format.

**Format.** Newest at the bottom. Each entry: date, one-line title, the user's own
words, and *why*. When a later ruling reverses an earlier one, mark the earlier entry
`SUPERSEDED` rather than deleting it — the reversal is itself information, and a
deleted mistake gets re-derived by the next reader.

---

- **2026-09-15 — origin.** The user twice asked for a free-text path and twice did
  not get one in the card. The first attempt named "Other" only in prose; the
  second produced a card with no cursor on it. Recorded verbatim: *"The final option
  should be Type: With the ability to type a response RIGHT THERE IN THE QUESTION."*
  (His phrasing "the final option should be Type:" describes what he wants to *see*,
  not what to author — see the third entry, which establishes that the line is the
  client's to draw and a self-authored one is a decoy.)
- **2026-09-15 — no opaque labels.** Same conversation, verbatim: *"no opaque
  references to model-based labeling (like B5 or The Melt Item)."* Internal IDs
  are for the model's bookkeeping and must never be the user's decision surface.
- **2026-09-15 — the write-in needs a real cursor, and it is not yours to draw.**
  Third correction in the same conversation, verbatim: *"You still aren't asking
  for my freeform answer properly. My cursor should actually appear on that line
  if I use it, NOT just say 'I'll give a freeform answer'."* A self-authored option
  labelled `Type:` submits a label instead of opening a field, so it is a decoy.
  **Two diagnoses were wrong before the right one; both are recorded so nobody
  re-derives them.** First theory: four options crowded the write-in out. Refuted —
  a three-option card had no write-in either. Second theory (drawn from that): the
  cursor is simply unavailable in this client, so use prose. Also refuted, and it was
  the more expensive error, because it would have retired the card entirely. Both
  failed for the same reason: the cards being compared differed in previews, and
  nobody had isolated that variable.
- **2026-09-15 — mark the recommendation, one line of why.** His choice, with the
  shape given in the preview he picked: the mark sits on the recommended option and
  carries a single line of reasoning. *"One line of why, on the marked option only.
  Never more."*
- **2026-09-15 — always the full briefing.** He rejected scaling framing to stakes
  and chose the full form for every card: what's being decided (two paragraphs),
  what constrains it, what it costs. **SUPERSEDED the same day — see the
  minimal-decisional-information entry.** Kept because the reversal is the useful
  part: what he chose in the abstract was not what he wanted once he saw it on screen.
- **2026-09-15 — minimal decisional information, not a briefing.** Verbatim: *"put
  ONLY a 'minimal decisional information' before the question. I think right now it's
  written to have a massive discussion before the question. That's overkill."* Only
  what changes the answer goes above the card; the test is whether deleting a sentence
  would change the choice. Trade-offs stay on the options, where they are next to what
  they describe.

  **Why the earlier ruling failed in practice:** "two paragraphs, not one sentence"
  reads as thoroughness on paper, but in a live card the lead-in grew to several
  times the height of the decision and buried it. Note the asymmetry — a thin frame
  costs one clarifying round trip; a bloated one is paid on every single card. When
  in doubt, err short.
- **2026-09-15 — previews whenever they aid comparison.** Not reserved for visual
  subjects. His reasoning, from the preview he chose: *"you are comparing SHAPES,
  not statements. Three mockups read faster side by side than three paragraphs."*
  **SUPERSEDED the same day — see the next entry.** The instinct stands; the
  mechanism does not. Mockups now go in the message body, never in a `preview`.
- **2026-09-15 — previews suppress the write-in line. Measured, three cards.** He
  asked to test the cursor directly and screenshotted each result (Claude Code
  2.1.116):

  | Card | Options | Previews | Bottom of card |
  |---|---|---|---|
  | 1 | 3 | yes, on all three | `Chat about this` only — **no write-in** |
  | 2 | 3 | none | `4. Type something.` then `5. Chat about this` |
  | 3 | 4 | none | `5. Type something.` then `6. Chat about this` |

  Cards 1 and 2 were the *same three options*, previews the only difference. So the
  preview is the sole cause, and option count is irrelevant — four is fine. A preview
  flips the client to side-by-side layout (options left, mockup box right) and the
  write-in line is not drawn in that layout; `Chat about this` aborts rather than
  answers, which is why it is not a substitute. His verdict on card 2: *"That is the
  CORRECT example that I like."* Then: *"change the skill now to decline previews in
  lieu of the type something."* Previews lose, every time.

  Method note worth keeping: the first two theories survived as long as they did
  because each new card changed more than one thing at once. The answer arrived the
  moment two cards differed in exactly one variable. Change one thing per card.
- **2026-09-15 — diversity, not a count.** Asked whether the two-option ban should
  hold for genuine binaries. Verbatim: *"It should say 'present several options with
  realistic trade-offs between them.' There should be a guard to avoid 2 question
  options unless it truly is a binary choice. It's more about encouraging diversity
  rather than a true ban."* So rule 1 is about the options being meaningfully
  different from each other, and the count is downstream of that. Padding to three is
  a violation of the rule, not compliance with it.
- **2026-09-15 — disclose interacting checkboxes as a combination option.** Verbatim:
  *"Add a section that IF checkboxes interact, these are disclosed as a 1+3 option
  later on down the list with explanation."* Read together with the opaque-label rule:
  the *concept* is `1+3`, the *label* must name both parts in words. Placement is
  after the singles, and the body has to say how they interact — the asymmetry being
  that you can see the interaction and the user cannot, so leaving it implicit hides
  the thing most likely to decide the answer.
- **2026-09-15 — ask when the design needs it; batch only what won't redirect the
  work; never bury a question in prose.** Verbatim: *"Batching is ok as long as the
  answer isn't likely to materially change the conversation. Asking as soon as the
  design needs the information is appropriate. Asking a question in the free text
  without a card should be discourage (the buried question problem that really does
  frequently happen)."* Note this is the opposite of the intuition that prose is the
  lighter-weight option: a prose question reads as commentary and gets skipped, and
  the failure is silent — a declined question and an unseen one look identical from
  this side. The card is what makes the ask legible as an ask.
- **2026-09-15 — real local time above every card.** Verbatim: *"Please also include
  printing the real local time above the question so that if a prompt is found from a
  long time ago in a chat I can see when it was asked."* Read from `date`, never
  guessed and never the session's start time, for the same reason the handoff ritual
  demands it: a plausible-looking wrong timestamp is worse than no timestamp, because
  it will be believed.
- **2026-09-22 — a card with no marked recommendation costs a whole round trip.** I put
  four genuinely different options for an approval decision, with costs on each,
  and marked no recommendation. He replied: *"What do you advise? Why is that one held out at
  the moment?"* — spending a turn to ask for the two things the card should already have
  carried. Rule 6 was written for exactly this and I simply omitted it, which is the
  common failure mode: the recommendation feels like pressure, so it gets dropped, and
  the user has to request it. Two things follow. **The mark is not optional politeness;
  withholding an opinion you hold is a wasted turn, not neutrality.** And note the
  *second* half of his question: he also wanted the mechanism behind the situation, not
  just the choice. So when a card asks the user to resolve a blocker, the lead-in must
  say plainly *why the blocker exists and what actually enforces it* — a card that
  presents options without the causal picture invites "explain first" instead of an
  answer. Both halves of that reply were symptoms of the same gap.
- **2026-09-23 — this skill outranks another skill's prose handoff.** After a design and
  plan were approved, I offered the two execution routes as prose ("**Which approach?**"),
  because `superpowers:writing-plans` prescribes that handoff *as literal prose text* to
  emit. He replied: *"Question card please"* — a whole round trip to get the format the
  rule already mandated. The reasoning that failed was "the other skill specifies the
  exact wording, so this is that skill's output, not a question of mine." That is wrong:
  it was a question offering options, so rule 10 applies regardless of which skill
  generated the options. **When another skill's template hands you a question to ask, take
  its OPTIONS and re-ask them as a card.** The template is specifying *what* to ask, never
  the presentation layer. Generalise: no upstream instruction to "ask X" licenses asking X
  in prose — if a skill, plan, checklist or doc tells you to pose a choice, the choice
  still arrives as a card. Worth noting the failure was invisible to me at the time: the
  prose read as compliance with a skill, which is exactly how a rule with a clear
  exception-shaped hole gets walked through.
- **2026-09-23 — I did not invoke this skill at all, and broke four rules at once.** Asked
  which new creature should replace a cut animal in a biome, and sent the card straight from
  memory of "roughly what a good card looks like". His correction: *"You didn't use my question
  card rule."* What the card actually got wrong, all four mechanical and all four covered above:
  **a `preview` on every one of the four options** (rule 8 — the one failure that costs the user
  their write-in line), **no marked recommendation** (rule 6, the second time this exact omission
  has been logged — see 2026-09-22), **no local time** (rule 9), and **`multiSelect: false` on
  options that were not mutually exclusive** — he wanted two of them and had to say so in the
  notes box, then hand-specify the second one himself. 🔴 The interaction he was reaching for was
  one I already knew and had not surfaced: the two he picked compose (one makes the water's *edge*
  lethal, the other its *body* impassable), which is precisely the combination option the checkbox
  section says to add. **The lesson is not "remember the rules" — it is that reasoning about a
  skill is not invoking it.** I considered loading this skill, judged the card simple enough to
  freehand, and shipped four violations in a single tool call; a 30-second read would have caught
  every one. ⇒ **Invoke before composing, never after being corrected.** Corollary worth keeping:
  when the options might reasonably be taken together, default to `multiSelect: true` — a
  single-select card silently asserts the options are rivals, and that assertion is often wrong.
- **2026-09-25 — the option cap is not four, and a preview killed the write-in for the third
  time.** Two corrections in one reply: *"You used an invalid question card that didn't let me
  type back to you. Use the skill. And ensure the skill allows as many options as you'd like in
  it, not just 3-4."* The first half is the preview failure **logged for the third time**
  (2026-09-15 origin, 2026-09-23, now) — I put previews on three of four options and the
  write-in line vanished, exactly as rule 8 predicts. Note the repeat pattern: on every one of
  the three occasions I had *not* invoked the skill before composing the card. That is now the
  single best predictor of a broken card, so it is worth stating as a causal claim rather than a
  coincidence. The second half is **new and is a genuine limit of the tool, not of the idea**:
  `AskUserQuestion` hard-caps `options` at four (`maxItems: 4` in its schema), so a card needing
  five or eight real alternatives cannot be expressed through it at all. His ruling is that the
  *question form* must not inherit that limit. Resolution adopted: when more than four genuinely
  different options exist, **draw the numbered card in the message body** and invite the answer
  there, where the user's normal input line is always typeable and unlimited in length. This is
  not the rule-10 prose-question anti-pattern — that targets a question *buried* in a paragraph
  with no visible options. An explicitly numbered, trade-off-carrying, clearly-announced card is
  a card regardless of which surface draws it. **Do not pad to four and do not silently drop the
  fifth option to fit the tool** — dropping is the worse failure, because the discarded option is
  invisible to the user and they cannot ask for what they were never shown.
- **2026-09-29 — a question closing a long report is still a question, and rule 10 is where I fail
  when nothing else in the card is wrong.** His correction was two words: *"Question cards"*. I had
  just delivered a multi-section review of a feasibility document and ended the final paragraph
  with *"Want me to apply the three corrections, or pick up the next step and get the benchmark
  actually running?"* — two options, in prose, at the end of a wall of findings,
  with no card at all. Note what is **new** here against the 2026-09-15 and 2026-09-25 entries:
  those were malformed *cards* (previews killing the write-in). This was **no card whatsoever**,
  and I did not notice, because the reply already felt complete — the analysis was the deliverable
  and the question read to me as a courteous sign-off rather than as a request for a decision.
  That is precisely the failure rule 10 describes and the reason its cost is silent: a question
  shaped like a sign-off gets answered only if the user happens to feel like answering it, and a
  skipped one is indistinguishable from a declined one. ⇒ **The trigger for a card is "am I asking
  for a decision", never "does this message feel like a question".** A long, satisfying report is
  an *aggravating* factor, not a mitigating one: the more substance sits above the question, the
  more the question reads as commentary. Practical check that would have caught it: before sending,
  scan the last two sentences for "want me to", "should I", "shall I", "or" between two courses of
  action — any hit means a card was owed. The 2026-09-25 causal claim also held again: **I had not
  invoked the skill before composing that reply.** Invoking it mid-turn after the correction is
  what surfaced the rule, three replies too late.
- **2026-10-15 — always recommend, but say when the pick is arbitrary.** Answering a review
  that argued a mandatory recommendation manufactures advocacy, verbatim: *"always review, but
  state if it's based on essentially a random choice"*. So rule 5 keeps the mark on every card
  and adds: when the options are equivalent, or the choice is his personal preference and the
  information to judge is missing, the one line of why says so plainly.
- **2026-10-20 — the card must carry its own context.** Asked how to answer a colleague's email about
  some questions, with the email's content only summarized in prose above the card, he
  refused the card verbatim: *"You didn't show me their question details. Question cards are
  supposed to provide all the context I need in the initial text block. You did not. Try again."*
  In focus mode the prose around a tool call may not be what he reads when the card is in front
  of him. ⇒ **When a decision answers someone else's message, quote that message's operative
  text (who, when, the exact ask) and any directly related reply inside the card's question
  text itself**, not only in surrounding prose.
- **2026-10-21 — the 2026-10-20 ruling was filed here but never folded into the rules, so it
  failed again.** Planning a fix for a browser permission prompt after two research passes, I asked "Which path should we start on?" with options naming the "bridge" and the
  "extension", findings only summarized in prose above. He refused it verbatim: *"You didn't
  educate me on what you learned at all, and you're referring to items that I haven't even read
  yet. Bridge? Extension? They weren't defined in the card. I thought we redefined the question
  card item to need much more than a single phrase as the question above? Did you use the
  question card skill?"* I had invoked the skill; the rule lived only in this log. ⇒ Folded in as
  rule 6: the question text teaches the findings and defines every term the options use.
- **2026-10-23 — the card covers what he is supposed to look at.** Verbatim: *"often I am shown a
  write-up in prose and even some art to look at or choices to consider, but then the Question Card
  starts and it completely covers everything I'm supposed to look at to make the decision. So we may
  need to print what I need to understand first and then say, 'After you read that, are you ready for
  a question card?' and pause there until I say yes if there are graphical elements to evaluate."*
  ⇒ Folded in as rule 10: visuals and long write-ups go first as plain messages, end with that
  exact line, and no card is sent until he says yes.
- **2026-10-23 — options listed WHAT, not WHY.** Verbatim: *"You need to specify for each option WHY
  we want to do this. This is just a list of WHAT it is and the details, but no motivation, no pro-con
  analysis. Try again"* (on a card about a maintenance task). ⇒ Rule 3 now leads each option
  with its motivation, then the pros and cons; a description that only restates the mechanism fails.
