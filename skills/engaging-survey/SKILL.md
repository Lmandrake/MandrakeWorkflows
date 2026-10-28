---
name: engaging-survey
description: Design, review or rewrite a survey or questionnaire so busy people want to answer it AND the answers are worth having; stakeholder and partner surveys, user-needs assessments, post-workshop or kickoff follow-ups, customer and community feedback forms, Google Forms / Typeform / Qualtrics drafts. Use whenever someone shares a survey draft, asks to "make this survey better / shorter / less boring / more engaging", asks what questions to put to users or partners, is turning a meeting or kickoff into a follow-up form, or calls a questionnaire long, dry, or a slog; even if they never say "survey" (e.g. "what should we ask the working groups", "draft the form for the stakeholders"). Not for bias-only wording audits of a finished instrument (a linter does that) or for interview guides alone.
---

# Engaging surveys: excitement in the frame, neutrality in the questions

## The one idea

People answer when **trust × reward outweighs effort** (Dillman's social exchange, as Caroline
Jarrett puts it). A survey about something exciting usually fails by being long and dry. The fix is
to put the energy in the **frame**: who is asking, the picture of what this makes possible, what
happens next, the thank-you. The **questions** stay neutral, concrete and quick. An exciting frame
with neutral questions gets both enthusiasm and honest data. Loaded or promotional questions get
neither (AAPOR: a survey must not be used to sell or to produce a predetermined result).

So for every draft you touch, do two separate jobs: **cut and sharpen the questions**, then
**write the frame**. Don't mix them.

The evidence behind each rule, with sources, is in `references/evidence.md`. Read it when you need
to justify a recommendation to the survey's owners; quoting their own field's guidance persuades
better than your opinion does.

## Step 1. Name the decisions before touching a question

Ask, or infer from the material: *what will the owners do differently depending on the answers?*
Write 3–6 decisions down (e.g. "which working groups to staff first", "which heat variable to
prioritise for the first product"). Then go through every question in the draft:

- **Keep** it only if you can name the decision it feeds and the number or pattern you'd look at.
- **Move** it to a focus group, interview or working-group agenda if it asks people to explain a
  workflow, describe constraints, tell a story at length, or design a solution. Those are
  conversation jobs. The NASA Earth Action Co-Development Toolkit (MSFC, 2026) gives surveys the
  job of measuring *how common* a need is; interviews and focus groups get decision context,
  workflows and workarounds.
- **Cut** it if no decision depends on it ("nice to know"), or if another question already covers
  it.

Present this as a table: question → decision it feeds → keep / move (where) / cut. The owners can
see why each cut happened, and the moved items become a gift to the next meeting, not a loss.

## Step 2. Set an honest budget

Default target: **2–5 minutes, about 8–12 items including identification.** The MSFC toolkit notes
surveys under 2 minutes get the most feedback; practitioners cite ~15 questions / 10–12 minutes as
the outer edge for volunteers. If the owners need more, **split by purpose**: a short one now (e.g.
"how did the kickoff land, how do you want to be involved, who else should we ask") and a second,
targeted one later. Don't argue for a longer single survey with skip logic: every branch question
is still a click, and skipped sections don't shorten what the respondent first sees.

Run `scripts/survey_budget.py <draft.md>` to count items, open-text boxes and long option lists
and to estimate completion time. Quote its number rather than the draft's own claim ("takes 12–15
minutes") when they disagree. The estimate is a rule of thumb (≈10 s per single choice, ≈45 s per
open box); say so.

## Step 3. Sharpen the questions you kept

These make questions easier and more pleasant to answer without leading the respondent:

- **Anchor in one real, recent moment** rather than the abstract. "Think of the last heat event
  your team responded to. What was the first decision you had to make?" beats "What heat-related
  decisions does your organization make?" People like telling a short story about their own work.
- **Ask for advice, not feedback or ratings of the past.** "What advice would you give us so this
  is useful to you?" Yoon et al. (2019) found "advice" requests drew 34% more areas to improve and
  56% more ways to improve than "feedback" requests.
- **Prefer "pick your top three" to "select all that apply".** Select-all lists of 10+ items are
  tedious and every item gets ticked; a forced top three gives a ranking you can act on.
- **Closed answers by default, with "Not sure" when it's a real answer** (GOV.UK). Open text: at
  most one or two, with **small boxes** and a one-line reason to answer ("one sentence is plenty").
  Large boxes raise blanks (Zuell et al. 2015).
