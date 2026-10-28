# Engaging stakeholder surveys: research notes (2026-10-23)

Gathered while reviewing a real stakeholder-survey draft, and as the evidence base for an
"engaging survey" skill. The raw fetches are kept privately and are not part of this skill; each claim below links its
public source where one exists. Text only.

**What was read in full** is marked ●; **abstract or metadata only** is marked ○. Claims below cite
the file they came from. Nothing here is from memory unless marked *(background, unverified here)*.

## How the search went

**Brainstorm 1 (where to look):** survey methodology (length/breakoff, satisficing, open-ended
items, social exchange); conversational and gamified surveys; NASA Earth Action and Applied
Sciences guidance, SNWG, SPoRT; NOAA/NWS social science; the Paperwork
Reduction Act; Anthropic's own interviewing work and skill-authoring docs; practitioner canon (Pew,
AAPOR, Superhuman's PMF survey, the Mom Test, Typeform, Google Forms); GitHub skills..

**Brainstorm 2 (after wave 1):** the MSFC co-development toolkit was the surprise, so: what makes
busy professionals *want* to answer (advice framing, authority of sender, reciprocity, closing the
loop); prioritisation formats that feel like play (Buy a Feature, MaxDiff, Kano); government UX
manuals (GOV.UK, 18F, digital.gov, OMB A-11 §280); heat-specific stakeholder work (NIHHIS, Heat
Action Hub); UX critics of surveys (Erika Hall, Caroline Jarrett)..

**Wave 3:** gamification evidence, endowed progress, vignettes/scenarios, invitation personalisation,
Google Forms branching limits, NWS heat social science, existing Claude survey skills..

## What we found

### 1. The partners already wrote the rulebook, and it says "under 2 minutes"
● **NASA Earth Action Solution Co-Development Toolkit v0.1** (EarthRISE with SPoRT and NSITE, MSFC,
2026-04-28; Zenodo 10.5281/zenodo.19866469).
- Surveys are "short structured instruments used to reach many respondents quickly and quantify
  needs", best for prevalence and stratifying by user type; "*Note: shorter surveys (under 2 mins.)
  receive the most feedback.*" (p. 48).
- Surveys belong at Step 3 (broad decision context, validating needs at scale) and Step 6
  (validating findings). Decision workflows, authority, constraints are interview and focus-group
  work (pp. 49–51).
- Its interview prompts (pp. 55–57) are the best source of *questions people like answering*:
  "Think back to the last time you had to [decision]. Can you walk me through it?"; "When things
  don't quite line up, how do you work around it?" (workarounds reveal must-haves); "If we could
  only improve one part of this process, what would make the biggest difference?"; "Who else should
  we talk to?"; and "hold back on proposing solutions early".
- **Use:** cite their own toolkit when proposing the cut. It turns "your survey is too long" into
  "let's follow your own agency's toolkit".

### 2. Ask for advice, not feedback
● Yoon, Blunden, Kristal & Whillans, *Why Asking for Advice Is More Effective Than Asking for
Feedback*, HBR, 2019. Across four experiments, people asked for "advice" rather
than "feedback" gave 34% more areas of improvement and 56% more ways to improve. Feedback reads as
evaluation of the past; advice invites people to imagine the future.
- **Use:** "Help us design the tool you'd want in two years" beats "Please rate".

