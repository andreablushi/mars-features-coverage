# Picking the best time window, explained simply

You have one feature, say Jezero crater, and three instruments that have all
looked at it, over about fifteen years. You want **one stretch of time** to
study. Not the whole fifteen years: a stretch.

A good stretch is one where:

- the observations are **close together in time**,
- **each instrument** covers as much ground as it can,
- there is **always at least one SHARAD track**, and ideally all three
  instruments are in there together.

---

## The steps, end to end

Before the reasoning behind any of it, here is everything the code does, in
order. Steps 1 to 6 build the timeline (`models/track.py:48`) and the rest is
the search over it (`algorithm.py:14`). `verdict.assess` (`verdict.py:61`) is
what calls both.

1. **Take each instrument set's observations**, every one the pipeline
   computed for the feature (`models/track.py:61`).
2. **Throw away the grazes.** An observation is kept only when it fills at
   least 2 cells of the feature's grid and covers at least 1 km2 of it. A
   sounder track has to cross at least a tenth of the feature's width as well
   (`filters/admissible.py:11`).
3. **Throw away the empty sets.** A set that observed the feature but filled
   none of its cells is dropped whole, rather than dragging every score it
   appears in down to nothing (`models/track.py:70`).
4. **Merge what is left onto one axis**, sorted by start time, oldest first
   (`models/track.py:80`). If nothing survives, the feature has no survey and
   the search stops here (`models/track.py:72`).
5. **Count what each set holds in total**, meaning the different cells it fills
   across its whole record (`models/track.py:93`). Every share later is measured
   against this.
6. **Check a sounder survived** (`algorithm.py:24`). With no admissible sounder
   track left anywhere, there is no survey and the search stops.
7. **Insist on every instrument the feature has** (`algorithm.py:31`).
8. **Work out the ceiling**, the score the whole record reaches from its first
   observation to its last (`algorithm.py:35`). The rungs climb towards this,
   not towards a perfect score.
9. **Climb 49 rungs**, from nothing up to that ceiling (`algorithm.py:36`). At
   each rung, slide a window along the axis and keep the shortest one clearing
   that rung while holding a sounder track and the instruments being insisted
   on (`algorithm.py:45` to `algorithm.py:58`).
10. **Stop climbing** at the first rung where nothing qualifies, or where the
    shortest window that does runs longer than a Mars year
    (`algorithm.py:60`).
11. **If the ladder produced nothing at all**, insist on one fewer instrument
    and go back to step 8 (`algorithm.py:66`). When even one instrument
    produces nothing, give up (`algorithm.py:68`).
12. **Take the bend.** Rescale both axes of the curve those windows trace to
    0..1 (`src/utils/maths/quantities.py:39`) and take the window furthest above the diagonal
    (`algorithm.py:73` to `algorithm.py:81`). When none sits above it, take
    the longest window on the curve instead.
13. **Pull in the ties.** Anything sharing an exact timestamp with either end
    of the chosen window joins it and the window is rescored
    (`models/window.py:31`, called at `algorithm.py:63`). It does not get a second
    longer.
14. **Mark the redundant observations** inside it (`filters/redundancy.py:10`, called at
    `algorithm.py:90`).
15. **Fill in the scorecard** and decide whether the feature is kept at all
    (`verdict.py:61`).

---

## Every number the search uses

All of them live in `configs.py`, and nothing else about the search is tunable.

| Name | Value | Where | What it decides |
|---|---|---|---|
| `MIN_AREA_KM2` | 1.0 | `configs.py:22` | An observation has to cover at least a square kilometre of the feature (`filters/admissible.py:27`). |
| `MIN_CELLS` | 2 | `configs.py:23` | It also has to fill more than a single cell of the feature's grid (`filters/admissible.py:24`). |
| `MIN_CROSSING` | 0.10 | `configs.py:27` | A sounder track has to cross at least a tenth of the feature's width (`filters/admissible.py:34`). |
| `MIN_GAIN_CELLS` | 1 | `configs.py:33` | How many cells an observation must add that its own set did not already hold, to count as bringing ground of its own (`filters/redundancy.py:27`). |
| `MIN_SETS` | 2 | `configs.py:30` | A feature is kept only when its window holds at least two instruments (`verdict.py:138`). |
| `MAX_SPAN_DAYS` | 687.0 | `configs.py:7` | No window may run longer than one Mars year, which is every season the feature has (`algorithm.py:60`). |
| `LEVELS` | 48 | `configs.py:11` | How many steps the ladder has, so 49 rungs counting the one asking for nothing (`algorithm.py:36`). |
| `ROUNDING` | 1e-9 | `configs.py:14` | A share is added cell by cell, so a window landing a rounding error under a rung is let through anyway (`algorithm.py:51`). |
| `DAY_SECONDS` | 86400.0 | `configs.py:17` | Every timestamp is divided by this, so a span is a number of days (`models/track.py:86`). |

