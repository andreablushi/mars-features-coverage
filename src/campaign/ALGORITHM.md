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

---

## The trick that makes it fast and exact

Two simple facts.

**One.** A window can always be pulled in so it starts and ends exactly on an
observation. You lose nothing and the window gets shorter. So the only windows
worth looking at are the ones that begin and end on an observation.

**Two.** A bigger window is never worse. Add an observation and you never lose
ground, never lose an instrument, never lose your SHARAD track.
The moment the window is good enough, stop growing it and start pulling the **left** edge in, as far as it will go.


---

## The pseudocode

```
find_best_time_window(feature):

  # ---- step 0: a look at the feature, or a clip of its edge
  drop every observation covering under a square kilometre of the feature
  drop every observation filling one cell of its grid or none
  drop every sounder track crossing under a tenth of the feature's width

  # ---- step 1: one timeline
  sets   <- every instrument that filled at least one cell of this feature
  total  <- for each set, the cells it fills across its whole record
  obs    <- all their observations on one axis, oldest first
  if no SHARAD track anywhere: give up, this feature has no campaign

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
same union behind. Oldest first is the order the campaign was actually observed
in, and it costs one pass instead of one pass per observation, which is what a
feature holding tens of thousands of them can afford.

It is not a small share. Across the 1,818 windows the search finds, 21.8% of
the observations inside them bring nothing new. Half the features have none at
all, and the redundancy piles up in the crowded ones: 2,656 of the 7,543
observations in the Noachis Terra window, 2,169 of the 6,520 in Terra
Cimmeria.

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
