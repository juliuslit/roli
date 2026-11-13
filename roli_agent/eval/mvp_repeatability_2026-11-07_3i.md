# Repeatability: pass A against pass B

The same photos, the same code and table (checkpoint sections 13-14), pass B with reuse_saved_reading on, 40 minutes after pass A.

| menu | menu read | recommendation text | ranking and figures | differences | model calls A / B | model $ A / B | USDA requests A / B |
|---|---|---|---|---|---|---|---|
| 03 Flour + Water | same | same | same | 0 | 11 / 10 | 0.0160 / 0.0081 | 2 / 2 |
| 08 The Greyhound | same | same | different | 1 | 50 / 12 | 0.1425 / 0.0065 | 150 / 2 |
| 01 Zuni Cafe | same | same | same | 0 | 26 / 8 | 0.0727 / 0.0061 | 17 / 1 |
| 23 Seafood chalkboard | same | same | same | 0 | 19 / 2 | 0.0338 / 0.0009 | 6 / 0 |

## 03 Flour + Water (20261107-050552-f6e155 vs 20261107-055043-88b1da)

No differences.

## 08 The Greyhound (20261107-050626-1a8351 vs 20261107-055054-052262)

- apple crumble rhubarb: ('evaluated', '6.923828', '16.908007') vs ('evaluated', '5.818779', '15.191547'): tag differed on ('https://garnishwithlemon.com/rhubarb-apple-crisp', 'ing_01'): ('eaten', 'plain_food') vs None

## 01 Zuni Cafe (20261107-050952-7ec318 vs 20261107-055152-83488a)

No differences.

## 23 Seafood chalkboard (20261107-051207-e625b7 vs 20261107-055203-4f6fbd)

No differences.