---

## What counts as an observation

Not every footprint that touches the feature is a look at it. A strip can pass
by and clip the corner, landing a handful of pixels inside, all of them on the
boundary, where a pixel is half feature and half whatever lies beside it. Those
are dropped before anything is counted.

Two things are asked of every observation, and a sounder is asked for a third.

**A square kilometre of ground inside the feature.** That is enough to crop
something out of. It is measured in ground and not in the instrument's own
pixels because a pixel is not a fixed thing: a quarter of a metre across for
HiRISE, five metres for CTX, a hundred and eighty for CRISM, and for SHARAD a
single radar trace covering more than a square kilometre by itself.

**More than one cell of the feature's grid.** This is the floor that knows how
big the feature is. The grid follows the cube root of the feature's width, so
two cells is a tenth of a percent of a small crater and a hundredth of that of
a continent, which is a size scaling a floor in kilometres cannot have.

**A tenth of the feature's width crossed, for a sounder.** A track reports a
line, and neither floor above can tell a line that crosses the feature from one
that enters it and stops. Both lay about the same ground inside, and both fill
few cells, because a line always fills few. Length is what separates them, and
the ground a track lays divided by the swath it sounds gives that length back
for nothing. Over 50,165 tracks the median crosses a third of the feature's
width, and the rule drops the fifth of them that cross less than a tenth.

Each floor binds a different instrument, which is the whole point of having
more than one. Ground binds CTX, CRISM and HiRISE, whose pixels are metres
across. Cells and the crossing bind SHARAD and MOLA, whose pixels are
kilometres across, and for which a ground floor is something a corner clip
clears on its own.

Two rules were tried and are not here. A floor in the instrument's own pixels
cannot work: nine pixels is 0.0003 km2 of CTX and 11.7 km2 of SHARAD, so any
number strict enough to bite on one deletes the other, and a nine trace floor
throws away a track crossing a small crater end to end, which is only two or
three traces long. A percentage of the feature cannot work either: a CRISM
observation covers 0.03% of its feature at the median and a HiRISE one 0.01%,
because seeing a small part of a big feature in detail is exactly what those
instruments are for, so any percentage worth writing down deletes them.

The dropping happens on the way onto the timeline, before a single total is
taken, so each set is scored against the ground its real looks reached. Doing
it later would measure every window against ground the dataset has already
decided is not there.

It is a light touch on most features and a heavy one on a few. Across all 1,918
features it turns away a median of 1.7% of the observations and 2.7% of them on
average, but Hyblaeus Catena loses 15 of its 17, and Noachis Terra 7,360 of its
63,442.

What it does not do is move the answer about. On 150 features the search was run
twice, once with the floors and once without: not one of the 147 that had a
window lost it, and 132 of them settle on the same stretch of time either way.
The 15 that move do so by half a day at the median, though the one that moves
most stretches by 370 days once the tracks that only grazed it stop counting.

*Code: all three floors are one function, `admissible` (`filters/admissible.py:11`), with the crossing rule at `filters/admissible.py:34`, applied on the way onto the timeline at `models/track.py:65`.*

---

## What "ground" means here

The feature is cut into a grid of small squares (cells). 
A window's ground is the number of **different** cells an observation uniquely fills, not the sum.
Every instrument is scored against **itself**:

```
reach of an instrument = cells it fills inside the window
                         ------------------------------
                         cells it fills in its whole record
```

So `1.0` means "this window gives you everything that instrument ever gave you for this feature".

