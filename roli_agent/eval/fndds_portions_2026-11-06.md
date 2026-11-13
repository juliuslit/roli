# FNDDS portions as a plate-size source, 2026-11-06 (SPEC_3_mvp.md 12.16.8a)

Read through the nutrition service's portions call from USDA Survey (FNDDS) records found by a Survey-only search; the disk store answers repeats. A portion qualifies when its words name a whole dish, a fillet or steak, or a restaurant order; a cup, spoon, slice, piece or USDA's 'Quantity not specified' default never does. Gram weights are USDA's own.

USDA remaining after this pass: no request was needed (every answer came from the disk store) of the hourly allowance (reserve 200).

## fish_main: protein alone (cooked fillet)

- searched: fish cod baked or broiled; fish salmon baked or broiled; candidates: Fish, cod, baked or broiled, Fish, cod, baked or broiled, coated, Fish, bass, baked or broiled, Fish, catfish, baked or broiled, Fish, flounder, baked or broiled, Fish, haddock, baked or broiled, Fish, mackerel, baked or broiled, Fish, perch, baked or broiled, Fish, pompano, baked or broiled, Fish, salmon, baked or broiled, Fish, salmon, baked or broiled, coated
- **2706241 Fish, cod, baked or broiled**: 1 cup 135 g; 1 whole fish, any size 420 g (qualifies); 1 cubic inch 17 g; 1 steak 210 g (qualifies); Quantity not specified 140 g; 1 large fillet 210 g (qualifies); 1 oz yields 20 g; 1 small/regular fillet 140 g (qualifies)
- **2706295 Fish, bass, baked or broiled**: 1 small/regular fillet 90 g (qualifies); 1 large fillet 135 g (qualifies); 1 cubic inch 17 g; 1 cup 135 g; 1 oz yields 20 g; Quantity not specified 90 g
- **2706286 Fish, salmon, baked or broiled**: 1 large fillet 210 g (qualifies); 1 oz yields 20 g; 1 small/regular fillet 140 g (qualifies); 1 cup 135 g; 1 steak 210 g (qualifies); Quantity not specified 140 g; 1 cubic inch 17 g
- qualifying: 9 portions, 90-420 g (protein alone (cooked fillet)); converted to raw by x1.2418

## crudo_starter: protein alone (raw fish)

- searched: sashimi; fish tuna raw; fish salmon raw; candidates: Fish, salmon, raw, Fish, tuna, raw, Fish, tuna, canned, Fish, tuna, cooked, Fish, tuna, NFS, Fish, raw, Fish with cream or white sauce, not tuna or lobster, Fish, canned, Fish curry, Fish sauce, Fish, salmon, canned, Fish, salmon, fried ...
- **2706284 Fish, salmon, raw**: 1 cup 135 g; Quantity not specified 85 g
- **2706308 Fish, tuna, raw**: 1 cup 135 g; Quantity not specified 85 g
- qualifying: none; the records carry only measures, pieces or the unspecified default

## tomato_salad_starter: whole dish

- searched: tomato and mozzarella salad; caprese salad; tomato salad; candidates: Tomato and cucumber salad made with tomato, cucumber, oil, and vinegar, Mozzarella cheese, tomato, and basil, with oil and vinegar dressing, Lettuce, salad with assorted vegetables including tomatoes and/or carrots, no dressing, Lettuce, salad with assorted vegetables excluding tomatoes and carrots, no dressing, Lettuce, salad with avocado, tomato, and/or carrots, with or without other vegetables, no dressing, Lettuce, salad with cheese, tomato and/or carrots, with or without other vegetables, no dressing, Lettuce, salad with egg, tomato, and/or carrots, with or without other vegetables, no dressing, Lettuce, salad with egg, cheese, tomato, and/or carrots, with or without other vegetables, no dressing, Salad dressing, NFS, for salads, Seafood garden salad with seafood, lettuce, tomato and/or carrots, other vegetables, no dressing, Beef salad, Crab salad ...
- **2705818 Mozzarella cheese, tomato, and basil, with oil and vinegar dressing**: Quantity not specified 80 g; 1 cup 160 g
- qualifying: none; the records carry only measures, pieces or the unspecified default

## pasta_main: whole dish (plated pasta)

