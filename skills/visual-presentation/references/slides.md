# Static-slide core (absorbed from technical-presentation, rules unchanged)

These are technical-presentation's rules, moved here unchanged (owner ruling Q1, 2026-10-28). They
govern every slide whether or not anything on it moves. The motion rules in `SKILL.md` sit on top.


## The one idea: every slide makes a claim and then defends it

A slide is an argument, not a container. The room should be able to read only the titles, in order,
and get the whole story. Everything else on the slide is there to defend its title.

## 1. Title = the takeaway; subtitle = what this slide holds that supports it

Write the title as the conclusion, the principle, or the high-level idea the viewer should leave with.
Write the subtitle as a plain description of the evidence on the slide.

An example: **"Moving to the new scheduler breaks only 2 of 140 service checks: An analysis of
existing test robustness."**

| | Good | Bad |
|---|---|---|
| Title | Existing checks mostly survive the scheduler change | Service-check sweep, rev 4 |
| Title | Start from today's checks, extend them only on evidence | Principle 1b |
| Subtitle | How three readings of each check's own purpose narrowed 64 flags to 2 | 64 − 47 = 17; 3 + 14 → 2 + 15 |

Then the slide **must defend that statement directly**. If something on the slide does not support
the title, cut it or move it to another slide whose title it does support.

## 2. Primary bullets are spoken; secondary text is for the eye

- **Header blocks and primary bullets are what the presenter says out loud** to lead the discussion.
  Write them as short full thoughts the presenter can speak as written.
- **Subtext and secondary bullets beneath them are data to review visually**: quotes, citations,
  counts, examples. The presenter does not talk through them unless someone asks.

So a slide reads at two speeds: the spoken layer carries the argument, the visual layer lets a
skeptic check it. Keep the spoken layer to a few items; the visual layer may be denser but stays
subordinate in size and weight.

## 3. No arithmetic in titles, subtitles or bold

- A number belongs in a title only when it **is** the takeaway ("breaks only 2 of 140").
- Sums, reconciliations and step-by-step tallies (`a + b = c`, `x → y`) never go in a title, subtitle,
  header or bold text. If numbers on a slide must reconcile, keep them consistent, and if showing the
  reconciliation genuinely helps, put it in small secondary text or the speaker notes.
- Prefer words for the shape of a result: "a second reading withdrew most of the flags" beats
  "64 − 47 = 17".

## 4. Open with where we stand, then the plan, then the method

A working deck answers "where are we, and now what?" before any detail:

1. **Where we stand**, in one slide: what exists now, and how preliminary it is.
2. **The process we propose**, in one slide, right up front: the whole path from input to output
   (for policy work: risks → coverage → gaps → mitigations → policy changes and guidance updates),
   with one line on what each step produces.
3. **The methods**, one slide per idea, each titled by what it lets us do.
4. **What we tested, on how much, and why that small**: say plainly when a trial is deliberately
   narrow (a few cases, one document) to test the workflow and get feedback before scaling.
5. **What we want from the room.**

## 5. Examples, names and plain words

- **Every abstract category gets a concrete example** beside it: a named risk, a named rule, a case.
- **Never put a colleague's name on a slide face or in the notes.** Describe the thing; provenance lives
  in repo files.
- **Plain words first, official terms in parentheses** (assurance, like this). Never a private project
  shorthand ("item 7", "rung 2") on the spoken layer; if a label is needed for cross-reference, it
  goes in the secondary text after the plain statement.
- **Each slide's speaker notes open with its one-sentence takeaway**, which should match the title.

## 6. Draft in markdown first when the user asks for speed

A markdown outline lets the user fix the argument before anyone spends time on layout. Use this shape per
slide, so the conversion to pptx is mechanical later:

```markdown
## <N>. <Takeaway title>
*<Subtitle: what this slide holds that supports the claim>*

- **<Spoken point>**
  - <visual-only support: quote, citation, number, example>
- **<Spoken point>**
  - <support>

> Notes: <one-sentence takeaway>. <anything the presenter needs but should not show>
```

## Self-check before showing the user a deck

Read only the titles in order. Do they tell the story as conclusions? Then, slide by slide:

- Does the subtitle say what evidence is here, in plain words?
- Does everything on the slide defend the title?
- Are the spoken bullets few and speakable, with data pushed into secondary text?
- Any `+`, `−`, `=`, `→` arithmetic in a title, subtitle or bold? Remove it.
- Any project shorthand, colleague name, or category without an example on the face?
- Does the deck open with where we stand and the one-slide process?