### 3. People answer when trust × reward outweighs effort
● Caroline Jarrett, *Surveys That Work* webinar slides (<https://www.effortmark.co.uk/wp-content/uploads/2021/03/Surveys-that-work-webinar-for-FocusVision.pdf>, CC BY-SA), after Dillman's
Tailored Design Method. Response = trust, then perceived reward against perceived effort. Every
question must earn a "so what": "the aim of a survey is to get a number that will help with a
decision". Test the questions on people who will answer them. "Asking one person the right question
gets better results than asking 10,000 people the wrong question." Rough response rates: an email to
a selected group for a one-off survey reaches up to 20%, and 20 questions pull that down.
● Erika Hall (<https://www.userinterviews.com/blog/erika-hall-on-why-surveys-almost-always-suck>): start from "what do we want to learn", not "we're running a survey,
what should we ask?".
- **Use:** for each draft question, write down the decision it feeds. Cut any question that feeds
  no decision.

### 4. Tiny surveys can drive real decisions
● Superhuman's product-market-fit engine (First Round Review, <https://review.firstround.com/how-superhuman-built-an-engine-to-find-product-market-fit/>): four questions only:
"How would you feel if you could no longer use X?" (very / somewhat / not disappointed), "What type
of people would most benefit?", "What is the main benefit you receive?", "How can we improve X for
you?". Directional at about 40 respondents. Each answer feeds a named decision.
- **Use:** a four-to-six question pulse is a credible instrument, not a compromise.

### 5. Conversation beats text boxes for the rich material
○ Xiao et al., *Tell Me About Yourself*, ACM TOCHI 2020 (<https://doi.org/10.1145/3381804>, abstract): n ≈ 600 field
study; a chatbot conversational survey drew significantly more engagement and better free-text
answers (informative, relevant, specific, clear) than a Qualtrics survey with the same questions.
● Anthropic Interviewer (<https://www.anthropic.com/research/anthropic-interviewer>, <https://www.anthropic.com/about-anthropic-interviewer>, <https://www.anthropic.com/research/your-thoughts-on-ai>): 1,250 AI-run interviews
of 10–15 minutes. 97.6% rated satisfaction 5 or higher out of 7, 96.96% said it captured their
thoughts, 99.12% would recommend the format. Plan → interview → analyse, with humans reviewing the
plan. Note the crowdworker selection bias, which the post admits.
○ Answer-box size (Zuell et al. 2015, <https://doi.org/10.1177/0894439314528091>, abstract): large open-text boxes *raise* item
nonresponse; a short motivation text raises response.
- **Use:** keep open text to one or two small, motivated prompts. Route depth to focus groups
  where partners offer them, or (later, with clearance) a conversational follow-up.

### 6. Excitement must live in the frame, not in the questions
● AAPOR *Best Practices* (<https://aapor.org/wp-content/uploads/2023/06/Survey-Best-Practices.pdf>): surveys "should not be used to produce predetermined
results, campaigning, fundraising, or selling". ● AAPOR *Question Wording* (<https://aapor.org/wp-content/uploads/2023/01/Question-Wording.pdf>):
leading wording and context effects bias the answers.
● GOV.UK *Designing good questions* (<https://www.gov.uk/service-manual/design/designing-good-questions>): closed questions are easier; allow "I'm not
sure"; split complex questions; change the question until it works in testing.
- **Use:** put the energy in the invitation, the opening picture, the "what happens next" and the
  thank-you, which carry no measurement risk. Keep each question neutral and easy. An exciting frame
  plus neutral items is how you get enthusiasm *and* honest data.

### 7. Google Forms constrains the design
● PlatoForms guide (<https://www.platoforms.com/blog/google-forms-conditional-logic/>): native branching works only from one multiple-choice or
dropdown question, never from checkboxes, and never combines answers. A design that says "show only the sections
you ticked" cannot be built natively.

### 8. Federal surveys of the public may need PRA clearance
○ NASA PRA generic clearances (public clearance listings): NASA holds, among others, *2700-0153 Generic
Clearance for the Collection of Qualitative Feedback on Agency Service Delivery* and a *Generic
Clearance for Conferences, Meetings, Workshops, Registrations and Challenges*. ● The NWS space-weather
user-needs survey (<https://www.weather.gov/media/nws/Results-of-the-First-National-Survey-of-User-Needs-for-Space-Weather-2024.pdf>) needed PRA clearance of its instrument, which took from December
2021 to June 2023, and still ran mostly as focus groups.
*(background, unverified here: the PRA generally applies to identical questions put to ten or more
non-federal respondents by or for a federal agency.)*
- **Use:** ask the survey's owners whether it falls under the agency's meetings/workshops generic clearance. A
  kickoff follow-up probably fits; a long needs assessment probably does not. This is a
  real reason to keep it short and framed as kickoff feedback.

### 9. Smaller levers (thinner evidence)
○ Endowed progress (Nunes & Drèze, J. Consumer Research 2006, <https://doi.org/10.1086/500480>): people work harder
toward a goal when shown they have already started. *Use:* "You've already done step one by coming
to the kickoff."
○ Personalised salutations raise response among scientists (DZHW, <https://doi.org/10.31235/osf.io/cvtna>). *Use:* send it
from the project lead, by name, to each person.
○ Gamification: the search hits (Keusch and Zhang's review, among others) are mixed and mostly
consumer panels; not strong enough to lean on. Light play (pick your top three, a scenario) yes;
points and badges, no.
● Buy a Feature (Hohmann, <https://www.lukehohmann.com/innovation-games/buy-a-feature>): a priced-feature budget game, fun and revealing in a
workshop. A natural working-group exercise rather than a Forms question.
● SPoRT stakeholder summits (the SPoRT "summits" web page): MSFC's existing engagement is seminars and summits
with users presenting their own use, which supports routing depth to focus groups.

### 10. Existing skills to borrow from
● `lonelydoctor/survey-linter` (<https://github.com/lonelydoctor/survey-linter/blob/main/SKILL.md>, MIT): a Claude skill plus deterministic CLI for
leading, double-barreled and unbalanced items. It covers *bias*, not *engagement*, so it complements
rather than replaces what we want. ● `cookiy-ai/user-research-skill` (<https://github.com/cookiy-ai/user-research-skill/blob/main/SKILL.md>).
● Anthropic skill-authoring best practices (<https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices>) and `anthropics/skills` skill-creator
(<https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md>), for the build step.

## Not reached
Galesic & Bošnjak 2009 (the length/breakoff experiment): metadata only, no abstract. 18F "beyond
surveys": only a Wayback shell came back. AMS SNWG assessment-process paper: 403. Puleston's
gamification work: not found in the open indexes.