A window's score is those instrument scores **multiplied together and rooted**,
not averaged. The next section is about why.

*Code: a set's share is `reach.py:83`, its total across the record `models/track.py:93`.*

---

## How the grid and the totals are built

Everything here is done once, on the way onto the timeline (`models/track.py:48`),
and the result is the `Track` the search walks (`models/track.py:17`).

**The cells.** The analysis stage cuts the feature into a grid of small squares
and hands every observation a bitmask of the cells it fills. The search never
touches geometry. It unpacks that mask into a list of cell numbers once
(`models/track.py:63`), and from then on an observation is a list of numbers and a
timestamp.

**How many cells there are.** The analysis stage reports how many cells fall
inside the feature, which on a feature whose outline curves is fewer than the
rectangle the grid was cut from. The search takes whichever is larger, that
count or the highest cell number anything actually filled plus one
(`models/track.py:96`), so there is always room for everything that arrived.

**The totals.** A set's total is the number of different cells its admissible
observations fill across the whole record (`models/track.py:93`). This is the
bottom of its share (`reach.py:83`), so every set is scored against itself and
never against the feature. A set filling 40 cells in total and 10 inside the
window reaches 25%, whether the feature has 50 cells or 50,000.

**The width a sounder is measured against.** The feature's width is the side of
a square of the same area, so the square root of its area in square kilometres
(`models/track.py:59`). A track's length inside the feature is the ground it laid
there divided by the swath it sounds (`filters/admissible.py:33`), which gives the
length back with no track geometry to carry around.

**What is remembered about the rejects.** The timestamps of the observations
turned away are kept, and so is how many of them were sounder tracks
(`models/track.py:97`). That is what lets the scorecard tell a feature no sounder
ever flew over from one whose only tracks grazed its edge (`verdict.py:89`).

---

## Why the shares are multiplied and not averaged

An average lets one instrument carry a window on its own. A hundred percent
beside two ones averages a third, and so does a window that serves all three
instruments evenly, so the average cannot tell them apart. It was not a
theoretical worry: measured across the windows the average picked, the spread
between the best and worst instrument ran to 61 points at the median, a quarter
of the windows held an instrument at exactly nothing, and a third of them had
the best set above half while the worst sat under a twentieth. Tile scored 30%
on shares of 90, 0 and 0.

Multiplying the shares and taking the root of them refuses that. The same
100/1/1 comes to 5%. Only a window that brings every instrument along scores
well, and a window missing one scores nothing at all.

It turned out to cost nothing. Over 53 features, against the average: the worst
instrument's share doubled, from 6.3% to 12.3%. Lopsided windows halved, from
28% to 15%. And the median window got **shorter**, 185 days to 169, because a
curve limited by its laggard flattens sooner and the bend arrives earlier. No
feature lost a third instrument. Across all 1,777 windows that are kept, the
worst instrument now reaches 13.5% at the median and the spread between best
and worst is 47 points, where the average left it at 61 on the features it was
measured on.

Something more direct, like the average minus its own spread, cannot be used
here. The sweep is exact only because the score never falls as the window
grows, and a spread penalty falls exactly when the instrument already ahead
gains more ground. Every score that rises with each instrument's share and
never falls is safe, which is the whole family from the average down through
the geometric mean and the harmonic mean to the plain minimum. Two of those
were tried beside this one: the minimum holds the spread tighter still, 18
points against 41, and the harmonic mean sits between them but stretches the
median window to 215 days. The geometric mean was taken because it was the one
that improved every measure without costing any.

Two things follow from it. Scores now sit lower, so the rungs climb towards
what the whole record reaches rather than towards one, and the curve stays
evenly sampled. And when the search settles for fewer instruments than the
feature has, the score is taken over that many, best first, since a set nobody
is asking for would otherwise sit at zero and take every window down with it.

*Code: `reach.py:94`.*

---

## The trick that makes it fast and exact

Two simple facts.

**One.** A window can always be pulled in so it starts and ends exactly on an
observation. You lose nothing and the window gets shorter. So the only windows
worth looking at are the ones that begin and end on an observation.

