# Plate-weight model, 2026-11-08

7498 MenuStat items with a weight, 75 restaurants, 5 folds grouped by restaurant; ridge on name words (vocabulary 689), family and the kids flag; lambda 10.0 (CV MAE in ln by lambda: {'0.3': 0.6702, '1.0': 0.6618, '3.0': 0.6502, '10.0': 0.6412}); 300 gradient steps. Interval quantiles are cross-fitted: an item's interval uses the held-out residuals of the other folds.

**Held-out:** MAE 0.6708 in ln (a factor of 1.96). Over the 3514 held-out items of P2 families with a row: the model's 80 % interval covers 73 % (the family range covers 69 %), median width 5.1x against 4.2x. **Switch rule: not met, the model stays off.**
External check, the UK chain sheets (382 items): MAE 0.9601 in ln, 80 % interval coverage 0.531, family range coverage 0.743.

| family | held-out items | MAE ln | median ratio | model 80 % coverage | model width | family range coverage | family range width |
|---|---|---|---|---|---|---|---|
| none | 3616 | 0.7751 | 0.88 | 0.793 | 11.3x | | |
| sandwich | 875 | 0.477 | 0.83 | 0.752 | 4.1x | 0.802 | 4.2x |
| dessert | 513 | 0.712 | 0.99 | 0.55 | 8.8x | 0.318 | 2.1x |
| vegetable_starter | 306 | 0.8606 | 0.77 | 0.699 | 12.6x | 0.703 | 6.4x |
| meat_main | 273 | 0.6992 | 1.15 | 0.527 | 6.3x | | |
| burger | 260 | 0.5759 | 0.95 | 0.662 | 5.1x | 0.8 | 5.1x |
| wrap | 219 | 0.6154 | 0.55 | 0.904 | 6.8x | 0.822 | 1.6x |
| kids_dish | 217 | 0.462 | 0.91 | 0.779 | 4.5x | 0.77 | 4.4x |
| soup | 209 | 0.3108 | 0.94 | 0.746 | 2.5x | 0.823 | 1.9x |
| fried_potato_side | 140 | 0.4553 | 1.05 | 0.779 | 4.7x | 0.471 | 2.2x |
| breakfast_eggs | 111 | 0.6304 | 0.61 | 0.811 | 5.1x | 0.811 | 5.1x |
| side_vegetable | 110 | 0.5442 | 1.06 | 0.673 | 5.4x | 0.782 | 4.9x |
| breakfast_pancakes | 95 | 0.6214 | 0.70 | 0.663 | 5.2x | 0.789 | 5.6x |
| dip | 94 | 0.5328 | 1.10 | 0.766 | 5.2x | 0.723 | 5.2x |
| fish_main | 81 | 0.6249 | 0.88 | 0.519 | 5.0x | | |
| burrito | 80 | 0.3427 | 0.87 | 0.912 | 6.2x | 0.362 | 1.5x |
| side_bread | 55 | 0.5502 | 1.28 | 0.655 | 4.3x | 0.764 | 3.1x |
| taco | 53 | 0.4307 | 1.22 | 0.792 | 5.3x | 0.491 | 1.5x |
| breakfast_cereal | 44 | 0.7488 | 0.91 | 0.614 | 9.0x | 0.773 | 11.3x |
| side_rice | 32 | 0.4704 | 1.01 | 1 | 7.7x | 0.781 | 4.7x |
| pasta_main | 31 | 0.5637 | 1.02 | 0.871 | 7.8x | 0.677 | 4.9x |
| side_salad | 27 | 0.3067 | 1.15 | 1 | 7.8x | 0.407 | 1.7x |
| quesadilla | 24 | 0.6196 | 0.60 | 0.875 | 8.2x | 0.833 | 6.6x |
| toast_plate | 19 | 0.4266 | 1.13 | 0.947 | 7.9x | 0.789 | 2.7x |
| pizza_neapolitan | 9 | 0.4802 | 1.11 | 0.889 | 7.9x | | |
| fish_starter | 5 | 1.1201 | 0.70 | 0.6 | 8.0x | | |

## The thirty largest coefficients (ln grams)

- word:whatameal: +1.911
- word:express: +1.240
- word:for: -1.132
- word:finger: +1.056
- word:flavor: -0.956
- word:below: +0.952
- word:meal: +0.940
- word:package: -0.863
- word:giant: +0.848
- word:easy: -0.835
- word:pick: +0.834
- word:salad: +0.827
- word:platter: +0.763
- word:timbit: -0.748
- word:smasher: +0.723
- word:slam: +0.723
- word:dinner: +0.710
- word:packet: -0.710
- word:bowl: +0.707
- word:calorie: +0.679
- word:drizzle: -0.677
- word:sundae: +0.631
- fam:none: -0.628
- word:ketchup: -0.612
- word:mayonnaise: -0.598
- word:cyo: -0.597
- word:nacho: +0.569
- word:sack: +0.552
- word:slider: -0.547
- word:pie: +0.529
