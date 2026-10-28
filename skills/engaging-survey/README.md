# engaging-survey

A Claude Code skill for designing or reviewing surveys that busy people want to answer and whose
answers drive decisions. Born from a stakeholder-survey review.

The rule it rests on, **excitement is a framing problem, not a question
problem.** Energy goes in the invitation, the opening picture, the progress already made, and the
promise of what happens next; the questions stay neutral, concrete and few.

- `SKILL.md`: the workflow (decisions first, honest budget, sharpen, frame, platform and PRA check,
  pilot) and what to hand back.
- `references/evidence.md`: the research notes behind each rule, with sources (NASA Earth Action
  Co-Development Toolkit, Yoon et al. on advice vs feedback, Jarrett/Dillman, AAPOR, GOV.UK,
  Superhuman, conversational surveys, Google Forms limits, PRA).
- `scripts/survey_budget.py`: counts questions, open boxes and long lists in a markdown draft and
  estimates completion time (rule of thumb, not a measurement).

## Install

```sh
ln -s "$(pwd)/skills/engaging-survey" ~/.claude/skills/engaging-survey   # from the repo root
```