**Two.** A bigger window is never worse. Add an observation and you never lose
ground, never lose an instrument, never lose your SHARAD track.
The moment the window is good enough, stop growing it and start pulling the **left** edge in, as far as it will go.

*Code: the sweep is `algorithm.py:45` to `algorithm.py:58`.*

---

## Inside the sliding window

The tally is the `Reach` class (`reach.py:8`). It keeps one counter per cell
per instrument set.

- Taking an observation in raises the counter of each cell it fills
  (`reach.py:40`). A counter rising from zero is new ground for that set.
- Dropping the oldest observation out lowers those counters again
  (`reach.py:61`). A counter falling back to zero is ground the window no
  longer reaches.
- How many cells a set holds is kept as a running number, so nothing is ever
  recounted.

That is what makes both ends of the window cheap, and it is why a feature
holding 63,442 observations is still a few seconds of work.

Two more things move with the window:

- **How many instruments are present** (`reach.py:128`), which rises when a
  set's first observation enters and falls when its last one leaves.
- **How many sounder tracks are inside**, kept as a plain counter in the sweep
  itself (`algorithm.py:47`), because a window holding none is not a survey
  at all.

The score is the geometric mean of the sets' shares: multiply them, take the
root (`reach.py:94`). A set with nothing in the window counts as zero rather
than being left out. Were it left out, taking an instrument in could lower the
score, and the sweep could no longer trust that a bigger window is never worse.
When the search has settled for fewer instruments than the feature has, only
that many shares are used, the best ones first (`reach.py:121`).

---

## The pseudocode

```
best_time_window(feature):

  # ---- step 0: a look at the feature, or a clip of its edge
  drop every observation covering under a square kilometre of the feature
  drop every observation filling one cell of its grid or none
  drop every sounder track crossing under a tenth of the feature's width

  # ---- step 1: one timeline
  sets   <- every instrument that filled at least one cell of this feature
  total  <- for each set, the cells it fills across its whole record
  obs    <- all their observations on one axis, oldest first
  if no SHARAD track anywhere: give up, this feature has no survey

  # ---- step 2: how many instruments to insist on
  for wanted = (all of them) down to 1:

      curve <- empty
      # ---- step 3: raise the demand, one rung at a time
      for level = 0, 1/48, 2/48, ... of what the whole record reaches:

          shortest <- SLIDE(wanted, level)        # see below
          if nothing qualifies, or it runs over a Mars year:
              stop climbing                       # more ground only costs more
          add shortest to curve

      if curve is not empty:
          stop                                    # this many instruments do fit

  if curve is empty: give up

  # ---- step 4: take the bend
  put both axes of curve on a 0..1 scale
  answer <- the point sitting furthest above the straight line
            joining the two ends of the curve
  if no point sits above that line at all:
      answer <- the longest window on the curve

  # ---- step 5: what the answer did not need
  walk answer oldest first, marking an observation redundant when its own
       set already holds every cell it brings
  return answer


SLIDE(wanted, level):
  left <- first observation
  for right = first observation .. last:
      take obs[right] into the window
      while  the window holds a SHARAD track
        and  it holds at least `wanted` instruments
        and  its score is at least `level`:
              remember it if it is the shortest seen so far
              drop obs[left] out of the window
              left <- left + 1
  return the shortest one remembered
```

Two small honesty fixes are in the real code:

- A share is added up cell by cell, so it can land a whisker under a rung it
  should have cleared. Rungs forgive the last rounding place.
- Two observations can carry the exact same timestamp. Once a window is
  chosen, anything sharing an instant with either end is pulled in too. It is
  ground for free: the window does not get one second longer.

*Code: the whole of it is `search` (`algorithm.py:14`).*

---

## The small print the pseudocode leaves out

**A window is measured start to start.** Its length is the start time of its
last observation minus the start time of its first (`algorithm.py:53`). How
long each observation itself ran plays no part.

**The rungs climb towards the record, not towards perfection.** Before the
climb begins, the whole record from first observation to last is scored, and
that score is the top of the ladder (`algorithm.py:35`). Rung `k` of 48 asks
for `k/48` of it (`algorithm.py:37`). The first rung asks for nothing, which
finds the shortest window holding the instruments and a sounder track, whatever
ground it happens to reach.

