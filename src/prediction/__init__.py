"""Predicting the dataset a strategy would leave, from the coverage measured.

The search says what one strategy makes of one feature. This stage runs it over
every tile of every feature measured, reads the result as one dataset, and
leaves what it found on disk so a notebook need not sweep again. Nothing here
draws anything: `src/visualization/` reads what this produces.
"""