- **One idea per question.** Split double-barrelled items; don't ask a respondent to define units,
  thresholds and timing in one breath.
- **Use their words, not yours.** Replace program jargon and acronyms with the respondent's
  vocabulary; offer a picture or one-line definition when a technical term is unavoidable.
- **A scenario may set up a question, but must not argue for an answer.** "It's a 105°F August
  afternoon" is fine; "Given how dangerous heat is, how important is…" is leading.

If a bias audit is wanted on top, a deterministic linter exists (`lonelydoctor/survey-linter`, MIT);
this skill is about engagement and scope, and does not replace it.

## Step 4. Write the frame (this is where the excitement goes)

Write each of these, in the owners' voice, short:

1. **The invitation** (email or message). From a named person the respondent knows, personally
   addressed, not from a list. Say in the first line what it's for and how long it takes ("4
   questions, about 3 minutes"). Give one concrete reason this matters *to them*.
2. **The opening screen.** One vivid sentence of the picture (what this makes possible, for whom,
   by when), then the honest time, then "your answers decide X". No paragraphs of program history.
3. **Progress they already made.** If they attended, contributed or signed up, say so ("You started
   this at the kickoff"). Endowed progress (Nunes & Drèze 2006) is a small but real nudge.
4. **Section lead-ins of one line** that tie each block to a decision ("These three tell us which
   working group to launch first").
5. **The close and the promise.** Thank them, say what happens next and *when they'll see results*
   ("We'll share what we heard at the next partner meeting"). Then keep the promise: the
   reward that sustains future response is being visibly heard.
6. **The deeper invitation.** Offer the conversation as the reward, not the burden: "Want 30
   minutes with the team to dig into your use case? Tick here." That routes the rich material
   (Step 1's "move" pile) to where it belongs.

## Step 5. Check the platform and the rules before anyone builds it

- **Google Forms branches only on one multiple-choice or dropdown question at a time**, never on
  checkboxes and never on combinations of answers. "Show the sections for every group you ticked"
  can't be built natively; use a single-choice gate or one Yes/No per section.
- **Federal surveys of the public can need clearance.** In the US, a federal agency asking the same
  questions of many non-federal respondents may fall under the Paperwork Reduction Act. Agencies
  hold generic clearances (NASA's include one for meetings and workshops) that a short event
  follow-up may fit and a long needs assessment may not. Flag this as a question for the owners;
  don't rule on it.
- **Contact details and facts you carry over.** An email address, a date or a "the board meets
  monthly" claim copied from the draft into your rewrite becomes your error too. Check each against
  another source (the person's own mail signature, the calendar) or mark it "confirm before
  sending"; don't silently reuse it.
- **Consent and confidentiality.** Say how answers will be used and who sees names; if names are
  collected, don't promise anonymity.

## Step 6. Pilot it on two or three real respondents

Jarrett: the only way to know a question is good is to test it on people who will answer it. Have
two or three friendly members of the audience take it while someone watches or times them. Fix what
they stumble on. A survey nobody piloted gets fixed by its respondents instead.

## What to hand back

When reviewing someone's draft, deliver, in this order:

1. **One-paragraph verdict**: current length and estimated time, the main problem, the proposal.
2. **Decisions list** (Step 1) and the **keep / move / cut table**.
3. **The rewritten survey**: frame pieces (Step 4) and the kept questions, numbered, with answer
   options and any branching written as a plain rule.
4. **The "move to conversation" list**, grouped by where it goes (focus group, interview, working
   group), so nothing the owners cared about is lost.
5. **Errata separately**: mechanical errors (numbering, broken skip logic, wrong contact details,
   factual claims to confirm). Keep errata apart from design advice so they get fixed even if the
   redesign is declined.

When writing a survey from scratch, skip 2 and 5 and deliver the decisions, the survey with its
frame, and the move-to-conversation list.

## Pitfalls

- **Rewriting questions to sound exciting.** Exclamation marks and superlatives in question stems
  are leading. Put energy in the frame.
- **Treating skip logic as length reduction.** Respondents feel every screen and every gate.
- **Gamification as the fix.** Points, badges and animated scales show mixed effects, mostly on
  consumer panels. A scenario, a top-three pick and a clear "this decides X" are enough play.
- **Keeping a question because someone senior wrote it.** Name its decision or move it; offer the
  conversation route so the cut costs the author nothing.
- **Promising results and not sending them.** That spends the trust the next survey needs.