**Shortest wins, and ground breaks the tie.** As the left edge is pulled in,
every qualifying window is compared on days first and ground second
(`algorithm.py:54`), so between two windows of exactly the same length the one
reaching more ground is kept.

**The same window is kept only once.** Neighbouring rungs often settle on the
identical stretch of time. The curve keeps one copy (`algorithm.py:63`), so
the bend is not dragged towards a window that happened to satisfy five rungs in
a row.

**The climb stops early on purpose.** The moment a rung has no qualifying
window inside a Mars year, every rung above it is skipped untried
(`algorithm.py:60`), because asking for more ground can only ever ask for more
days.

**Settling for fewer instruments is all or nothing.** The search tries every
instrument the feature has, and only when that produces no curve at all does it
try one fewer (`algorithm.py:31` and `algorithm.py:66`). It never mixes: a
curve is built entirely at one instrument count, and the score is taken over
that count, best sets first.

---

## Why the instrument count comes first

The score cannot trade an instrument away any more: a window missing one
multiplies by zero, whatever the others reach. That was the trade an average
would have made happily, two instruments at 100% beating three at 60%, and it
is the reason the count was put first in the first place.

What the count decides now is what to do when they cannot all be had. The
search insists on every instrument that has ever touched the feature, and only
when no window inside a Mars year holds that many does it settle for fewer, and
score the window on that many, best first. That is what makes a two instrument
answer mean something. It means "there is genuinely no Mars year in the whole
record where all three were here", not "two was shorter".

*Code: `algorithm.py:31`, and the score over that count `reach.py:121`.*

---

## Why the bend, and why days are not logged

The curve of ground against days climbs steeply at first, while extra days
still bring in whole new observations, then flattens out once the only things
left to collect overlap what you already hold. The bend between the two is the
knee.

Put both axes on a 0 to 1 scale and the curve runs corner to corner across a
square. The knee is simply the point furthest above the diagonal.

Scaling both axes that way is also why the days need no scaling of their own.
Dividing every day count by the same number, whatever it is, cancels out of
that rescaling exactly, so measuring time against the record's own pace rather
than in plain days would give the same answer every time.

Sometimes no point sits above the diagonal at all. The curve is then bending
the other way: ground is still speeding up when the cap arrives, and stopping
early buys nothing. There is no knee to find, so the longest window on the
curve is the answer.

It is tempting to compare days in their logarithm, since going from one day to
two feels like going from six months to a year. It is also wrong here, and the
data says so plainly: on a log axis these curves bend the *other* way, so the
"knee" collapses onto the shortest, emptiest window on the curve. Ground
saturates against elapsed days, so plain days is the axis it bends on.

*Code: the rescaling is `src/utils/maths/quantities.py:39`, the bend `algorithm.py:73` to `algorithm.py:81`.*

---

## What the window did not need

A window is a stretch of time, so it holds everything taken during it,
including the observations that show ground the window already had. A set that
images the same patch twice in a fortnight has covered it once.

So once the window is chosen it is walked oldest first, and every observation
is asked what it brought that nothing before it from its own set had already
brought. The ones that brought nothing are redundant: drop them and the window
covers the same ground over the same days. They are marked rather than removed,
because a window is a stretch of time and not a list of observations.

Reordering that walk by what each observation adds, which is how a cover is
usually built greedily, marks a different set of them and leaves exactly the
same union behind. Oldest first is the order the survey was actually observed
in, and it costs one pass instead of one pass per observation, which is what a
feature holding tens of thousands of them can afford.

It is not a small share. Across the 1,818 windows the search finds, 21.8% of
the observations inside them bring nothing new. Half the features have none at
all, and the redundancy piles up in the crowded ones: 2,656 of the 7,543
observations in the Noachis Terra window, 2,169 of the 6,520 in Terra
Cimmeria.

*Code: `filters/redundancy.py:10`.*

---

## Whether the feature is worth keeping

A window can be found and the feature still be a poor thing to put in a
dataset. The window can rest on two observations, or on a single instrument, or
on a feature the record barely touched. Each of those is a different reason to
leave it out, so each is asked separately rather than rolled into one score:

