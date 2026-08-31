They were downloaded once from the PDS Geosciences node and renamed after what they hold.

    https://pds-geosciences.wustl.edu/mro/mro-m-crism-2-edr-v1/mrocr_0001/cdr/wa/

## What is here

| file | downloaded as | detector | bands | wavelengths | mean step |
|---|---|---|---|---:|---|
| `infrared_55.img` | `CDR410803692813_WA0300010L_3` | L, infrared | 55 | 3926 to 1024 nm, descending | 54.8 nm |
| `infrared_70.img` | `CDR410803692813_WA0300020L_3` | L, infrared | 70 | 3926 to 1024 nm, descending | 42.7 nm |
| `visible_19.img` | `CDR420850327000_WA0300010S_2` | S, visible | 19 | 376 to 1053 nm, ascending | 37.6 nm |
| `visible_25.img` | `CDR420850327000_WA0300020S_2` | S, visible | 25 | 376 to 1053 nm, ascending | 28.2 nm |

The two configurations cover the same spectral range at different sampling.
`WA030001x` is the coarser downlink, `WA030002x` the finer one.

### Where the two configurations were seen

Nothing published says multispectral survey mode has more than one. It came out
of the observations, on 2026-08-31. Every label names its own record and its own
band count, in two lines that sit a few apart:

    MRO:WAVELENGTH_FILE_NAME       = "CDR410803692813_WA0300010L_3.IMG"
    ...
        BANDS                      =  55

The pool was grouped by the three digit scan code a product id carries, code 214
in `msp00006994_05_if214_trr3`, and three observations were sampled from each
code. Both detectors' labels were fetched from ODE for each and those two lines
read off. Codes 211, 213 and 214 named `WA0300010` at 55 and 18 or 19 bands.
Codes 215, 217 and 218 named `WA0300020` at 70 and 24 or 25 bands, all nine
sampled. Counting the pool by scan code puts those three codes together at about
126 observations out of 48979, so the finer configuration is rare but real, and
one of those cannot be read with the coarser table.

The archive holds eight wavelength configurations per detector, `WA0000000`
through `WA0300030`. Only these two were ever seen named by a multispectral
survey observation, so only these two are kept.

The coarser is a subset of the finer: both span 3926.3 down to 1023.6 nm on the
infrared detector, and all 54 live centres of the 55 band table appear in the 70
band table to 0.01 nm. They still need separate files, because a table maps band
index to wavelength and the indices diverge, and which 54 of the 69 channels the
coarser downlink kept is what its own file records.

## Layout

Each file is one line by 64 columns by bands of centre wavelengths in nm,
written line interleaved as 32 bit floats, little endian. A trailing record of
detector row numbers follows the image and is not read.

Wavelength is a function of column as well as band, which is spectral smile.
Where the detector was never calibrated the value is 65535.
