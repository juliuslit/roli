# Assumed weights built from recipe data, 2026-11-08

Stored extractions: 2463 files, 2103 with ingredient lines, 2040 distinct recipes, 1738 with a serving count; 20096 lines read, 4013 with a weight stated in the text (explicit grams, an embedded weight, or a water-like liquid at 1 g per ml), 167 skipped as cooking medium or removed by a saved tag, 719 filed under a weights row. Per-serving grams = the line's grams / the recipe's serving count.
A data range replaces the hand row at run time when it rests on at least 8 recipes of the dish family, or 15 recipes across families (12.20), its spread (p90 / p10) is under 20x and its median lies within 4x of the hand row's range (`adapt.WeightsTable.data_usable`); otherwise the hand row stands and the last column says why. Pizza recipes are divided by their unit count (one plate is one pizza), other recipes by their serving count.

| row | hand range g | family | recipes | lines | p10-p90 g (data) | median | min-max | density lines | embedded | live? |
|---|---|---|---|---|---|---|---|---|---|---|
| W01 chives, garnish on a starter | 1-3 | any | 2 | 2 | 1.3-2.4 | 1.8 | 1.18-2.50 | 0 | 0 | 2 recipes, 15 needed |
| W01 chives, garnish on a starter | 1-3 | meat_main | 1 | 1 | 2.5-2.5 | 2.5 | 2.50-2.50 | 0 | 0 | 1 recipes, 8 needed |
| W01 chives, garnish on a starter | 1-3 | sandwich | 1 | 1 | 1.2-1.2 | 1.2 | 1.18-1.18 | 0 | 0 | 1 recipes, 8 needed |
| W02 basil leaves, garnish | 2.5-6 | any | 10 | 10 | 2.4-61.0 | 5.0 | 1.11-99.22 | 0 | 3 | 10 recipes, 15 needed |
| W02 basil leaves, garnish | 2.5-6 | dip | 1 | 1 | 5.0-5.0 | 5.0 | 5.00-5.00 | 0 | 0 | 1 recipes, 8 needed |
| W02 basil leaves, garnish | 2.5-6 | fish_main | 1 | 1 | 56.7-56.7 | 56.7 | 56.70-56.70 | 0 | 0 | 1 recipes, 8 needed |
| W02 basil leaves, garnish | 2.5-6 | leaf_salad_starter | 1 | 1 | 3.8-3.8 | 3.8 | 3.75-3.75 | 0 | 0 | 1 recipes, 8 needed |
| W02 basil leaves, garnish | 2.5-6 | tomato_salad_starter | 1 | 1 | 99.2-99.2 | 99.2 | 99.22-99.22 | 0 | 1 | 1 recipes, 8 needed |
| W02 basil leaves, garnish | 2.5-6 | vegetable_starter | 1 | 1 | 7.1-7.1 | 7.1 | 7.09-7.09 | 0 | 0 | 1 recipes, 8 needed |
| W03a mint leaves, garnish | 0.3-11.4 | any | 2 | 2 | 22.5-64.7 | 43.6 | 17.18-70.00 | 0 | 1 | 2 recipes, 15 needed |
| W03a mint leaves, garnish | 0.3-11.4 | dessert | 1 | 1 | 17.2-17.2 | 17.2 | 17.18-17.18 | 0 | 1 | 1 recipes, 8 needed |
| W03a mint leaves, garnish | 0.3-11.4 | fish_and_chips | 1 | 1 | 70.0-70.0 | 70.0 | 70.00-70.00 | 0 | 0 | 1 recipes, 8 needed |
| W04a parsley, garnish | 3.8-10 | any | 11 | 11 | 2.5-12.5 | 6.0 | 2.00-15.00 | 0 | 2 | 11 recipes, 15 needed |
| W04a parsley, garnish | 3.8-10 | fish_main | 1 | 1 | 12.5-12.5 | 12.5 | 12.50-12.50 | 0 | 0 | 1 recipes, 8 needed |
| W04a parsley, garnish | 3.8-10 | leaf_salad_starter | 2 | 2 | 6.2-7.4 | 6.8 | 6.00-7.50 | 0 | 1 | 2 recipes, 8 needed |
| W04a parsley, garnish | 3.8-10 | meat_main | 1 | 1 | 7.5-7.5 | 7.5 | 7.50-7.50 | 0 | 0 | 1 recipes, 8 needed |
| W04a parsley, garnish | 3.8-10 | sandwich | 1 | 1 | 15.0-15.0 | 15.0 | 15.00-15.00 | 0 | 0 | 1 recipes, 8 needed |
| W04a parsley, garnish | 3.8-10 | tomato_salad_starter | 1 | 1 | 5.0-5.0 | 5.0 | 5.00-5.00 | 0 | 0 | 1 recipes, 8 needed |
| W04a parsley, garnish | 3.8-10 | vegetable_starter | 1 | 1 | 3.3-3.3 | 3.3 | 3.33-3.33 | 0 | 1 | 1 recipes, 8 needed |
| W04b cilantro, garnish | 4-20 | any | 3 | 3 | 3.8-6.6 | 4.8 | 3.54-7.09 | 0 | 1 | 3 recipes, 15 needed |
| W04b cilantro, garnish | 4-20 | fried_potato_side | 1 | 1 | 7.1-7.1 | 7.1 | 7.09-7.09 | 0 | 0 | 1 recipes, 8 needed |
| W04b cilantro, garnish | 4-20 | pasta_main | 1 | 1 | 4.8-4.8 | 4.8 | 4.80-4.80 | 0 | 1 | 1 recipes, 8 needed |
| W04b cilantro, garnish | 4-20 | quesadilla | 1 | 1 | 3.5-3.5 | 3.5 | 3.54-3.54 | 0 | 0 | 1 recipes, 8 needed |
| W05 grated hard cheese finished  | 5-15 | any | 43 | 43 | 4.8-25.0 | 10.0 | 3.12-150.00 | 0 | 6 | yes |
| W05 grated hard cheese finished  | 5-15 | fish_main | 1 | 1 | 7.5-7.5 | 7.5 | 7.50-7.50 | 0 | 0 | 1 recipes, 8 needed |
| W05 grated hard cheese finished  | 5-15 | fried_potato_side | 2 | 2 | 3.4-5.9 | 4.7 | 3.12-6.25 | 0 | 0 | 2 recipes, 8 needed |
| W05 grated hard cheese finished  | 5-15 | leaf_salad_starter | 1 | 1 | 14.2-14.2 | 14.2 | 14.17-14.17 | 0 | 0 | 1 recipes, 8 needed |
| W05 grated hard cheese finished  | 5-15 | meat_main | 3 | 3 | 7.7-15.0 | 10.0 | 7.09-16.25 | 0 | 2 | 3 recipes, 8 needed |
| W05 grated hard cheese finished  | 5-15 | pasta_main | 10 | 10 | 6.9-21.6 | 12.1 | 4.72-25.00 | 0 | 1 | yes |
| W05 grated hard cheese finished  | 5-15 | pizza_neapolitan | 2 | 2 | 41.0-105.4 | 73.2 | 33.00-113.40 | 0 | 1 | 2 recipes, 8 needed |
| W05 grated hard cheese finished  | 5-15 | sandwich | 1 | 1 | 15.0-15.0 | 15.0 | 15.00-15.00 | 0 | 0 | 1 recipes, 8 needed |
| W05 grated hard cheese finished  | 5-15 | side_bread | 1 | 1 | 21.3-21.3 | 21.3 | 21.26-21.26 | 0 | 0 | 1 recipes, 8 needed |
| W05 grated hard cheese finished  | 5-15 | soup | 2 | 2 | 6.0-8.7 | 7.4 | 5.67-9.09 | 0 | 0 | 2 recipes, 8 needed |
| W05 grated hard cheese finished  | 5-15 | toast_plate | 1 | 1 | 10.0-10.0 | 10.0 | 10.00-10.00 | 0 | 0 | 1 recipes, 8 needed |
| W05 grated hard cheese finished  | 5-15 | vegetable_starter | 9 | 9 | 5.5-120.7 | 12.5 | 3.33-150.00 | 0 | 0 | spread 5.5-120.7 g is wider than 20x: not one role |
| W06 fresh mozzarella / fior di l | 85-170 | any | 32 | 32 | 10.8-226.8 | 56.7 | 4.72-340.19 | 0 | 4 | spread 10.8-226.8 g is wider than 20x: not one role |
| W06 fresh mozzarella / fior di l | 85-170 | burrito | 1 | 1 | 28.4-28.4 | 28.4 | 28.35-28.35 | 0 | 0 | 1 recipes, 8 needed |
| W06 fresh mozzarella / fior di l | 85-170 | dip | 1 | 1 | 56.7-56.7 | 56.7 | 56.70-56.70 | 0 | 0 | 1 recipes, 8 needed |
| W06 fresh mozzarella / fior di l | 85-170 | fried_potato_side | 4 | 4 | 12.2-33.8 | 21.2 | 10.00-37.50 | 0 | 0 | 4 recipes, 8 needed |
| W06 fresh mozzarella / fior di l | 85-170 | leaf_salad_starter | 1 | 1 | 83.3-83.3 | 83.3 | 83.33-83.33 | 0 | 0 | 1 recipes, 8 needed |
| W06 fresh mozzarella / fior di l | 85-170 | pizza_neapolitan | 13 | 13 | 99.4-272.2 | 226.8 | 77.96-340.19 | 0 | 2 | yes |
| W06 fresh mozzarella / fior di l | 85-170 | sandwich | 2 | 2 | 22.1-29.1 | 25.6 | 21.26-30.00 | 0 | 0 | 2 recipes, 8 needed |
| W06 fresh mozzarella / fior di l | 85-170 | side_bread | 4 | 4 | 23.4-52.4 | 35.4 | 21.26-56.70 | 0 | 2 | 4 recipes, 8 needed |
| W06 fresh mozzarella / fior di l | 85-170 | vegetable_starter | 3 | 3 | 4.8-16.1 | 5.0 | 4.72-18.90 | 0 | 0 | 3 recipes, 8 needed |
| W07 sesame seeds, toasted, garni | 3-9 | any | 2 | 3 | 1.9-3.0 | 3.0 | 1.67-3.00 | 0 | 0 | 2 recipes, 15 needed |
| W07 sesame seeds, toasted, garni | 3-9 | dessert | 1 | 1 | 1.7-1.7 | 1.7 | 1.67-1.67 | 0 | 0 | 1 recipes, 8 needed |
| W10 bottarga, shaved or grated o | 3-10 | any | 2 | 2 | 7.8-13.5 | 10.6 | 7.09-14.17 | 0 | 0 | 2 recipes, 15 needed |
| W10 bottarga, shaved or grated o | 3-10 | pasta_main | 1 | 1 | 14.2-14.2 | 14.2 | 14.17-14.17 | 0 | 0 | 1 recipes, 8 needed |
| W11 grapes, halved, garnish | 20-49 | any | 2 | 3 | 32.5-72.0 | 62.5 | 25.00-74.42 | 0 | 1 | 2 recipes, 15 needed |
| W11 grapes, halved, garnish | 20-49 | meat_main | 1 | 1 | 74.4-74.4 | 74.4 | 74.42-74.42 | 0 | 1 | 1 recipes, 8 needed |
| W11 grapes, halved, garnish | 20-49 | vegetable_starter | 1 | 2 | 28.8-58.8 | 43.8 | 25.00-62.50 | 0 | 0 | 1 recipes, 8 needed |
| W12 lemon juice, finishing | 5.9-15 | any | 116 | 120 | 1.2-11.1 | 3.7 | 0.31-31.25 | 117 | 0 | yes |
| W12 lemon juice, finishing | 5.9-15 | breakfast_eggs | 10 | 10 | 2.3-8.1 | 5.2 | 0.82-14.79 | 10 | 0 | yes |
| W12 lemon juice, finishing | 5.9-15 | breakfast_pancakes | 1 | 1 | 1.2-1.2 | 1.2 | 1.23-1.23 | 1 | 0 | 1 recipes, 8 needed |
| W12 lemon juice, finishing | 5.9-15 | crudo_starter | 4 | 4 | 1.6-6.3 | 3.1 | 1.23-7.39 | 4 | 0 | 4 recipes, 8 needed |
| W12 lemon juice, finishing | 5.9-15 | dessert | 9 | 11 | 0.6-3.7 | 1.8 | 0.31-4.03 | 9 | 0 | yes |
| W12 lemon juice, finishing | 5.9-15 | dip | 3 | 3 | 1.4-3.3 | 1.8 | 1.23-3.70 | 3 | 0 | 3 recipes, 8 needed |
| W12 lemon juice, finishing | 5.9-15 | fish_main | 18 | 18 | 2.5-11.3 | 6.5 | 0.41-19.72 | 18 | 0 | yes |
| W12 lemon juice, finishing | 5.9-15 | fried_potato_side | 1 | 1 | 3.0-3.0 | 3.0 | 2.96-2.96 | 1 | 0 | 1 recipes, 8 needed |
| W12 lemon juice, finishing | 5.9-15 | leaf_salad_starter | 17 | 17 | 2.5-8.9 | 4.9 | 1.64-11.09 | 17 | 0 | yes |
| W12 lemon juice, finishing | 5.9-15 | meat_main | 5 | 6 | 0.6-23.0 | 6.2 | 0.62-31.25 | 6 | 0 | 5 recipes, 8 needed |
| W12 lemon juice, finishing | 5.9-15 | pasta_main | 5 | 5 | 4.2-9.5 | 5.6 | 3.70-9.86 | 5 | 0 | 5 recipes, 8 needed |
| W12 lemon juice, finishing | 5.9-15 | sandwich | 7 | 7 | 2.2-13.3 | 3.0 | 1.85-22.18 | 7 | 0 | 7 recipes, 8 needed |
| W12 lemon juice, finishing | 5.9-15 | side_bread | 1 | 1 | 3.7-3.7 | 3.7 | 3.70-3.70 | 1 | 0 | 1 recipes, 8 needed |
| W12 lemon juice, finishing | 5.9-15 | soup | 7 | 7 | 2.5-7.4 | 3.7 | 2.46-7.39 | 7 | 0 | 7 recipes, 8 needed |
| W12 lemon juice, finishing | 5.9-15 | toast_plate | 2 | 2 | 3.0-6.9 | 4.9 | 2.46-7.39 | 2 | 0 | 2 recipes, 8 needed |
| W12 lemon juice, finishing | 5.9-15 | vegetable_starter | 9 | 10 | 3.7-12.8 | 4.6 | 3.70-28.35 | 9 | 0 | yes |
| W13 lemon zest | 1-2 | any | 1 | 1 | 3.7-3.7 | 3.7 | 3.70-3.70 | 1 | 0 | 1 recipes, 15 needed |
| W13 lemon zest | 1-2 | taco | 1 | 1 | 3.7-3.7 | 3.7 | 3.70-3.70 | 1 | 0 | 1 recipes, 8 needed |
| W14 salt, to taste | 0.4-6 | any | 27 | 34 | 0.4-184.2 | 4.5 | 0.12-396.89 | 4 | 12 | spread 0.4-184.2 g is wider than 20x: not one role |
| W14 salt, to taste | 0.4-6 | breakfast_pancakes | 1 | 1 | 0.5-0.5 | 0.5 | 0.50-0.50 | 0 | 1 | 1 recipes, 8 needed |
| W14 salt, to taste | 0.4-6 | crudo_starter | 1 | 2 | 5.1-13.9 | 9.5 | 4.00-15.00 | 0 | 0 | 1 recipes, 8 needed |
| W14 salt, to taste | 0.4-6 | dessert | 4 | 5 | 0.2-0.5 | 0.4 | 0.12-0.53 | 0 | 4 | 4 recipes, 8 needed |
| W14 salt, to taste | 0.4-6 | fish_and_chips | 1 | 2 | 0.8-1.4 | 1.1 | 0.75-1.50 | 0 | 2 | 1 recipes, 8 needed |
| W14 salt, to taste | 0.4-6 | fish_main | 1 | 3 | 1.4-10.8 | 3.8 | 0.75-12.50 | 0 | 0 | 1 recipes, 8 needed |
| W14 salt, to taste | 0.4-6 | fried_potato_side | 1 | 1 | 0.8-0.8 | 0.8 | 0.75-0.75 | 0 | 1 | 1 recipes, 8 needed |
| W14 salt, to taste | 0.4-6 | meat_main | 5 | 5 | 4.1-21.2 | 8.3 | 3.50-25.00 | 0 | 0 | 5 recipes, 8 needed |
| W14 salt, to taste | 0.4-6 | sandwich | 1 | 3 | 11.6-97.5 | 34.0 | 6.00-113.40 | 0 | 0 | 1 recipes, 8 needed |
| W14 salt, to taste | 0.4-6 | side_rice | 2 | 2 | 217.1-376.9 | 297.0 | 197.16-396.89 | 1 | 1 | 2 recipes, 8 needed |
| W14 salt, to taste | 0.4-6 | soup | 5 | 5 | 6.8-245.5 | 100.0 | 0.27-251.38 | 3 | 0 | 5 recipes, 8 needed |
| W14 salt, to taste | 0.4-6 | toast_plate | 1 | 1 | 153.9-153.9 | 153.9 | 153.90-153.90 | 0 | 1 | 1 recipes, 8 needed |
| W15 black pepper, to taste | 0.1-2.3 | any | 6 | 7 | 0.3-66.6 | 21.3 | 0.12-113.40 | 0 | 1 | 6 recipes, 15 needed |
| W15 black pepper, to taste | 0.1-2.3 | crudo_starter | 1 | 1 | 0.5-0.5 | 0.5 | 0.50-0.50 | 0 | 0 | 1 recipes, 8 needed |
| W15 black pepper, to taste | 0.1-2.3 | fried_potato_side | 2 | 2 | 3.7-31.9 | 17.8 | 0.12-35.44 | 0 | 1 | 2 recipes, 8 needed |
| W15 black pepper, to taste | 0.1-2.3 | sandwich | 2 | 3 | 8.3-95.0 | 21.3 | 5.00-113.40 | 0 | 0 | 2 recipes, 8 needed |
| W17 sourdough croutons or torn b | 28-60 | any | 23 | 23 | 21.2-137.1 | 45.4 | 3.75-300.00 | 0 | 9 | yes |
| W17 sourdough croutons or torn b | 28-60 | burger | 1 | 1 | 150.0-150.0 | 150.0 | 150.00-150.00 | 0 | 0 | 1 recipes, 8 needed |
| W17 sourdough croutons or torn b | 28-60 | dessert | 2 | 2 | 23.1-38.1 | 30.6 | 21.25-40.00 | 0 | 0 | 2 recipes, 8 needed |
| W17 sourdough croutons or torn b | 28-60 | fish_main | 3 | 3 | 22.0-27.7 | 25.0 | 21.25-28.35 | 0 | 1 | 3 recipes, 8 needed |
| W17 sourdough croutons or torn b | 28-60 | leaf_salad_starter | 3 | 3 | 20.2-56.1 | 25.5 | 18.90-63.79 | 0 | 0 | 3 recipes, 8 needed |
| W17 sourdough croutons or torn b | 28-60 | pizza_neapolitan | 2 | 2 | 255.0-295.0 | 275.0 | 250.00-300.00 | 0 | 0 | 2 recipes, 8 needed |
| W17 sourdough croutons or torn b | 28-60 | sandwich | 1 | 1 | 56.7-56.7 | 56.7 | 56.70-56.70 | 0 | 1 | 1 recipes, 8 needed |
| W17 sourdough croutons or torn b | 28-60 | side_bread | 3 | 3 | 40.0-56.7 | 56.7 | 35.83-56.70 | 0 | 3 | 3 recipes, 8 needed |
| W17 sourdough croutons or torn b | 28-60 | soup | 1 | 1 | 50.0-50.0 | 50.0 | 50.00-50.00 | 0 | 0 | 1 recipes, 8 needed |
| W17 sourdough croutons or torn b | 28-60 | vegetable_starter | 1 | 1 | 3.8-3.8 | 3.8 | 3.75-3.75 | 0 | 1 | 1 recipes, 8 needed |
| W18 corn kernels, side on a main | 73-145 | any | 19 | 21 | 28.4-210.0 | 70.9 | 3.70-216.17 | 1 | 10 | yes |
| W18 corn kernels, side on a main | 73-145 | fish_main | 3 | 3 | 20.0-102.1 | 85.0 | 3.70-106.31 | 1 | 1 | 3 recipes, 8 needed |
| W18 corn kernels, side on a main | 73-145 | meat_main | 2 | 2 | 74.1-99.6 | 86.8 | 70.87-102.77 | 0 | 1 | 2 recipes, 8 needed |
| W18 corn kernels, side on a main | 73-145 | quesadilla | 1 | 1 | 56.7-56.7 | 56.7 | 56.70-56.70 | 0 | 0 | 1 recipes, 8 needed |
| W18 corn kernels, side on a main | 73-145 | soup | 8 | 9 | 36.8-213.3 | 47.2 | 14.17-216.17 | 0 | 6 | yes |
| W18 corn kernels, side on a main | 73-145 | vegetable_starter | 1 | 1 | 28.4-28.4 | 28.4 | 28.35-28.35 | 0 | 0 | 1 recipes, 8 needed |
| W19 summer squash, side on a mai | 118-196 | any | 5 | 5 | 27.2-135.1 | 37.8 | 22.73-200.00 | 0 | 3 | 5 recipes, 15 needed |
| W19 summer squash, side on a mai | 118-196 | soup | 1 | 1 | 37.8-37.8 | 37.8 | 37.80-37.80 | 0 | 1 | 1 recipes, 8 needed |
| W19 summer squash, side on a mai | 118-196 | vegetable_starter | 1 | 1 | 200.0-200.0 | 200.0 | 200.00-200.00 | 0 | 0 | 1 recipes, 8 needed |
| W20b shishito peppers, side on a  | 25-55 | any | 1 | 1 | 20.8-20.8 | 20.8 | 20.83-20.83 | 0 | 0 | 1 recipes, 15 needed |
| W20b shishito peppers, side on a  | 25-55 | vegetable_starter | 1 | 1 | 20.8-20.8 | 20.8 | 20.83-20.83 | 0 | 0 | 1 recipes, 8 needed |
| W22 pistachios, garnish | 7-14 | any | 2 | 2 | 7.5-14.2 | 10.8 | 6.67-15.00 | 0 | 0 | 2 recipes, 15 needed |
| W22 pistachios, garnish | 7-14 | crudo_starter | 1 | 1 | 6.7-6.7 | 6.7 | 6.67-6.67 | 0 | 0 | 1 recipes, 8 needed |
| W22 pistachios, garnish | 7-14 | vegetable_starter | 1 | 1 | 15.0-15.0 | 15.0 | 15.00-15.00 | 0 | 0 | 1 recipes, 8 needed |
| W23 capers, garnish | 4.3-8.6 | any | 3 | 3 | 1.7-2.5 | 2.5 | 1.50-2.50 | 1 | 0 | 3 recipes, 15 needed |
| W23 capers, garnish | 4.3-8.6 | fish_and_chips | 1 | 1 | 2.5-2.5 | 2.5 | 2.50-2.50 | 0 | 0 | 1 recipes, 8 needed |
| W23 capers, garnish | 4.3-8.6 | fish_main | 1 | 1 | 1.5-1.5 | 1.5 | 1.50-1.50 | 0 | 0 | 1 recipes, 8 needed |
| W23 capers, garnish | 4.3-8.6 | leaf_salad_starter | 1 | 1 | 2.5-2.5 | 2.5 | 2.46-2.46 | 1 | 0 | 1 recipes, 8 needed |
| W24 green olives (castelvetrano) | 8-27 | any | 12 | 15 | 9.5-46.8 | 28.4 | 7.51-66.67 | 0 | 4 | 12 recipes, 15 needed |
| W24 green olives (castelvetrano) | 8-27 | fish_main | 2 | 3 | 15.0-25.0 | 25.0 | 12.50-25.00 | 0 | 0 | 2 recipes, 8 needed |
| W24 green olives (castelvetrano) | 8-27 | meat_main | 1 | 1 | 12.5-12.5 | 12.5 | 12.50-12.50 | 0 | 0 | 1 recipes, 8 needed |
| W24 green olives (castelvetrano) | 8-27 | snack_bowl | 6 | 8 | 7.5-31.4 | 29.2 | 7.51-31.89 | 0 | 3 | 6 recipes, 8 needed |
| W24 green olives (castelvetrano) | 8-27 | vegetable_starter | 2 | 2 | 19.4-61.4 | 40.4 | 14.17-66.67 | 0 | 1 | 2 recipes, 8 needed |
| W26 pancetta, guanciale or bacon | 16-32 | any | 26 | 26 | 9.7-70.9 | 28.4 | 7.09-113.40 | 0 | 2 | yes |
| W26 pancetta, guanciale or bacon | 16-32 | breakfast_eggs | 2 | 2 | 15.6-26.9 | 21.3 | 14.17-28.35 | 0 | 0 | 2 recipes, 8 needed |
| W26 pancetta, guanciale or bacon | 16-32 | dip | 2 | 2 | 10.6-39.0 | 24.8 | 7.09-42.52 | 0 | 0 | 2 recipes, 8 needed |
| W26 pancetta, guanciale or bacon | 16-32 | fried_potato_side | 1 | 1 | 16.2-16.2 | 16.2 | 16.25-16.25 | 0 | 0 | 1 recipes, 8 needed |
| W26 pancetta, guanciale or bacon | 16-32 | leaf_salad_starter | 3 | 3 | 18.0-97.4 | 33.3 | 14.17-113.40 | 0 | 0 | 3 recipes, 8 needed |
| W26 pancetta, guanciale or bacon | 16-32 | meat_main | 1 | 1 | 12.5-12.5 | 12.5 | 12.50-12.50 | 0 | 0 | 1 recipes, 8 needed |
| W26 pancetta, guanciale or bacon | 16-32 | pasta_main | 7 | 7 | 15.8-47.2 | 28.4 | 11.34-50.00 | 0 | 0 | 7 recipes, 8 needed |
| W26 pancetta, guanciale or bacon | 16-32 | sandwich | 2 | 2 | 39.7-54.8 | 47.2 | 37.80-56.70 | 0 | 0 | 2 recipes, 8 needed |
| W26 pancetta, guanciale or bacon | 16-32 | side_rice | 1 | 1 | 26.7-26.7 | 26.7 | 26.67-26.67 | 0 | 0 | 1 recipes, 8 needed |
| W26 pancetta, guanciale or bacon | 16-32 | snack_bowl | 1 | 1 | 8.1-8.1 | 8.1 | 8.10-8.10 | 0 | 0 | 1 recipes, 8 needed |
| W27 heavy cream, finishing | 15-30 | any | 50 | 56 | 9.4-70.1 | 28.4 | 6.25-150.00 | 0 | 13 | yes |
| W27 heavy cream, finishing | 15-30 | breakfast_cereal | 1 | 1 | 120.0-120.0 | 120.0 | 120.00-120.00 | 0 | 0 | 1 recipes, 8 needed |
| W27 heavy cream, finishing | 15-30 | dessert | 10 | 13 | 9.9-100.9 | 28.4 | 8.75-150.00 | 0 | 5 | yes |
| W27 heavy cream, finishing | 15-30 | dip | 5 | 5 | 19.8-49.1 | 32.4 | 14.17-56.70 | 0 | 3 | 5 recipes, 8 needed |
| W27 heavy cream, finishing | 15-30 | fried_potato_side | 2 | 2 | 22.9-24.8 | 23.8 | 22.68-25.00 | 0 | 0 | 2 recipes, 8 needed |
| W27 heavy cream, finishing | 15-30 | pasta_main | 1 | 1 | 56.7-56.7 | 56.7 | 56.70-56.70 | 0 | 0 | 1 recipes, 8 needed |
| W27 heavy cream, finishing | 15-30 | quesadilla | 1 | 1 | 28.4-28.4 | 28.4 | 28.35-28.35 | 0 | 0 | 1 recipes, 8 needed |
| W27 heavy cream, finishing | 15-30 | sandwich | 2 | 2 | 29.3-36.9 | 33.1 | 28.35-37.80 | 0 | 0 | 2 recipes, 8 needed |
| W27 heavy cream, finishing | 15-30 | side_bread | 3 | 3 | 28.4-35.9 | 28.4 | 28.35-37.80 | 0 | 0 | 3 recipes, 8 needed |
| W27 heavy cream, finishing | 15-30 | snack_bowl | 1 | 1 | 28.4-28.4 | 28.4 | 28.35-28.35 | 0 | 1 | 1 recipes, 8 needed |
| W27 heavy cream, finishing | 15-30 | soup | 1 | 1 | 119.1-119.1 | 119.1 | 119.07-119.07 | 0 | 1 | 1 recipes, 8 needed |
| W27 heavy cream, finishing | 15-30 | vegetable_starter | 1 | 1 | 22.7-22.7 | 22.7 | 22.68-22.68 | 0 | 0 | 1 recipes, 8 needed |
| W29 dry seasoning blend or spice | 2-8 | any | 2 | 2 | 1.3-6.8 | 4.1 | 0.62-7.50 | 1 | 0 | 2 recipes, 15 needed |
| W29 dry seasoning blend or spice | 2-8 | burger | 1 | 1 | 0.6-0.6 | 0.6 | 0.62-0.62 | 1 | 0 | 1 recipes, 8 needed |
| W30 burrata or stracciatella, a  | 50-125 | any | 2 | 2 | 87.9-110.6 | 99.2 | 85.05-113.40 | 0 | 0 | 2 recipes, 15 needed |
| W30 burrata or stracciatella, a  | 50-125 | vegetable_starter | 2 | 2 | 87.9-110.6 | 99.2 | 85.05-113.40 | 0 | 0 | 2 recipes, 8 needed |
| W31 aged or semi-soft cheese nam | 15-60 | any | 37 | 39 | 17.4-117.7 | 32.4 | 7.09-226.80 | 0 | 8 | hand row limited to dish types |
| W31 aged or semi-soft cheese nam | 15-60 | crudo_starter | 1 | 1 | 7.1-7.1 | 7.1 | 7.09-7.09 | 0 | 0 | 1 recipes, 8 needed |
| W31 aged or semi-soft cheese nam | 15-60 | leaf_salad_starter | 10 | 10 | 16.0-45.8 | 25.0 | 14.17-50.00 | 0 | 2 | yes |
| W31 aged or semi-soft cheese nam | 15-60 | meat_main | 4 | 4 | 35.4-98.1 | 52.5 | 32.40-113.40 | 0 | 1 | 4 recipes, 8 needed |
| W31 aged or semi-soft cheese nam | 15-60 | pasta_main | 6 | 6 | 19.7-138.6 | 63.8 | 17.72-142.50 | 0 | 2 | 6 recipes, 8 needed |
| W31 aged or semi-soft cheese nam | 15-60 | tomato_salad_starter | 3 | 4 | 24.4-170.1 | 33.1 | 22.68-226.80 | 0 | 0 | 3 recipes, 8 needed |
| W31 aged or semi-soft cheese nam | 15-60 | vegetable_starter | 13 | 14 | 20.0-64.1 | 40.6 | 14.17-180.00 | 0 | 3 | yes |
| W32 cheese topping on one pizza  | 60-140 | any | 3 | 3 | 68.0-294.8 | 113.4 | 56.70-340.19 | 0 | 2 | hand row limited to dish types |
| W32 cheese topping on one pizza  | 60-140 | pizza_neapolitan | 3 | 3 | 68.0-294.8 | 113.4 | 56.70-340.19 | 0 | 2 | 3 recipes, 8 needed |
| W33 blue cheese on a plate (comp | 15-60 | any | 9 | 9 | 9.3-56.7 | 22.7 | 6.67-56.70 | 0 | 1 | 9 recipes, 15 needed |
| W33 blue cheese on a plate (comp | 15-60 | burger | 2 | 2 | 10.6-15.6 | 13.1 | 10.00-16.25 | 0 | 0 | 2 recipes, 8 needed |
| W33 blue cheese on a plate (comp | 15-60 | fried_potato_side | 1 | 1 | 56.7-56.7 | 56.7 | 56.70-56.70 | 0 | 0 | 1 recipes, 8 needed |
| W33 blue cheese on a plate (comp | 15-60 | leaf_salad_starter | 1 | 1 | 21.3-21.3 | 21.3 | 21.26-21.26 | 0 | 1 | 1 recipes, 8 needed |
| W33 blue cheese on a plate (comp | 15-60 | pizza_neapolitan | 1 | 1 | 56.7-56.7 | 56.7 | 56.70-56.70 | 0 | 0 | 1 recipes, 8 needed |
| W33 blue cheese on a plate (comp | 15-60 | sandwich | 2 | 2 | 27.5-47.5 | 37.5 | 25.00-50.00 | 0 | 0 | 2 recipes, 8 needed |
| W33 blue cheese on a plate (comp | 15-60 | side_rice | 1 | 1 | 22.7-22.7 | 22.7 | 22.68-22.68 | 0 | 0 | 1 recipes, 8 needed |
| W34 feta, queso fresco, cotija o | 15-45 | any | 14 | 14 | 14.2-54.7 | 28.4 | 9.45-100.00 | 0 | 2 | 14 recipes, 15 needed |
| W34 feta, queso fresco, cotija o | 15-45 | breakfast_eggs | 2 | 2 | 11.0-23.4 | 17.2 | 9.45-25.00 | 0 | 1 | 2 recipes, 8 needed |
| W34 feta, queso fresco, cotija o | 15-45 | fried_potato_side | 1 | 1 | 28.4-28.4 | 28.4 | 28.35-28.35 | 0 | 0 | 1 recipes, 8 needed |
| W34 feta, queso fresco, cotija o | 15-45 | leaf_salad_starter | 3 | 3 | 15.1-27.8 | 18.9 | 14.17-30.00 | 0 | 1 | 3 recipes, 8 needed |
| W34 feta, queso fresco, cotija o | 15-45 | quesadilla | 1 | 1 | 28.4-28.4 | 28.4 | 28.35-28.35 | 0 | 0 | 1 recipes, 8 needed |
| W34 feta, queso fresco, cotija o | 15-45 | sandwich | 1 | 1 | 56.7-56.7 | 56.7 | 56.70-56.70 | 0 | 0 | 1 recipes, 8 needed |
| W34 feta, queso fresco, cotija o | 15-45 | snack_bowl | 1 | 1 | 14.2-14.2 | 14.2 | 14.17-14.17 | 0 | 0 | 1 recipes, 8 needed |
| W34 feta, queso fresco, cotija o | 15-45 | vegetable_starter | 1 | 1 | 37.5-37.5 | 37.5 | 37.50-37.50 | 0 | 0 | 1 recipes, 8 needed |
| W35 soft goat cheese on a plate  | 20-60 | any | 18 | 18 | 16.2-95.7 | 28.4 | 9.45-141.75 | 0 | 2 | yes |
| W35 soft goat cheese on a plate  | 20-60 | crudo_starter | 2 | 2 | 10.2-15.9 | 13.1 | 9.45-16.67 | 0 | 0 | 2 recipes, 8 needed |
| W35 soft goat cheese on a plate  | 20-60 | leaf_salad_starter | 7 | 7 | 24.6-99.2 | 28.4 | 18.90-120.49 | 0 | 1 | 7 recipes, 8 needed |
| W35 soft goat cheese on a plate  | 20-60 | pizza_neapolitan | 1 | 1 | 141.8-141.8 | 141.8 | 141.75-141.75 | 0 | 0 | 1 recipes, 8 needed |
| W35 soft goat cheese on a plate  | 20-60 | sandwich | 1 | 1 | 56.7-56.7 | 56.7 | 56.70-56.70 | 0 | 0 | 1 recipes, 8 needed |
| W35 soft goat cheese on a plate  | 20-60 | taco | 1 | 1 | 28.4-28.4 | 28.4 | 28.35-28.35 | 0 | 0 | 1 recipes, 8 needed |
| W36 fresh ricotta as a component | 30-90 | any | 9 | 9 | 45.1-453.6 | 97.2 | 25.56-453.59 | 0 | 4 | 9 recipes, 15 needed |
| W36 fresh ricotta as a component | 30-90 | dessert | 3 | 3 | 31.8-89.1 | 56.7 | 25.56-97.20 | 0 | 2 | 3 recipes, 8 needed |
| W36 fresh ricotta as a component | 30-90 | pizza_neapolitan | 4 | 4 | 112.7-453.6 | 326.0 | 76.00-453.59 | 0 | 2 | 4 recipes, 8 needed |
| W36 fresh ricotta as a component | 30-90 | vegetable_starter | 1 | 1 | 116.9-116.9 | 116.9 | 116.94-116.94 | 0 | 0 | 1 recipes, 8 needed |
| W37 cured whole-muscle pork (pro | 20-50 | any | 9 | 9 | 13.4-47.6 | 20.0 | 12.50-56.70 | 0 | 1 | 9 recipes, 15 needed |
| W37 cured whole-muscle pork (pro | 20-50 | breakfast_eggs | 2 | 2 | 31.2-53.9 | 42.5 | 28.35-56.70 | 0 | 1 | 2 recipes, 8 needed |
| W37 cured whole-muscle pork (pro | 20-50 | fish_main | 1 | 1 | 45.4-45.4 | 45.4 | 45.36-45.36 | 0 | 0 | 1 recipes, 8 needed |
| W37 cured whole-muscle pork (pro | 20-50 | leaf_salad_starter | 1 | 1 | 33.3-33.3 | 33.3 | 33.33-33.33 | 0 | 0 | 1 recipes, 8 needed |
| W37 cured whole-muscle pork (pro | 20-50 | pasta_main | 2 | 2 | 12.7-14.1 | 13.4 | 12.50-14.29 | 0 | 0 | 2 recipes, 8 needed |
| W37 cured whole-muscle pork (pro | 20-50 | soup | 1 | 1 | 13.6-13.6 | 13.6 | 13.64-13.64 | 0 | 0 | 1 recipes, 8 needed |
| W38 cured sausage (salami, soppr | 20-60 | any | 17 | 20 | 10.7-56.7 | 21.3 | 5.00-150.00 | 0 | 1 | yes |
| W38 cured sausage (salami, soppr | 20-60 | dip | 1 | 1 | 28.4-28.4 | 28.4 | 28.35-28.35 | 0 | 0 | 1 recipes, 8 needed |
| W38 cured sausage (salami, soppr | 20-60 | fish_main | 2 | 3 | 7.3-123.3 | 16.7 | 5.00-150.00 | 0 | 0 | 2 recipes, 8 needed |
| W38 cured sausage (salami, soppr | 20-60 | leaf_salad_starter | 3 | 4 | 14.3-22.3 | 21.3 | 11.34-22.68 | 0 | 1 | 3 recipes, 8 needed |
| W38 cured sausage (salami, soppr | 20-60 | pasta_main | 1 | 1 | 14.3-14.3 | 14.3 | 14.29-14.29 | 0 | 0 | 1 recipes, 8 needed |
| W38 cured sausage (salami, soppr | 20-60 | pizza_neapolitan | 1 | 1 | 56.7-56.7 | 56.7 | 56.70-56.70 | 0 | 0 | 1 recipes, 8 needed |
| W38 cured sausage (salami, soppr | 20-60 | sandwich | 1 | 1 | 22.7-22.7 | 22.7 | 22.68-22.68 | 0 | 0 | 1 recipes, 8 needed |
| W38 cured sausage (salami, soppr | 20-60 | side_rice | 1 | 1 | 12.5-12.5 | 12.5 | 12.50-12.50 | 0 | 0 | 1 recipes, 8 needed |
| W38 cured sausage (salami, soppr | 20-60 | soup | 1 | 1 | 18.2-18.2 | 18.2 | 18.18-18.18 | 0 | 0 | 1 recipes, 8 needed |
| W38 cured sausage (salami, soppr | 20-60 | vegetable_starter | 2 | 2 | 33.9-45.8 | 39.8 | 32.40-47.25 | 0 | 0 | 2 recipes, 8 needed |
| W40 egg- or mayonnaise-based dre | 20-45 | any | 9 | 9 | 4.1-51.3 | 14.1 | 2.36-56.70 | 0 | 3 | 9 recipes, 15 needed |
| W40 egg- or mayonnaise-based dre | 20-45 | burger | 1 | 1 | 50.0-50.0 | 50.0 | 50.00-50.00 | 0 | 0 | 1 recipes, 8 needed |
| W40 egg- or mayonnaise-based dre | 20-45 | dip | 2 | 2 | 7.8-51.3 | 29.5 | 2.36-56.70 | 0 | 1 | 2 recipes, 8 needed |
| W40 egg- or mayonnaise-based dre | 20-45 | fish_main | 1 | 1 | 18.8-18.8 | 18.8 | 18.75-18.75 | 0 | 0 | 1 recipes, 8 needed |
| W41 almonds, toasted or slivered | 7-20 | any | 10 | 11 | 3.1-18.8 | 6.7 | 2.14-25.00 | 0 | 1 | 10 recipes, 15 needed |
| W41 almonds, toasted or slivered | 7-20 | breakfast_cereal | 3 | 3 | 3.8-14.1 | 6.7 | 3.12-16.00 | 0 | 1 | 3 recipes, 8 needed |
| W41 almonds, toasted or slivered | 7-20 | dessert | 3 | 4 | 6.2-14.0 | 7.1 | 6.25-16.50 | 0 | 0 | 3 recipes, 8 needed |
| W41 almonds, toasted or slivered | 7-20 | leaf_salad_starter | 1 | 1 | 18.8-18.8 | 18.8 | 18.75-18.75 | 0 | 0 | 1 recipes, 8 needed |
| W41 almonds, toasted or slivered | 7-20 | vegetable_starter | 1 | 1 | 25.0-25.0 | 25.0 | 25.00-25.00 | 0 | 0 | 1 recipes, 8 needed |
| W42 watermelon, in a salad or as | 80-200 | any | 6 | 6 | 66.2-396.9 | 187.5 | 45.00-453.59 | 0 | 0 | 6 recipes, 15 needed |
| W42 watermelon, in a salad or as | 80-200 | fish_main | 2 | 2 | 146.5-318.7 | 232.6 | 125.00-340.19 | 0 | 0 | 2 recipes, 8 needed |
| W42 watermelon, in a salad or as | 80-200 | leaf_salad_starter | 2 | 2 | 270.4-433.2 | 351.8 | 250.00-453.59 | 0 | 0 | 2 recipes, 8 needed |
| W43 eggplant / aubergine, roaste | 80-200 | any | 17 | 17 | 87.8-181.4 | 113.4 | 37.80-340.19 | 0 | 7 | yes |
| W43 eggplant / aubergine, roaste | 80-200 | fish_main | 1 | 1 | 113.4-113.4 | 113.4 | 113.40-113.40 | 0 | 1 | 1 recipes, 8 needed |
| W43 eggplant / aubergine, roaste | 80-200 | meat_main | 1 | 1 | 113.4-113.4 | 113.4 | 113.40-113.40 | 0 | 0 | 1 recipes, 8 needed |
| W43 eggplant / aubergine, roaste | 80-200 | soup | 1 | 1 | 141.8-141.8 | 141.8 | 141.75-141.75 | 0 | 1 | 1 recipes, 8 needed |
| W43 eggplant / aubergine, roaste | 80-200 | tomato_salad_starter | 1 | 1 | 226.8-226.8 | 226.8 | 226.80-226.80 | 0 | 1 | 1 recipes, 8 needed |
| W43 eggplant / aubergine, roaste | 80-200 | vegetable_starter | 12 | 12 | 97.7-151.1 | 113.4 | 75.60-340.19 | 0 | 3 | yes |
| W44 broccoli rabe / rapini, side | 60-150 | any | 1 | 1 | 113.4-113.4 | 113.4 | 113.40-113.40 | 0 | 1 | 1 recipes, 15 needed |
| W44 broccoli rabe / rapini, side | 60-150 | vegetable_starter | 1 | 1 | 113.4-113.4 | 113.4 | 113.40-113.40 | 0 | 1 | 1 recipes, 8 needed |
| W45 turnip, side or component | 40-120 | any | 2 | 2 | 79.4-109.6 | 94.5 | 75.60-113.40 | 0 | 0 | 2 recipes, 15 needed |
| W45 turnip, side or component | 40-120 | fried_potato_side | 1 | 1 | 75.6-75.6 | 75.6 | 75.60-75.60 | 0 | 0 | 1 recipes, 8 needed |
| W45 turnip, side or component | 40-120 | leaf_salad_starter | 1 | 1 | 113.4-113.4 | 113.4 | 113.40-113.40 | 0 | 0 | 1 recipes, 8 needed |
| W46 mustard greens or similar bi | 30-100 | any | 2 | 2 | 112.7-214.1 | 163.4 | 100.00-226.80 | 0 | 1 | 2 recipes, 15 needed |
| W46 mustard greens or similar bi | 30-100 | fish_main | 1 | 1 | 100.0-100.0 | 100.0 | 100.00-100.00 | 0 | 1 | 1 recipes, 8 needed |
| W46 mustard greens or similar bi | 30-100 | leaf_salad_starter | 1 | 1 | 226.8-226.8 | 226.8 | 226.80-226.80 | 0 | 0 | 1 recipes, 8 needed |
| W47 stone fruit, sliced, in a sa | 50-150 | any | 10 | 10 | 6.2-170.1 | 52.0 | 6.00-425.24 | 0 | 6 | 10 recipes, 15 needed |
| W47 stone fruit, sliced, in a sa | 50-150 | breakfast_cereal | 1 | 1 | 6.0-6.0 | 6.0 | 6.00-6.00 | 0 | 1 | 1 recipes, 8 needed |
| W47 stone fruit, sliced, in a sa | 50-150 | dessert | 5 | 5 | 18.9-311.8 | 97.2 | 6.25-425.24 | 0 | 3 | 5 recipes, 8 needed |
| W47 stone fruit, sliced, in a sa | 50-150 | leaf_salad_starter | 2 | 2 | 68.0-83.2 | 75.6 | 66.15-85.05 | 0 | 2 | 2 recipes, 8 needed |
| W47 stone fruit, sliced, in a sa | 50-150 | meat_main | 1 | 1 | 33.3-33.3 | 33.3 | 33.33-33.33 | 0 | 0 | 1 recipes, 8 needed |
| W47 stone fruit, sliced, in a sa | 50-150 | vegetable_starter | 1 | 1 | 12.5-12.5 | 12.5 | 12.50-12.50 | 0 | 0 | 1 recipes, 8 needed |
| W48 roasted, grilled or bell pep | 40-120 | any | 12 | 12 | 14.3-212.6 | 50.2 | 14.17-250.00 | 0 | 5 | 12 recipes, 15 needed |
| W48 roasted, grilled or bell pep | 40-120 | fish_main | 2 | 2 | 17.8-46.4 | 32.1 | 14.17-50.00 | 0 | 0 | 2 recipes, 8 needed |
| W48 roasted, grilled or bell pep | 40-120 | pasta_main | 1 | 1 | 66.7-66.7 | 66.7 | 66.67-66.67 | 0 | 1 | 1 recipes, 8 needed |
| W48 roasted, grilled or bell pep | 40-120 | soup | 3 | 3 | 27.6-197.0 | 78.0 | 15.00-226.80 | 0 | 3 | 3 recipes, 8 needed |
| W48 roasted, grilled or bell pep | 40-120 | tomato_salad_starter | 1 | 1 | 85.0-85.0 | 85.0 | 85.05-85.05 | 0 | 1 | 1 recipes, 8 needed |
| W48 roasted, grilled or bell pep | 40-120 | vegetable_starter | 2 | 2 | 70.4-230.0 | 150.2 | 50.40-250.00 | 0 | 0 | 2 recipes, 8 needed |
| W49 fennel, shaved or roasted, s | 40-120 | any | 2 | 2 | 2.2-3.8 | 3.0 | 2.00-4.00 | 0 | 0 | 2 recipes, 15 needed |
| W50 lime or lemon wedge, charred | 10-35 | any | 53 | 54 | 1.2-13.9 | 4.9 | 0.62-29.57 | 53 | 1 | yes |
| W50 lime or lemon wedge, charred | 10-35 | breakfast_eggs | 1 | 1 | 1.2-1.2 | 1.2 | 1.23-1.23 | 1 | 0 | 1 recipes, 8 needed |
| W50 lime or lemon wedge, charred | 10-35 | burger | 1 | 1 | 1.6-1.6 | 1.6 | 1.64-1.64 | 1 | 0 | 1 recipes, 8 needed |
| W50 lime or lemon wedge, charred | 10-35 | crudo_starter | 1 | 1 | 7.4-7.4 | 7.4 | 7.39-7.39 | 1 | 0 | 1 recipes, 8 needed |
| W50 lime or lemon wedge, charred | 10-35 | dip | 3 | 3 | 1.9-8.3 | 2.0 | 1.85-9.86 | 3 | 0 | 3 recipes, 8 needed |
| W50 lime or lemon wedge, charred | 10-35 | fish_main | 14 | 14 | 1.7-14.8 | 6.6 | 0.62-29.57 | 14 | 0 | yes |
| W50 lime or lemon wedge, charred | 10-35 | fried_potato_side | 2 | 3 | 1.6-4.1 | 3.0 | 1.23-4.44 | 3 | 0 | 2 recipes, 8 needed |
| W50 lime or lemon wedge, charred | 10-35 | leaf_salad_starter | 2 | 2 | 3.7-3.7 | 3.7 | 3.70-3.70 | 2 | 0 | 2 recipes, 8 needed |
| W50 lime or lemon wedge, charred | 10-35 | meat_main | 4 | 4 | 5.7-16.0 | 6.6 | 5.55-19.72 | 4 | 0 | 4 recipes, 8 needed |
| W50 lime or lemon wedge, charred | 10-35 | pasta_main | 1 | 1 | 1.8-1.8 | 1.8 | 1.85-1.85 | 1 | 0 | 1 recipes, 8 needed |
| W50 lime or lemon wedge, charred | 10-35 | quesadilla | 1 | 1 | 1.4-1.4 | 1.4 | 1.39-1.39 | 1 | 0 | 1 recipes, 8 needed |
| W50 lime or lemon wedge, charred | 10-35 | side_bread | 1 | 1 | 11.8-11.8 | 11.8 | 11.83-11.83 | 1 | 0 | 1 recipes, 8 needed |
| W50 lime or lemon wedge, charred | 10-35 | taco | 7 | 7 | 2.2-8.4 | 5.6 | 1.85-9.86 | 7 | 0 | 7 recipes, 8 needed |
| W50 lime or lemon wedge, charred | 10-35 | toast_plate | 1 | 1 | 4.9-4.9 | 4.9 | 4.93-4.93 | 1 | 0 | 1 recipes, 8 needed |
| W50 lime or lemon wedge, charred | 10-35 | vegetable_starter | 3 | 3 | 2.3-6.8 | 4.2 | 1.85-7.39 | 3 | 0 | 3 recipes, 8 needed |
| W51 pickles, gherkins or pickled | 20-60 | any | 1 | 1 | 2.5-2.5 | 2.5 | 2.50-2.50 | 0 | 0 | 1 recipes, 15 needed |
| W51 pickles, gherkins or pickled | 20-60 | fish_and_chips | 1 | 1 | 2.5-2.5 | 2.5 | 2.50-2.50 | 0 | 0 | 1 recipes, 8 needed |
| W52 sweet chilli, hot or chilli  | 15-45 | any | 1 | 1 | 3.0-3.0 | 3.0 | 3.00-3.00 | 0 | 0 | 1 recipes, 15 needed |
| W54 garden peas or petits pois,  | 60-150 | any | 37 | 37 | 14.7-118.0 | 50.0 | 8.33-226.80 | 0 | 4 | yes |
| W54 garden peas or petits pois,  | 60-150 | breakfast_cereal | 1 | 1 | 75.0-75.0 | 75.0 | 75.00-75.00 | 0 | 0 | 1 recipes, 8 needed |
| W54 garden peas or petits pois,  | 60-150 | fish_and_chips | 1 | 1 | 75.0-75.0 | 75.0 | 75.00-75.00 | 0 | 0 | 1 recipes, 8 needed |
| W54 garden peas or petits pois,  | 60-150 | fish_main | 2 | 2 | 38.6-67.3 | 52.9 | 35.00-70.87 | 0 | 0 | 2 recipes, 8 needed |
| W54 garden peas or petits pois,  | 60-150 | leaf_salad_starter | 5 | 5 | 16.4-181.4 | 22.7 | 16.25-226.80 | 0 | 0 | 5 recipes, 8 needed |
| W54 garden peas or petits pois,  | 60-150 | meat_main | 3 | 3 | 13.2-59.9 | 16.2 | 12.50-70.87 | 0 | 0 | 3 recipes, 8 needed |
| W54 garden peas or petits pois,  | 60-150 | pasta_main | 2 | 2 | 77.5-97.5 | 87.5 | 75.00-100.00 | 0 | 0 | 2 recipes, 8 needed |
| W54 garden peas or petits pois,  | 60-150 | side_rice | 5 | 5 | 17.0-68.0 | 35.0 | 16.67-80.00 | 0 | 1 | 5 recipes, 8 needed |
| W54 garden peas or petits pois,  | 60-150 | soup | 7 | 7 | 11.8-56.7 | 37.5 | 8.33-66.67 | 0 | 0 | 7 recipes, 8 needed |
| W54 garden peas or petits pois,  | 60-150 | vegetable_starter | 2 | 2 | 37.6-138.6 | 88.1 | 25.00-151.20 | 0 | 0 | 2 recipes, 8 needed |
| W58 new or baby potatoes, boiled | 120-180 | any | 4 | 4 | 147.5-200.0 | 200.0 | 125.00-200.00 | 0 | 0 | 4 recipes, 15 needed |
| W58 new or baby potatoes, boiled | 120-180 | breakfast_cereal | 1 | 1 | 200.0-200.0 | 200.0 | 200.00-200.00 | 0 | 0 | 1 recipes, 8 needed |
| W58 new or baby potatoes, boiled | 120-180 | leaf_salad_starter | 1 | 1 | 125.0-125.0 | 125.0 | 125.00-125.00 | 0 | 0 | 1 recipes, 8 needed |
| W58 new or baby potatoes, boiled | 120-180 | meat_main | 1 | 1 | 200.0-200.0 | 200.0 | 200.00-200.00 | 0 | 0 | 1 recipes, 8 needed |