```
A window holding a sounder track            one
Instruments in the window                   2
```

A count of observations was asked for at first, three of them, on the
convention that time series work wants three to five before it will look at a
site at all. It was taken out again. That convention is about fitting a trend
through a pixel, and nothing here fits a trend. A sample is one crop per
instrument inside the window, so one observation from each instrument is
already a whole sample, and the instruments are counted directly. The count is
still measured and shown beside the window; it just decides nothing.

A fourth rung was tried and taken back out: a floor on how much of the feature
the whole record ever touched, on the reasoning that a feature nothing has
looked at has nothing to crop to. It never decided anything. An ODE footprint
dwarfs a named feature, so the record covers essentially all of every one of
them, and not a single feature of the 1,918 fell under even 97%. A rung that
always passes is a rung that teaches you to stop reading the list.

The rest of the card is measured and reported without having a say. How many of
the window's observations brought ground of their own. What the window reaches,
and over how long. Then one line per instrument, saying the least ground a
single one of its observations covers inside the window, thinnest first, in
both of the units the floors are written in, since neither follows from the
other. Everything in the window cleared those floors on the way in, so the line
is how close to them the window is really working, and whether it is holding
anything that ought to have been turned away and was not. And last, how many
observations the window turned away as too small to count, which is also where
a feature that lost its only sounder track that way says so, instead of reading
like one no sounder ever flew over.

The search still runs on a feature that will be left out. What it found is
worth reading beside the reason it was not kept, and the panels draw it either
way.

Of the 1,918 features with coverage computed here, 1,777 are kept and 141 are
left out: 83 because no stretch of their record holds a sounder track at all,
41 because only one instrument was there when it did, and 17 because nothing
they hold cleared the floors in the first place.

What is not decided here is how many features of a class the dataset wants.
Every corpus this was modelled on ends with a quota, whether over ecoregions or
over the 44 units of the geologic map of Mars, and a quota can only be filled
once every feature has been judged. This scores them one at a time. The
choosing between them belongs to the stage that builds the dataset.

*Code: `verdict.py:61`, with the card built at `verdict.py:113`.*

---

## The scorecard, row by row

Every feature gets the same card, built in `_checks` (`verdict.py:113`). Each
row is a `Check` (`verdict.py:19`) carrying what was asked, what the feature
answered, and whether the row has a say. Two rows decide, and the rest are
there to be read. A feature is kept when every deciding row passes
(`verdict.py:51`).

| Row | Decides | What it says | Code |
|---|---|---|---|
| A window holding a sounder track | yes | `found`, or `none`, or `none, N tracks were too small to count` when the feature had tracks but every one of them grazed it. | `verdict.py:89` |
| Instruments in the window | yes | How many sets have an observation inside, against the 2 required. | `verdict.py:135` |
| Observations bringing ground of their own | no | The core count against the total, such as `18 of 27`. | `verdict.py:141` |
| Ground the window reaches, counted evenly | no | The score and the length, such as `31% over 105 days`. | `verdict.py:148` |
| Smallest observation from each set | no | One row per instrument in the window, thinnest first, giving the least ground a single observation of that set covers inside it, in square kilometres and in that instrument's own pixels. | `verdict.py:177` |
| Observations too small to count | no | How many were turned away out of everything taken during the window. On a feature with no window, the count is over its whole record instead, which is the only span it has. | `verdict.py:229` |

The reading rows never keep a feature out, however poor they look.

A feature that filled no cells at all never reaches this card. It gets a single
row, `Ground on the feature: no cells filled`, and is left out on it
(`verdict.py:84`).

---

## What the search returns

One `Survey` (`results.py:12`), holding:

| Field | What it is |
|---|---|
| `start`, `end` | When the first and last observations inside the window were taken. |
| `days` | How long it lasts, start to start. |
| `reach` | Its score, the geometric mean of the sets' shares. |
| `instruments` | How many sets have an observation inside it. |
| `observations` | How many observations it holds. |
| `core` | How many of them brought ground nothing before them from their own set had already brought. |
| `redundant` | The rest, which is `observations` minus `core` (`results.py:45`). |
| `knee` | Whether the curve bent and this is the bend, or whether it never did and this is simply the longest window on the curve. |
| `shares` | What each named set reaches, one number per instrument (`models/window.py:60`). |
| `frontier` | Every window it was chosen from, shortest first, as `Window` records (`models/window.py:12`), so what a longer stretch would have bought can always be read off. |

