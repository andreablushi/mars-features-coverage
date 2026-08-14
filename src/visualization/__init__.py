"""Reading the computed artifacts back as widgets and figures.

Neither pipeline stage imports anything here. This is the interactive layer a
notebook drives, and the only place matplotlib and ipywidgets are used, which
is why they stay in the `notebook` dependency group.
"""
