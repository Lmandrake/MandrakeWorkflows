# Tidewater — Buoy Calibration Review after the Dock Tank Test

> **Invented example.** Tidewater, its buoys and every participant are fictional, written to show
> this skill's conventions. No real meeting is described.

**Date / time:** 2031-03-12, a short review call (about three minutes recorded).
**Participants:** Odalys Okafor (field lead, ran the dock test), Teodor Lindqvist (instrument
technician), Tamsin (data lead, alert product), and an unnamed chair (Speaker 1).

This summary is selective; `source/2031-03-12_tidewater_buoy-calibration-review.txt` holds
everything said.

**Transcription note.** "Oda Lys" is **Odalys** Okafor (she answers to it at 00:00:09). "see tee
dee" is a **CTD**, the reference instrument. **Speaker 3 is almost certainly Tamsin**: the chair
addresses "Tamsin, from the data side" at 00:01:38 and Speaker 3 answers about the alert product;
inferred, not certain. **Speaker 1**, who chairs, is unresolved.

- **Okafor** reported that five of six buoys agreed with the reference to about a tenth of a
  degree in the tank test on 2031-03-06 ("last Thursday"), and that **buoy four reads warm by
  almost half a degree**, worse in sun. Shading cut the offset to about 0.15, so she blamed a
  thinner, different-batch paint on its housing.
- **Lindqvist** objected that buoy four alone had its **thermistor swapped in January**, and that
  "The shade test doesn't separate those two, because shading cools the sensor too." **Okafor**
  conceded: "I can't rule out the thermistor from one afternoon." Lindqvist proposed swapping
  thermistors between buoys two and four, "a one day job"; Tamsin asked him to log internal
  temperature on the spare channel while in there, which he put at about two hours.
- The surprise came from **Tamsin**: the bias barely matters for the seasonal average, but the
  marine heatwave alert fires on **any single buoy** above **1.5 degrees** for six hours, so "half a
  degree of bias on one buoy is a third of the threshold." Okafor said she "didn't realise the
  alert used single buoys." The chair ruled buoy four **out of the alert, kept in the seasonal
  average**; Lindqvist and Tamsin agreed.

## Key Dates & Action Items

**Dates**
- 2031-03-17 ("Monday") thermistor swap; answer by 2031-03-18 ("Tuesday night").
- 2031-03-19 ("Wednesday the nineteenth") decision meeting.
- 2031-03-24 ("the twenty-fourth") boat booked; buoys redeploy.

**Action items**
- **Tamsin** — remove buoy four from the heatwave alert today (a config change).
- **Lindqvist** — swap the thermistors of buoys two and four, and wire internal-temperature logging.
- **Okafor** — if the offset stays with the housing, repaint all six buoys from one paint batch
  before 2031-03-24.
- **Everyone** — record the swap results in the shared sheet, not email, so the alert change has
  its reason beside it (Tamsin's request; the chair agreed).