It also writes its own one line summary for a legend or a title
(`results.py:67`), and its length in units that read well (`results.py:54`).

Nothing comes back at all when no set left anything measurable behind
(`models/track.py:72`), or when no admissible sounder track exists anywhere in the
record (`algorithm.py:24`).

---

## What it looks like on real features

```
Jezero         149 days    3 instruments   27%     (90, 44 and 5 across them)
Gale           105 days    3 instruments   31%     (73, 25, 17)
Noachis Terra  353 days    3 instruments   23%     (45, 25, 11)
Bahn           652 days    2 instruments   56%     (no Mars year holds all three)
Ada             no window                          (SHARAD never flew here)
```

Four of those five are kept. Ada is left out for the sounder it never had, and
Bahn only just stays, on the three observations it is asked for and no more.

The Gale curve, the whole thing the bend was chosen from:

```
   0.5 days    7%      <- the three instruments, and nothing more
  11.3 days   11%
  16.9 days   16%
  33.4 days   19%
  55.5 days   23%
  77.6 days   28%
 105.3 days   31%      <- the bend, and the answer
 164.9 days   36%
 225.5 days   40%
 391.5 days   44%
 557.4 days   50%
 650.9 days   59%
```

Read the bottom of that list: after 105 days you are paying 545 more days for
another 28 points. That is the deal the algorithm turns down.

## What it gives up

Turning that deal down costs something, and it should be said plainly. Across
the 1,296 features whose curve ran on past the window that was taken, the bend
gives up a median of 12 points to save a median of 381 days, keeping about
seven tenths of what the longest window on the curve reached. One feature in
seven keeps under half.

None of it is hidden. Every window the answer was chosen from is returned
beside it, so what a longer stretch would have bought can always be read off.

---

## What it costs

One pass over the timeline per rung. Nothing is ever recomputed from scratch,
because the tally of cells is updated as the window slides rather than
rebuilt.

```
median feature (70 observations)          a few milliseconds
Jezero, Gale (300-500 observations)       one to three seconds
Noachis Terra (63,442 observations)       about five seconds
```

Dropping the slivers is one pass over the record and marking the redundant
observations is one pass over the window, so neither shows beside the sweep.

Fewer rungs than this and the curve grows too thin to find a bend in: at 24 it
gave up about 3 points of ground on a fifth of the features tried. More rungs
buy nothing at all, and 96 of them cost nearly three times as long.

How much of the ladder gets climbed is decided by the cap and not by the
ladder, though. The median curve ends with 8 windows on it and a quarter of
them with three or fewer, because the climb stops at the first rung whose
shortest window runs past a Mars year. Those thin curves belong to features
whose window holds four observations at the median, where there is little for a
bend to be found in and the answer sits near the shortest window that
qualifies at all.

*Code: the incremental tally is `reach.py:40` and `reach.py:61`.*

---

## Where each step lives

| File | What it does |
|---|---|
| `filters/admissible.py` | Decides whether one observation is a look at the feature or a graze of its edge. |
| `timeline.py` | Applies that decision, merges every set onto one axis, and works out the totals, the grid size and the feature's width. |
| `reach.py` | The sliding window's tally: what each set holds, how many instruments are present, and the score. |
| `models/window.py` | One window, what it reaches, and pulling in the observations tied at either end of it. |
| `src/utils/maths/quantities.py` | Rescales one axis of the curve to run from nought to one. Shared, not survey's own. |
| `algorithm.py` | The search itself: the instrument count, the ladder of rungs, the sweep, and the bend. |
| `filters/redundancy.py` | Marks the observations inside the chosen window that brought nothing of their own. |
| `results.py` | The survey the search returns. |
| `verdict.py` | Asks the feature everything the dataset asks of it, and returns the scorecard. |
| `configs.py` | Every number in the table above. |

Line numbers here are from the code as it stands. If one has drifted, the
function names beside it have not.