- searched: spaghetti with tomato sauce; pasta with meat sauce; lasagna with meat; candidates: Spaghetti sauce, Spaghetti sauce with meat, Spaghetti sauce with poultry, Spaghetti sauce with seafood, Spaghetti sauce with added vegetables, Spaghetti sauce, fat free, Spaghetti sauce, reduced sodium, Spaghetti sauce with seafood and added vegetables, Spaghetti sauce with meat and added vegetables, Spaghetti sauce with poultry and added vegetables, Pasta with cream sauce and meat, restaurant, Pasta with tomato-based sauce, cheese and meat ...
- **2708861 Pasta with cream sauce and meat, restaurant**: Quantity not specified 250 g; 1 cup 250 g
- **2708837 Pasta with tomato-based sauce and meat, restaurant**: 1 cup 250 g; Quantity not specified 250 g
- **2708752 Lasagna with meat, from restaurant**: 1 piece (1/6 of 8" square, approx 2-1/2" x 4") 206 g; 1 cup 250 g; Quantity not specified 250 g; 1 piece (1/8 of 7" x 12", approx 3-1/2" x 3") 232 g; 1 surface inch 21 g
- qualifying: none; the records carry only measures, pieces or the unspecified default

## fish_starter: whole dish (fried seafood plate)

- searched: calamari fried; shrimp breaded fried; crab cake; candidates: Calamari, fried, Calamari, cooked, Clams, fried, Crayfish, fried, Dove, fried, Fried broccoli, Fried cauliflower, Fried eggplant, Fried mushrooms, Fried okra, Shrimp, fried, Rice, fried, with shrimp ...
- **2706334 Calamari, fried**: Quantity not specified 85 g; 1 item 15 g; 1 cup 135 g
- **2706364 Shrimp, fried**: 1 prawn 20 g; 1 tiny shrimp 5 g; 1 large/jumbo shrimp 15 g; Quantity not specified 85 g; 1 small/medium shrimp 10 g; 1 cup 135 g
- **2706549 Crab, cake**: 1 cake or patty 85 g; Quantity not specified 85 g
- qualifying: none; the records carry only measures, pieces or the unspecified default

## pizza_neapolitan: whole dish (whole pizza)

- searched: pizza cheese regular crust; pizza cheese thin crust; pizza cheese; pizza pepperoni; candidates: Pizza, cheese, stuffed crust, Pizza, no cheese, thick crust, Pizza, no cheese, thin crust, Pizza, extra cheese, thick crust, White pizza, cheese, thick crust, Pizza, cheese, with fruit, thick crust, Pizza, cheese, with fruit, thin crust, Pizza, extra cheese, thin crust, Pizza, cheese, with fruit, medium crust, White pizza, cheese, thin crust, Pizza, cheese, from frozen, thin crust, Pizza with cheese and extra vegetables, thin crust ...
- **2708674 Pizza, no cheese, thin crust**: 1 extra-large pizza (16-18" diameter) 809 g; 1 piece, NFS 75 g; Quantity not specified 150 g; 1 surface inch 4 g; 1 piece, extra-large pizza 81 g; 1 personal size pizza (5-7" diameter) 110 g (qualifies); 1 medium pizza (11-12" diameter) 432 g (qualifies); 1 piece, small pizza 51 g; 1 piece, large pizza 75 g; 1 piece, medium pizza 54 g; 1 large pizza (13-15" diameter) 599 g (qualifies); 1 small pizza (8-10" diameter) 306 g (qualifies)
- **2708623 Pizza, extra cheese, thick crust**: 1 medium pizza (11-12" diameter) 792 g (qualifies); 1 piece, NFS 141 g; 1/2 English muffin 58 g; 1 piece, medium pizza 99 g; 1 piece, large pizza 141 g; 1/2 bagel 98 g; 1 small pizza (8-10" diameter) 565 g (qualifies); Quantity not specified 282 g; 1 extra-large pizza (16-18" diameter) 1448 g; 1 surface inch 7 g; 1 large pizza (13-15" diameter) 1112 g (qualifies); 1 piece, extra-large pizza 145 g; 1 piece, small pizza 94 g; 1 personal size pizza (5-7" diameter) 232 g (qualifies); 1 French bread 154 g
- **2708622 Pizza, extra cheese, thin crust**: 1 extra-large pizza (16-18" diameter) 1056 g; 1 piece, medium pizza 66 g; 1 large pizza (13-15" diameter) 732 g (qualifies); 1 personal size pizza (5-7" diameter) 136 g (qualifies); 1 surface inch 5 g; 1 piece, large pizza 92 g; Quantity not specified 184 g; 1 piece, NFS 92 g; 1 piece, small pizza 63 g; 1 piece, extra-large pizza 106 g; 1 medium pizza (11-12" diameter) 528 g (qualifies); 1 small pizza (8-10" diameter) 377 g (qualifies)
- qualifying: 12 portions, 110-1112 g (whole dish (whole pizza)); dough = x0.5694

## leaf_salad_starter: whole dish

- searched: caesar salad; lettuce salad with assorted vegetables; candidates: Caesar salad, with romaine, no dressing, Caesar dressing, Chicken or turkey caesar garden salad, chicken and/or turkey, lettuce, tomato, cheese, no dressing, Caesar dressing, light, Chicken or turkey, breaded, fried, caesar garden salad, chicken and/or turkey, lettuce, tomatoes, cheese, no dressing, Caesar dressing, fat free, Salad dressing, NFS, for salads, Beef salad, Crab salad, Lobster salad, Lettuce, salad with assorted vegetables including tomatoes and/or carrots, no dressing, Lettuce, salad with assorted vegetables excluding tomatoes and carrots, no dressing ...
- **2709591 Caesar salad, with romaine, no dressing**: 1 cup 79 g; Quantity not specified 79 g; 1 Wendy's side salad 113 g (qualifies)
- **2709822 Lettuce, salad with assorted vegetables including tomatoes and/or carrots, no dressing**: 1 McDonald's side salad 87 g (qualifies); 1 cup 73 g; Quantity not specified 73 g; 1 side salad 94 g (qualifies); 1 Burger King side salad 98 g (qualifies); 1 Wendy's side salad 168 g (qualifies)
- qualifying: 5 portions, 87-168 g (whole dish)

## meat_main: protein alone (cooked cut)

- searched: steak beef broiled; chicken breast grilled; pork chop broiled; candidates: Beef, steak, round, Beef, sandwich steak, Beef, steak, chuck, Beef, steak, cube, Beef, steak, flank, Beef, steak, NFS, Beef, steak, tenderloin, Beef, steak, country fried, Beef steak with onions, Puerto Rican style, Beef, steak, ribeye, lean and fat eaten, Chicken breast, grilled with sauce, skin eaten, Chicken breast, grilled with sauce, skin not eaten ...
- **2705824 Beef, steak, NFS**: Quantity not specified 160 g; 1 oz yields 20 g; 1 regular 160 g (qualifies); 1 piece/slice, any size 30 g; 1 thick 240 g (qualifies); 1 cup 135 g; 1 thin 120 g (qualifies); 1 cubic inch 17 g
- **2705841 Beef, steak, tenderloin**: 1 regular 160 g (qualifies); 1 cup 135 g; 1 piece/slice, any size 30 g; 1 oz yields 20 g; 1 thin 120 g (qualifies); 1 thick 240 g (qualifies); Quantity not specified 160 g; 1 cubic inch 17 g
- **2705829 Beef, steak, ribeye, lean and fat eaten**: 1 thin 180 g (qualifies); 1 cup 135 g; 1 oz yields 20 g; Quantity not specified 240 g; 1 cubic inch 17 g; 1 thick 360 g (qualifies); 1 regular 240 g (qualifies); 1 piece/slice, any size 30 g
- **2705968 Chicken breast, grilled without sauce, skin not eaten**: 1 medium breast 120 g (qualifies); 1 large or thick slice 85 g; 1 small breast 105 g (qualifies); 1 cup, cooked, diced 135 g; Quantity not specified 120 g; 1 oz, cooked 28 g; 1 breast quarter (yield after cooking, bone removed) 155 g; 1 large breast 135 g (qualifies); 1 small or thin slice 30 g; 1 medium slice 60 g
- **2705866 Pork, chop, NS as to fat eaten**: 1 oz yields 20 g; 1 thick 180 g (qualifies); Quantity not specified 120 g; 1 cubic inch 17 g; 1 slice, any size 30 g; 1 regular 120 g (qualifies); 1 cup 135 g; 1 thin 90 g (qualifies)
- qualifying: 15 portions, 90-360 g (protein alone (cooked cut)); converted to raw by x1.2500

## vegetable_starter: whole dish

- searched: vegetables grilled; bruschetta; candidates: Scallops, grilled, Shrimp, grilled, Chicken fillet, grilled, Fish sandwich, grilled, Fish, bass, grilled, Fish, catfish, grilled, Fish, cod, grilled, Fish, flounder, grilled, Fish, haddock, grilled, Fish, mackerel, grilled, Bruschetta
- **2707652 Bruschetta**: 1 large or thick slice 59 g; 1 slice 43 g; 1 slice, snack-size 14 g; 1 small or thin/very thin slice 32 g; 1 medium or regular slice 43 g; Quantity not specified 43 g
- qualifying: none; the records carry only measures, pieces or the unspecified default

## fried_potato_side: whole dish (an order of fries)

- searched: potato french fries restaurant; candidates: Potato, french fries, restaurant, Potato, french fries, with cheese, fast food / restaurant, Potato, french fries, with chili, fast food / restaurant, Potato, french fries, with chili and cheese, fast food / restaurant, Potato, french fries, with cheese, Potato, french fries, with chili, Potato, french fries, NFS, Potato, french fries, school, Potato, french fries, from fresh, fried, Potato, french fries, from frozen, fried
- **2709462 Potato, french fries, restaurant**: 1 crinkle cut 5 g; 1 value/dollar menu order 85 g (qualifies); 1 medium fast food order 145 g (qualifies); 1 straight cut 5 g; 1 fry, NS as to shape 5 g; 1 wedge 9 g; 1 waffle 8 g; 1 cup 60 g; 1 spiral or curly 8 g; 1 kids meal order 70 g (qualifies); 1 small fast food order 110 g (qualifies); 1 shoestring 2 g; 1 large fast food order 180 g (qualifies); Quantity not specified 110 g
- qualifying: 5 portions, 70-180 g (whole dish (an order of fries))

## snack_bowl: whole dish

- searched: olives; almonds roasted; candidates: Olive tapenade, Olive oil, Olives, black, Olives, green, Olives, NFS, Olives, stuffed, Mayonnaise, reduced fat,  with olive oil, Bread, vegetable, Bread, vegetable, toasted, Codfish salad, Puerto Rican style, Serenata, Almonds, honey roasted, Almonds, unsalted ...
- **2710088 Olives, NFS**: Quantity not specified 15 g; 1 olive 5 g; 1 cup 135 g
- **2707487 Almonds, salted**: 1 package 50 g; 1 cup 141 g; 1 100 calorie package 18 g; 1 oz 28 g; 1 nut 1 g; Quantity not specified 28 g
- qualifying: none; the records carry only measures, pieces or the unspecified default

## fish_and_chips: protein alone (fried fillet)

- searched: fish and chips; fish battered fried; candidates: Fish curry, Fish sauce, Fish, anchovy, Fish, canned, Fish, carp, Fish, croaker, Fish, eel, Fish, halibut, Fish, herring, Fish, mullet, Fish, bass, fried, Fish, catfish, fried ...
- **2706244 Fish, cod, fried**: 1 large fillet 210 g (qualifies); 1 cubic inch 17 g; 1 small/regular fillet 140 g (qualifies); 1 cup 135 g; 1 steak 210 g (qualifies); Quantity not specified 140 g; 1 oz yields 20 g; 1 whole fish, any size 420 g (qualifies)
- **2706258 Fish, haddock, fried**: 1 small/regular fillet 140 g (qualifies); 1 cubic inch 17 g; Quantity not specified 140 g; 1 whole fish, any size 420 g (qualifies); 1 cup 135 g; 1 oz yields 20 g; 1 large fillet 210 g (qualifies); 1 steak 210 g (qualifies)
- qualifying: 8 portions, 140-420 g (protein alone (fried fillet))

## burger: whole dish (whole item)

- searched: hamburger on bun; cheeseburger on bun; candidates: Roll, white, hamburger bun, Roll, multigrain, hamburger bun, Roll, whole wheat, hamburger bun, Hamburger, on white bun, 1 small patty, Hamburger, on white bun, 1 medium patty, Hamburger, on wheat bun, 1 large patty, Hamburger, on wheat bun, 1 medium patty, Hamburger, on wheat bun, 1 small patty, Hamburger, on white bun, 1 large patty, Roll, wheat or cracked wheat, hamburger bun, Cheeseburger, on white bun, 1 small patty, Cheeseburger, on white bun, 1 medium patty ...
- **2706927 Hamburger, on white bun, 1 small patty**: Quantity not specified 115 g; 1 hamburger 115 g (qualifies)
- **2706932 Hamburger, on white bun, 1 medium patty**: Quantity not specified 145 g; 1 hamburger 145 g (qualifies)
- **2706934 Hamburger, on white bun, 1 large patty**: Quantity not specified 175 g; 1 hamburger 175 g (qualifies)
- **2706895 Cheeseburger, on white bun, 1 small patty**: Quantity not specified 135 g; 1 cheeseburger 135 g (qualifies)
- **2706901 Cheeseburger, on white bun, 1 medium patty**: Quantity not specified 165 g; 1 cheeseburger 165 g (qualifies)
- qualifying: 5 portions, 115-175 g (whole dish (whole item))

## sandwich: whole dish (whole item)

- searched: chicken sandwich; turkey sandwich; ham and cheese sandwich; candidates: Chicken fillet sandwich, NFS, Chicken salad sandwich on wheat, Chicken salad sandwich on white, Chicken salad sandwich wrap, Chicken deli sandwich or sub, restaurant, Barbecue chicken sandwich, on wheat bun, Barbecue chicken sandwich, on white bun, Chicken fillet sandwich, from school cafeteria, Chicken deli sandwich or sub, with cheese, restaurant, Chicken fillet sandwich, fried, on wheat bun, Turkey sandwich on wheat, Turkey sandwich on white ...
- **2707000 Chicken fillet sandwich, NFS**: 1 sandwich, any size 140 g (qualifies); Quantity not specified 140 g
- **2706988 Chicken deli sandwich or sub, restaurant**: 1 regular 130 g (qualifies); 1 large 195 g (qualifies); Quantity not specified 130 g; 1 miniature/slider 65 g; 1 regular or 6" submarine 195 g (qualifies)
- **2706985 Turkey sandwich or sub, restaurant**: Quantity not specified 130 g; 1 miniature/slider 65 g; 1 regular 130 g (qualifies); 1 large 195 g (qualifies); 1 regular or 6" submarine 195 g (qualifies)
- **2706969 Ham sandwich or sub, with cheese, restaurant**: 1 miniature/slider 80 g; 1 regular 160 g (qualifies); 1 large 240 g (qualifies); Quantity not specified 160 g; 1 regular or 6" submarine 240 g (qualifies)
- qualifying: 10 portions, 130-240 g (whole dish (whole item))

## wrap: whole dish (whole item)

- searched: chicken wrap; wrap sandwich; candidates: Chicken salad sandwich wrap, Chicken fillet wrap sandwich, fried, from fast food, Chicken fillet wrap sandwich, grilled, from fast food, Turkey sandwich wrap, Fish wrap sandwich, Ham sandwich wrap, Sandwich wrap, NFS, Vegetable sandwich wrap, Multiple meat sandwich wrap, Tuna salad sandwich wrap, Hamburger wrap sandwich, from fast food
- **2707017 Chicken fillet wrap sandwich, grilled, from fast food**: 1 sandwich, any size 161 g (qualifies); Quantity not specified 161 g
- **2706987 Turkey sandwich wrap**: 1 sandwich, any size 135 g (qualifies); Quantity not specified 135 g
- **2706881 Sandwich wrap, NFS**: Quantity not specified 140 g; 1 sandwich, any size 140 g (qualifies)
- qualifying: 3 portions, 135-161 g (whole dish (whole item))

## taco: whole dish (one taco)

- searched: taco with chicken; taco with beef; candidates: Taco or tostada salad with chicken, Taco, flour tortilla, chicken, cheese, Taco, corn tortilla, chicken, cheese, Taco, flour tortilla, chicken, with beans, cheese, Taco, corn tortilla, chicken, with beans, cheese, Taco or tostada salad with chicken and sour cream, Taco sauce, Taco, fish, Taco, NFS, Taco shell, flour, Beef taco filling: beef, cheese, tomato, taco sauce, Taco, flour tortilla, beef, cheese ...
- **2708526 Taco, flour tortilla, chicken, cheese**: Quantity not specified 105 g; 1 large 160 g (qualifies); 1 cup 120 g; 1 small/regular 105 g (qualifies); 1 miniature 50 g
- **2708529 Taco, fish**: Quantity not specified 100 g; 1 cup 120 g; 1 small/regular 100 g (qualifies); 1 miniature 50 g; 1 large 150 g (qualifies)
- **2708514 Taco, NFS**: Quantity not specified 105 g; 1 large 160 g (qualifies); 1 small/regular 105 g (qualifies); 1 cup 120 g; 1 miniature 50 g
- **2708522 Taco, flour tortilla, beef, cheese**: 1 small/regular 105 g (qualifies); 1 large 160 g (qualifies); Quantity not specified 105 g; 1 miniature 50 g; 1 cup 120 g
- qualifying: 8 portions, 100-160 g (whole dish (one taco))

## burrito: whole dish (whole item)

- searched: burrito with beef and beans; burrito chicken; candidates: Burrito, beef, with beans, cheese, Burrito bowl, beef or pork, with beans, Burrito, beef, with beans and rice, cheese, Burrito bowl, beef or pork, with beans and rice, Burrito, beef, cheese, Burrito bowl, with beans, Burrito, with beans, cheese, Burrito, with beans, no cheese, Burrito bowl, beef or pork, Burrito, beef, with rice, cheese, Burrito bowl, chicken, Burrito, chicken, cheese ...
- **2708537 Burrito, beef, with beans, cheese**: Quantity not specified 220 g; 1 small/regular 220 g (qualifies); 1 miniature 110 g; 1 cup 120 g; 1 large 330 g (qualifies)
- **2708543 Burrito, chicken, cheese**: 1 miniature 110 g; 1 cup 120 g; Quantity not specified 220 g; 1 small/regular 220 g (qualifies); 1 large 330 g (qualifies)
- **2708546 Burrito, chicken, with beans and rice, cheese**: 1 miniature 110 g; 1 large 330 g (qualifies); Quantity not specified 220 g; 1 cup 120 g; 1 small/regular 220 g (qualifies)
- **2708534 Burrito, NFS**: 1 cup 120 g; Quantity not specified 220 g; 1 small/regular 220 g (qualifies); 1 large 330 g (qualifies); 1 miniature 110 g
- qualifying: 8 portions, 220-330 g (whole dish (whole item))

## quesadilla: whole dish (whole item)

- searched: quesadilla with chicken; quesadilla cheese; candidates: Quesadilla, chicken, Quesadilla, chicken, with vegetables, Quesadilla, egg, Quesadilla, NFS, Quesadilla, with vegetables, Quesadilla, beef or pork, Quesadilla, cheese only, Quesadilla, egg, with meat, Quesadilla, beef or pork, with vegetables, Chicken, chicken roll, roasted, Cheese, processed cheese food
- **2708593 Quesadilla, chicken**: 1 full circle 140 g; 1 cup 95 g; 1 half circle 70 g; 1 triangular piece 35 g; Quantity not specified 70 g
- **2708590 Quesadilla, NFS**: Quantity not specified 70 g; 1 triangular piece 35 g; 1 half circle 70 g; 1 full circle 140 g; 1 cup 95 g
- **2708591 Quesadilla, cheese only**: 1 triangular piece 30 g; 1 half circle 60 g; Quantity not specified 60 g; 1 full circle 120 g; 1 cup 95 g
- qualifying: none; the records carry only measures, pieces or the unspecified default

## breakfast_eggs: whole dish

- searched: egg omelet with cheese; eggs benedict; scrambled eggs; candidates: Egg omelet or scrambled egg, with cheese, made with butter, Egg omelet or scrambled egg, with cheese, made with margarine, Egg omelet or scrambled egg, with cheese, made with oil, Egg omelet or scrambled egg, with cheese, no added fat, Egg substitute, omelet, scrambled, or fried, with cheese, Egg white, omelet, scrambled, or fried, with cheese, Egg omelet or scrambled egg, with cheese and meat, made with butter, Egg omelet or scrambled egg, with cheese and meat, made with margarine, Egg omelet or scrambled egg, with cheese and meat, made with oil, Egg omelet or scrambled egg, with cheese and meat, no added fat, Egg, Benedict, Egg, creamed ...
- **2707212 Egg omelet or scrambled egg, with cheese, no added fat**: 1 egg 60 g; Quantity not specified 120 g; 1 cup 135 g
- **2707180 Egg, Benedict**: 1 egg 155 g; Quantity not specified 155 g
- **2707205 Egg omelet or scrambled egg, no added fat**: Quantity not specified 100 g; 1 egg 50 g; 1 cup 135 g
- qualifying: none; the records carry only measures, pieces or the unspecified default

## breakfast_pancakes: whole dish

- searched: pancakes plain; waffle plain; french toast; candidates: Pancakes, plain, Pancakes, plain, frozen, Pancakes, plain, reduced fat, Pancakes, plain, fast food / restaurant, Chinese pancake, Pancake syrup, Pancakes, chocolate, Pancakes, fruit, Pancakes, NFS, Pancakes, pumpkin, Waffle, plain, Waffle, plain, frozen ...
- **2708299 Pancakes, plain, fast food / restaurant**: 1 silver dollar pancake 20 g; 1 large pancake 90 g; 1 extra large pancake 150 g; 1 small pancake 20 g; Quantity not specified 100 g; 1 medium pancake 50 g; 1 surface inch 2 g; 1 miniature/bite size pancake 10 g
- **2708320 Waffle, plain, fast food / restaurant**: 1 large waffle 125 g; 1 miniature/bite size waffle 10 g; 1 surface inch 2 g; 1 medium waffle 75 g; 1 thick / Belgian waffle 135 g; Quantity not specified 75 g; 1 small waffle 40 g; 1 surface inch, Belgian waffle 4 g
- **2708333 French toast, fast food / restaurant**: Quantity not specified 85 g; 1 slice, any size 85 g
- qualifying: none; the records carry only measures, pieces or the unspecified default

## breakfast_cereal: whole dish (a bowl)

- searched: oatmeal cooked; granola; candidates: Oatmeal, multigrain, Oatmeal, NFS, Bread, oatmeal, Cookie, oatmeal, Crackers, oatmeal, Muffin, oatmeal, Pie, oatmeal, Roll, oatmeal, Cookie, oatmeal, with raisins, Snack bar, oatmeal, Cookie, granola, Cereal, granola ...
- **2708380 Oatmeal, NFS**: 1 cup, cooked 240 g; 1 cup, dry, yields 485 g; 1 oz, dry, yields 170 g; Quantity not specified 240 g
- **2708461 Cereal, granola**: Quantity not specified 110 g; 1 prepackaged single serving 30 g; 1 cup 110 g
- qualifying: none; the records carry only measures, pieces or the unspecified default

## toast_plate: whole dish

- searched: bread toasted; toast with butter; candidates: Bread, rye, toasted, Bread, vegetable, toasted, Bread, white, toasted, Bread, barley, toasted, Bread, black, toasted, Bread, cheese, toasted, Bread, cinnamon, toasted, Bread, Cuban, toasted, Bread, multigrain, toasted, Bread, oatmeal, toasted, Melba toast, Anisette toast ...
- **2707599 Bread, white, toasted**: 1 cup 40 g; 1 cubic inch 4 g; Quantity not specified 25 g; 1 slice, snack-size 9 g; 1 small or thin/very thin slice 22 g; 1 slice, crust not eaten 12 g; 1 large or thick slice 39 g; 1 medium or regular slice 25 g
- **2707776 Bread, multigrain, toasted**: Quantity not specified 33 g; 1 large or thick slice 39 g; 1 slice, crust not eaten 15 g; 1 small or thin/very thin slice 22 g; 1 medium or regular slice 33 g; 1 slice, snack-size 9 g
- qualifying: none; the records carry only measures, pieces or the unspecified default

## soup: whole dish (a bowl)

- searched: soup chicken noodle; soup tomato; soup vegetable; candidates: Soup, chicken noodle, Soup, chicken noodle, canned, Soup, noodle, NFS, Soup, chicken, Soup, ramen noodles, water added, Chicken or turkey and noodles with gravy, Chicken or turkey and noodles, no sauce, Soup, chicken, canned, Soup, cream of chicken, Chicken or turkey and noodles with cheese sauce, Soup, tomato, Soup, cream of tomato ...
- **2709149 Soup, chicken noodle**: Quantity not specified 245 g; 1 cup 245 g
- **2709757 Soup, tomato**: 1 cup 245 g; Quantity not specified 245 g
- **2710113 Soup, vegetable**: Quantity not specified 245 g; 1 cup 245 g
- qualifying: none; the records carry only measures, pieces or the unspecified default

## dip: whole dish (a pot)

- searched: hummus; guacamole; dip cheese; candidates: Hummus, flavored, Hummus, plain, Bean chips, Guacamole, NFS, Guacamole with tomatoes, Cheese dip, Cheese dip with chili pepper, Seafood dip, Dessert dip, Layer dip, Tzatziki dip, Dip, NFS ...
- **2707402 Hummus, plain**: 1 individual container 70 g; 1 tablespoon 15 g; Quantity not specified 60 g
- **2709307 Guacamole, NFS**: 1 tablespoon 15 g; 1 individual container 70 g; Quantity not specified 60 g
- **2705618 Dip, NFS**: Quantity not specified 60 g; 1 tablespoon 15 g; 1 individual container 70 g
- qualifying: none; the records carry only measures, pieces or the unspecified default

## side_salad: whole dish

- searched: lettuce salad with assorted vegetables; garden salad; candidates: Lettuce, salad with assorted vegetables including tomatoes and/or carrots, no dressing, Lettuce, salad with assorted vegetables excluding tomatoes and carrots, no dressing, Lettuce, salad with avocado, tomato, and/or carrots, with or without other vegetables, no dressing, Lettuce, salad with cheese, tomato and/or carrots, with or without other vegetables, no dressing, Lettuce, salad with egg, tomato, and/or carrots, with or without other vegetables, no dressing, Lettuce, salad with egg, cheese, tomato, and/or carrots, with or without other vegetables, no dressing, Seafood garden salad with seafood, lettuce, tomato and/or carrots, other vegetables, no dressing, Seafood garden salad with seafood, lettuce, vegetables excluding tomato and carrots, no dressing, Seafood garden salad with seafood, lettuce, eggs, tomato and/or carrots, other vegetables, no dressing, Seafood garden salad with seafood, lettuce, eggs, vegetables excluding tomato and carrots, no dressing, Chicken or turkey caesar garden salad, chicken and/or turkey, lettuce, tomato, cheese, no dressing, Asian chicken or turkey garden salad, chicken and/or turkey, lettuce, fruit, nuts, no dressing ...
- **2709822 Lettuce, salad with assorted vegetables including tomatoes and/or carrots, no dressing**: 1 McDonald's side salad 87 g (qualifies); 1 cup 73 g; Quantity not specified 73 g; 1 side salad 94 g (qualifies); 1 Burger King side salad 98 g (qualifies); 1 Wendy's side salad 168 g (qualifies)
- **2709823 Lettuce, salad with assorted vegetables excluding tomatoes and carrots, no dressing**: Quantity not specified 74 g; 1 cup 74 g
- qualifying: 4 portions, 87-168 g (whole dish)

## side_vegetable: whole dish (a side)

- searched: broccoli cooked; green beans cooked; vegetables mixed cooked; candidates: Broccoli raab, cooked, Broccoli, Chinese, cooked, Broccoli, cooked, as ingredient, Broccoli, cooked, from restaurant, Broccoli, fresh, cooked with oil, Broccoli, frozen, cooked with oil, Broccoli, NS as to form, cooked, Broccoli, fresh, cooked, no added fat, Broccoli, frozen, cooked, no added fat, Broccoli and cauliflower, cooked, no added fat, Green beans, cooked, as ingredient, Green beans, cooked, Szechuan-style ...
- **2709644 Broccoli, cooked, from restaurant**: 1 floweret 10 g; 1 cup 160 g; 1 piece 10 g; Quantity not specified 80 g; 1 spear 40 g
- **2709851 Green beans, cooked, from restaurant**: Quantity not specified 73 g; 1 bean 6 g; 1 cut piece 2 g; 1 cup 145 g
- **2710012 Classic mixed vegetables, cooked, from restaurant**: Quantity not specified 93 g; 1 cup 185 g
- qualifying: none; the records carry only measures, pieces or the unspecified default

## side_rice: whole dish (a side)

- searched: rice white cooked; rice pilaf; candidates: Rice, white, cooked, glutinous, Rice, white, cooked, as ingredient, Rice, white, cooked, made with oil, Rice, white, cooked, no added fat, Rice, white, cooked, NS as to fat, Rice, white, cooked, made with margarine, Rice, white, cooked, made with butter, Rice, white and wild, cooked, fat added, Rice, white and wild, cooked, no added fat, Rice, white and wild, cooked, NS as to fat, Rice pilaf, Dirty rice ...
- **2708403 Rice, white, cooked, NS as to fat**: 1 cup, cooked 163 g; Quantity not specified 122 g
- **2709077 Rice pilaf**: Quantity not specified 155 g; 1 cup 206 g
- qualifying: none; the records carry only measures, pieces or the unspecified default

## side_bread: whole dish (an order)

- searched: garlic bread; bread roll; breadsticks; candidates: Garlic bread, NFS, Garlic bread, from frozen, Garlic bread, from fast food / restaurant, Garlic bread, with melted cheese, from frozen, Garlic bread, with parmesan cheese, from frozen, Garlic bread, with parmesan cheese, from fast food / restaurant, Garlic bread, with melted cheese, from fast food / restaurant, Garlic sauce, Garlic, cooked, Garlic, raw, Roll, egg bread, Roll, multigrain ...
- **2707627 Garlic bread, from fast food / restaurant**: 1 baguette (about 22" long) 376 g; Quantity not specified 74 g; 1 small slice 37 g; 1 medium slice 74 g; 1 mini baguette (about 9" long) 176 g; 1 large slice 111 g; 1 piece/slice Texas Toast 40 g
- **2707662 Roll, garlic**: 1 medium/regular/sandwich size roll 35 g; Quantity not specified 43 g; 1 miniature/small roll 28 g; 1 large roll 43 g
- **2707693 Breadsticks, soft, fast food / restaurant**: 1 garlic knot 34 g; 1 small stick 26 g; Quantity not specified 50 g; 1 medium stick 40 g; 1 large stick 50 g
- qualifying: none; the records carry only measures, pieces or the unspecified default

## dessert: whole dish (one dessert)

- searched: cake chocolate with icing; cheesecake; brownie; ice cream; candidates: Cake or cupcake, chocolate, no icing, Cake or cupcake, chocolate with chocolate icing, bakery, Doughnut, cake type, chocolate icing, Cake or cupcake, chocolate with chocolate icing, from mix, Cake or cupcake, white with chocolate icing, bakery, Cake or cupcake, chocolate with white icing, bakery, Ice cream cake, Cake or cupcake, white with chocolate icing, from mix, Cake or cupcake, chocolate with white icing, from mix, Cake or cupcake, white, no icing, Cheesecake, chocolate, Cheesecake, fruit ...
- **2707866 Cake or cupcake, chocolate with chocolate icing, bakery**: 1 regular cupcake 90 g; Quantity not specified 175 g; 1 regular or small piece/slice, 2+ layer cake 175 g (qualifies); 1 cup 100 g; 1 regular or small piece/slice, 1 layer cake 115 g (qualifies); 1 cubic inch 7 g; 1 miniature/bite size 30 g; 1 large piece/slice, 1 layer cake 170 g (qualifies); 1 large piece/slice, 2+ layer cake 260 g (qualifies)
- **2707861 Cheesecake, plain**: Quantity not specified 175 g; 1 cup 180 g; 1 piece/slice, any size 175 g (qualifies)
- **2707904 Cookie, brownie, without icing**: 1 small or bite size 30 g; 1 medium 50 g; Quantity not specified 50 g; 1 large 90 g
- **2705630 Ice cream, vanilla**: 1 individual container 75 g (qualifies); 1 medium ice cream cup 240 g; 1 small ice cream cup 120 g; 1 scoop 120 g (qualifies); 1 large ice cream cup 360 g; Quantity not specified 135 g; 1 cubic inch 9 g; 1 cup 135 g
- qualifying: 7 portions, 75-260 g (whole dish (one dessert))

## kids_dish: whole dish

- searched: chicken nuggets; macaroni and cheese; candidates: Chicken nuggets, NFS, Chicken nuggets, from frozen, Chicken nuggets, from restaurant, Chicken nuggets, from fast food, Chicken nuggets, from other sources, Chicken nuggets, from school lunch, Turkey, nuggets, Chicken patty, or nuggets, boneless, breaded, potatoes, vegetable, frozen meal, Chicken, chicken roll, roasted, Orange chicken, Macaroni or noodles with cheese, Beef and macaroni with cheese sauce ...
- **2706094 Chicken nuggets, from restaurant**: Quantity not specified 80 g; 1 nugget 16 g; 1 cup 140 g
- **2708811 Macaroni or noodles with cheese**: 1 cup 230 g; Quantity not specified 230 g
- qualifying: none; the records carry only measures, pieces or the unspecified default

