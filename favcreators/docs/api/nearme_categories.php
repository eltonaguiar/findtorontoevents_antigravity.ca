<?php
/**
 * Near Me Categories, Landmarks, Dietary Tags, Crisis Resources
 * PHP 5.2 compatible — no closures, no short array syntax, no ?:
 *
 * Used by nearme.php to map user queries to Foursquare category IDs,
 * resolve Toronto landmarks/intersections, detect crisis queries,
 * and provide dietary/delivery metadata.
 */

// ============================================================
// A. FOURSQUARE CATEGORY MAPPINGS
//    Maps lowercase user terms -> array('query' => ..., 'categories' => '...')
//    'categories' = comma-separated Foursquare v3 category IDs
//    'query' = optimized Foursquare query string
//    'group' = category group for delivery suggestions
// ============================================================

function nearme_get_category_map() {
    $map = array(
        // --- DINING: Coffee & Tea ---
        'coffee' => array('query' => 'coffee shop', 'categories' => '13034,13032', 'group' => 'food'),
        'coffee shop' => array('query' => 'coffee shop', 'categories' => '13034', 'group' => 'food'),
        'coffee shops' => array('query' => 'coffee shop', 'categories' => '13034', 'group' => 'food'),
        'cafe' => array('query' => 'cafe', 'categories' => '13032', 'group' => 'food'),
        'cafes' => array('query' => 'cafe', 'categories' => '13032', 'group' => 'food'),
        'tea' => array('query' => 'tea room', 'categories' => '13035', 'group' => 'food'),
        'tea shop' => array('query' => 'tea room', 'categories' => '13035', 'group' => 'food'),
        'bubble tea' => array('query' => 'bubble tea', 'categories' => '13032', 'group' => 'food'),
        'boba' => array('query' => 'bubble tea', 'categories' => '13032', 'group' => 'food'),
        'tim hortons' => array('query' => 'Tim Hortons', 'categories' => '13034', 'group' => 'food'),
        'tims' => array('query' => 'Tim Hortons', 'categories' => '13034', 'group' => 'food'),
        'starbucks' => array('query' => 'Starbucks', 'categories' => '13034', 'group' => 'food'),

        // --- DINING: Restaurants by Cuisine ---
        'restaurant' => array('query' => 'restaurant', 'categories' => '13065', 'group' => 'food'),
        'restaurants' => array('query' => 'restaurant', 'categories' => '13065', 'group' => 'food'),
        'chinese restaurant' => array('query' => 'chinese restaurant', 'categories' => '13099', 'group' => 'food'),
        'chinese restaurants' => array('query' => 'chinese restaurant', 'categories' => '13099', 'group' => 'food'),
        'chinese food' => array('query' => 'chinese restaurant', 'categories' => '13099', 'group' => 'food'),
        'indian restaurant' => array('query' => 'indian restaurant', 'categories' => '13148', 'group' => 'food'),
        'indian restaurants' => array('query' => 'indian restaurant', 'categories' => '13148', 'group' => 'food'),
        'indian food' => array('query' => 'indian restaurant', 'categories' => '13148', 'group' => 'food'),
        'italian restaurant' => array('query' => 'italian restaurant', 'categories' => '13192', 'group' => 'food'),
        'italian restaurants' => array('query' => 'italian restaurant', 'categories' => '13192', 'group' => 'food'),
        'italian food' => array('query' => 'italian restaurant', 'categories' => '13192', 'group' => 'food'),
        'mexican restaurant' => array('query' => 'mexican restaurant', 'categories' => '13236', 'group' => 'food'),
        'mexican restaurants' => array('query' => 'mexican restaurant', 'categories' => '13236', 'group' => 'food'),
        'mexican food' => array('query' => 'mexican restaurant', 'categories' => '13236', 'group' => 'food'),
        'thai restaurant' => array('query' => 'thai restaurant', 'categories' => '13263', 'group' => 'food'),
        'thai restaurants' => array('query' => 'thai restaurant', 'categories' => '13263', 'group' => 'food'),
        'thai food' => array('query' => 'thai restaurant', 'categories' => '13263', 'group' => 'food'),
        'japanese restaurant' => array('query' => 'japanese restaurant', 'categories' => '13302', 'group' => 'food'),
        'japanese restaurants' => array('query' => 'japanese restaurant', 'categories' => '13302', 'group' => 'food'),
        'japanese food' => array('query' => 'japanese restaurant', 'categories' => '13302', 'group' => 'food'),
        'korean restaurant' => array('query' => 'korean restaurant', 'categories' => '13352', 'group' => 'food'),
        'korean restaurants' => array('query' => 'korean restaurant', 'categories' => '13352', 'group' => 'food'),
        'korean food' => array('query' => 'korean restaurant', 'categories' => '13352', 'group' => 'food'),
        'vietnamese restaurant' => array('query' => 'vietnamese restaurant', 'categories' => '13065', 'group' => 'food'),
        'vietnamese food' => array('query' => 'vietnamese restaurant', 'categories' => '13065', 'group' => 'food'),
        'greek restaurant' => array('query' => 'greek restaurant', 'categories' => '13065', 'group' => 'food'),
        'greek food' => array('query' => 'greek restaurant', 'categories' => '13065', 'group' => 'food'),
        'caribbean restaurant' => array('query' => 'caribbean restaurant', 'categories' => '13065', 'group' => 'food'),
        'caribbean food' => array('query' => 'caribbean restaurant', 'categories' => '13065', 'group' => 'food'),
        'jerk chicken' => array('query' => 'caribbean jerk chicken', 'categories' => '13065', 'group' => 'food'),
        'ethiopian restaurant' => array('query' => 'ethiopian restaurant', 'categories' => '13065', 'group' => 'food'),
        'ethiopian food' => array('query' => 'ethiopian restaurant', 'categories' => '13065', 'group' => 'food'),
        'middle eastern restaurant' => array('query' => 'middle eastern restaurant', 'categories' => '13065', 'group' => 'food'),
        'middle eastern food' => array('query' => 'middle eastern restaurant', 'categories' => '13065', 'group' => 'food'),
        'filipino restaurant' => array('query' => 'filipino restaurant', 'categories' => '13065', 'group' => 'food'),
        'filipino food' => array('query' => 'filipino restaurant', 'categories' => '13065', 'group' => 'food'),
        'portuguese restaurant' => array('query' => 'portuguese restaurant', 'categories' => '13065', 'group' => 'food'),
        'portuguese food' => array('query' => 'portuguese restaurant', 'categories' => '13065', 'group' => 'food'),
        'brazilian restaurant' => array('query' => 'brazilian restaurant', 'categories' => '13065', 'group' => 'food'),
        'brazilian food' => array('query' => 'brazilian restaurant', 'categories' => '13065', 'group' => 'food'),
        'french restaurant' => array('query' => 'french restaurant', 'categories' => '13065', 'group' => 'food'),
        'french food' => array('query' => 'french restaurant', 'categories' => '13065', 'group' => 'food'),
        'turkish restaurant' => array('query' => 'turkish restaurant', 'categories' => '13065', 'group' => 'food'),
        'turkish food' => array('query' => 'turkish restaurant', 'categories' => '13065', 'group' => 'food'),
        'persian restaurant' => array('query' => 'persian restaurant', 'categories' => '13065', 'group' => 'food'),
        'persian food' => array('query' => 'persian restaurant', 'categories' => '13065', 'group' => 'food'),
        'afghan restaurant' => array('query' => 'afghan restaurant', 'categories' => '13065', 'group' => 'food'),
        'lebanese restaurant' => array('query' => 'lebanese restaurant', 'categories' => '13065', 'group' => 'food'),
        'lebanese food' => array('query' => 'lebanese restaurant', 'categories' => '13065', 'group' => 'food'),
        'mediterranean restaurant' => array('query' => 'mediterranean restaurant', 'categories' => '13383', 'group' => 'food'),
        'mediterranean food' => array('query' => 'mediterranean restaurant', 'categories' => '13383', 'group' => 'food'),

        // --- DINING: Specific Food Types ---
        'pizza' => array('query' => 'pizza', 'categories' => '13064', 'group' => 'food'),
        'pizza place' => array('query' => 'pizza', 'categories' => '13064', 'group' => 'food'),
        'pizza places' => array('query' => 'pizza', 'categories' => '13064', 'group' => 'food'),
        'pizza shop' => array('query' => 'pizza', 'categories' => '13064', 'group' => 'food'),
        'sushi' => array('query' => 'sushi', 'categories' => '13068', 'group' => 'food'),
        'sushi restaurant' => array('query' => 'sushi restaurant', 'categories' => '13068', 'group' => 'food'),
        'ramen' => array('query' => 'ramen', 'categories' => '13272', 'group' => 'food'),
        'ramen shop' => array('query' => 'ramen', 'categories' => '13272', 'group' => 'food'),
        'pho' => array('query' => 'pho', 'categories' => '13065', 'group' => 'food'),
        'shawarma' => array('query' => 'shawarma', 'categories' => '13065', 'group' => 'food'),
        'tacos' => array('query' => 'tacos', 'categories' => '13065', 'group' => 'food'),
        'taco' => array('query' => 'tacos', 'categories' => '13065', 'group' => 'food'),
        'burgers' => array('query' => 'burger', 'categories' => '13031', 'group' => 'food'),
        'burger' => array('query' => 'burger', 'categories' => '13031', 'group' => 'food'),
        'burger joint' => array('query' => 'burger', 'categories' => '13031', 'group' => 'food'),
        'wings' => array('query' => 'chicken wings', 'categories' => '13065', 'group' => 'food'),
        'chicken wings' => array('query' => 'chicken wings', 'categories' => '13065', 'group' => 'food'),
        'fried chicken' => array('query' => 'fried chicken', 'categories' => '13065', 'group' => 'food'),
        'hot dog' => array('query' => 'hot dog', 'categories' => '13145', 'group' => 'food'),
        'hot dogs' => array('query' => 'hot dog', 'categories' => '13145', 'group' => 'food'),
        'hot dog stand' => array('query' => 'hot dog stand', 'categories' => '13145', 'group' => 'food'),
        'hot dog stands' => array('query' => 'hot dog stand', 'categories' => '13145', 'group' => 'food'),
        'sandwich' => array('query' => 'sandwich shop', 'categories' => '13065', 'group' => 'food'),
        'sandwiches' => array('query' => 'sandwich shop', 'categories' => '13065', 'group' => 'food'),
        'sub' => array('query' => 'sub sandwich', 'categories' => '13065', 'group' => 'food'),
        'subway' => array('query' => 'Subway sandwich', 'categories' => '13065', 'group' => 'food'),
        'deli' => array('query' => 'deli', 'categories' => '13039', 'group' => 'food'),
        'delis' => array('query' => 'deli', 'categories' => '13039', 'group' => 'food'),
        'seafood' => array('query' => 'seafood restaurant', 'categories' => '13338', 'group' => 'food'),
        'seafood restaurant' => array('query' => 'seafood restaurant', 'categories' => '13338', 'group' => 'food'),
        'steak' => array('query' => 'steakhouse', 'categories' => '13065', 'group' => 'food'),
        'steakhouse' => array('query' => 'steakhouse', 'categories' => '13065', 'group' => 'food'),
        'bbq' => array('query' => 'bbq restaurant', 'categories' => '13065', 'group' => 'food'),
        'barbecue' => array('query' => 'bbq restaurant', 'categories' => '13065', 'group' => 'food'),
        'noodles' => array('query' => 'noodle house', 'categories' => '13065', 'group' => 'food'),
        'dim sum' => array('query' => 'dim sum', 'categories' => '13099', 'group' => 'food'),
        'curry' => array('query' => 'curry restaurant', 'categories' => '13148', 'group' => 'food'),
        'biryani' => array('query' => 'biryani', 'categories' => '13148', 'group' => 'food'),
        'kebab' => array('query' => 'kebab', 'categories' => '13065', 'group' => 'food'),
        'falafel' => array('query' => 'falafel', 'categories' => '13065', 'group' => 'food'),
        'gyro' => array('query' => 'gyro', 'categories' => '13065', 'group' => 'food'),
        'poutine' => array('query' => 'poutine', 'categories' => '13065', 'group' => 'food'),

        // --- DINING: Fast Food & Quick Service ---
        'fast food' => array('query' => 'fast food', 'categories' => '13145', 'group' => 'food'),
        'mcdonalds' => array('query' => 'McDonalds', 'categories' => '13145', 'group' => 'food'),
        'wendys' => array('query' => 'Wendys', 'categories' => '13145', 'group' => 'food'),
        'kfc' => array('query' => 'KFC', 'categories' => '13145', 'group' => 'food'),
        'popeyes' => array('query' => 'Popeyes', 'categories' => '13145', 'group' => 'food'),
        'food truck' => array('query' => 'food truck', 'categories' => '13145', 'group' => 'food'),
        'food trucks' => array('query' => 'food truck', 'categories' => '13145', 'group' => 'food'),
        'food court' => array('query' => 'food court', 'categories' => '13065', 'group' => 'food'),

        // --- DINING: Bakery, Dessert, Ice Cream ---
        'bakery' => array('query' => 'bakery', 'categories' => '13025', 'group' => 'food'),
        'bakeries' => array('query' => 'bakery', 'categories' => '13025', 'group' => 'food'),
        'donut' => array('query' => 'donut shop', 'categories' => '13025', 'group' => 'food'),
        'donuts' => array('query' => 'donut shop', 'categories' => '13025', 'group' => 'food'),
        'donut shop' => array('query' => 'donut shop', 'categories' => '13025', 'group' => 'food'),
        'doughnut' => array('query' => 'donut shop', 'categories' => '13025', 'group' => 'food'),
        'dessert' => array('query' => 'dessert shop', 'categories' => '13040', 'group' => 'food'),
        'desserts' => array('query' => 'dessert shop', 'categories' => '13040', 'group' => 'food'),
        'ice cream' => array('query' => 'ice cream', 'categories' => '13046', 'group' => 'food'),
        'ice cream shop' => array('query' => 'ice cream shop', 'categories' => '13046', 'group' => 'food'),
        'gelato' => array('query' => 'gelato', 'categories' => '13046', 'group' => 'food'),
        'frozen yogurt' => array('query' => 'frozen yogurt', 'categories' => '13046', 'group' => 'food'),
        'pastry' => array('query' => 'pastry shop', 'categories' => '13025', 'group' => 'food'),
        'cake' => array('query' => 'cake shop', 'categories' => '13025', 'group' => 'food'),

        // --- DINING: Brunch, Breakfast, Buffet ---
        'brunch' => array('query' => 'brunch', 'categories' => '13065', 'group' => 'food'),
        'breakfast' => array('query' => 'breakfast restaurant', 'categories' => '13065', 'group' => 'food'),
        'buffet' => array('query' => 'buffet', 'categories' => '13065', 'group' => 'food'),
        'all you can eat' => array('query' => 'buffet all you can eat', 'categories' => '13065', 'group' => 'food'),
        'diner' => array('query' => 'diner', 'categories' => '13065', 'group' => 'food'),

        // --- DINING: Juice & Smoothies ---
        'juice' => array('query' => 'juice bar', 'categories' => '13032', 'group' => 'food'),
        'juice bar' => array('query' => 'juice bar', 'categories' => '13032', 'group' => 'food'),
        'smoothie' => array('query' => 'smoothie', 'categories' => '13032', 'group' => 'food'),
        'smoothies' => array('query' => 'smoothie', 'categories' => '13032', 'group' => 'food'),

        // --- DINING: Bars & Nightlife ---
        'bar' => array('query' => 'bar', 'categories' => '13003', 'group' => 'food'),
        'bars' => array('query' => 'bar', 'categories' => '13003', 'group' => 'food'),
        'pub' => array('query' => 'pub', 'categories' => '13003', 'group' => 'food'),
        'pubs' => array('query' => 'pub', 'categories' => '13003', 'group' => 'food'),
        'brewery' => array('query' => 'brewery', 'categories' => '13029', 'group' => 'food'),
        'breweries' => array('query' => 'brewery', 'categories' => '13029', 'group' => 'food'),
        'wine bar' => array('query' => 'wine bar', 'categories' => '13003', 'group' => 'food'),
        'cocktail bar' => array('query' => 'cocktail bar', 'categories' => '13003', 'group' => 'food'),
        'sports bar' => array('query' => 'sports bar', 'categories' => '13003', 'group' => 'food'),
        'lounge' => array('query' => 'lounge', 'categories' => '13003', 'group' => 'food'),
        'nightclub' => array('query' => 'nightclub', 'categories' => '10032', 'group' => 'entertainment'),
        'nightclubs' => array('query' => 'nightclub', 'categories' => '10032', 'group' => 'entertainment'),
        'club' => array('query' => 'nightclub', 'categories' => '10032', 'group' => 'entertainment'),
        'hookah' => array('query' => 'hookah lounge', 'categories' => '13003', 'group' => 'food'),
        'hookah lounge' => array('query' => 'hookah lounge', 'categories' => '13003', 'group' => 'food'),
        'shisha' => array('query' => 'hookah lounge', 'categories' => '13003', 'group' => 'food'),

        // --- SERVICES ---
        'gas station' => array('query' => 'gas station', 'categories' => '19007', 'group' => 'services'),
        'gas stations' => array('query' => 'gas station', 'categories' => '19007', 'group' => 'services'),
        'gas' => array('query' => 'gas station', 'categories' => '19007', 'group' => 'services'),
        'petrol' => array('query' => 'gas station', 'categories' => '19007', 'group' => 'services'),
        'pharmacy' => array('query' => 'pharmacy', 'categories' => '17035', 'group' => 'pharmacy'),
        'pharmacies' => array('query' => 'pharmacy', 'categories' => '17035', 'group' => 'pharmacy'),
        'drug store' => array('query' => 'pharmacy', 'categories' => '17035', 'group' => 'pharmacy'),
        'drugstore' => array('query' => 'pharmacy', 'categories' => '17035', 'group' => 'pharmacy'),
        'shoppers drug mart' => array('query' => 'Shoppers Drug Mart', 'categories' => '17035', 'group' => 'pharmacy'),
        'bank' => array('query' => 'bank', 'categories' => '11045', 'group' => 'services'),
        'banks' => array('query' => 'bank', 'categories' => '11045', 'group' => 'services'),
        'post office' => array('query' => 'post office', 'categories' => '12071', 'group' => 'services'),
        'canada post' => array('query' => 'Canada Post', 'categories' => '12071', 'group' => 'services'),
        'laundromat' => array('query' => 'laundromat', 'categories' => '11060', 'group' => 'services'),
        'laundry' => array('query' => 'laundromat', 'categories' => '11060', 'group' => 'services'),
        'car wash' => array('query' => 'car wash', 'categories' => '19009', 'group' => 'services'),
        'hair salon' => array('query' => 'hair salon', 'categories' => '11057', 'group' => 'services'),
        'hair salons' => array('query' => 'hair salon', 'categories' => '11057', 'group' => 'services'),
        'barber' => array('query' => 'barber shop', 'categories' => '11057', 'group' => 'services'),
        'barber shop' => array('query' => 'barber shop', 'categories' => '11057', 'group' => 'services'),
        'dry cleaner' => array('query' => 'dry cleaner', 'categories' => '11060', 'group' => 'services'),
        'dry cleaners' => array('query' => 'dry cleaner', 'categories' => '11060', 'group' => 'services'),
        'tailor' => array('query' => 'tailor', 'categories' => '11060', 'group' => 'services'),
        'locksmith' => array('query' => 'locksmith', 'categories' => '11060', 'group' => 'services'),
        'auto repair' => array('query' => 'auto repair', 'categories' => '19001', 'group' => 'services'),
        'mechanic' => array('query' => 'auto mechanic', 'categories' => '19001', 'group' => 'services'),
        'tire shop' => array('query' => 'tire shop', 'categories' => '19001', 'group' => 'services'),
        'oil change' => array('query' => 'oil change', 'categories' => '19001', 'group' => 'services'),
        'printing' => array('query' => 'print shop', 'categories' => '11060', 'group' => 'services'),
        'print shop' => array('query' => 'print shop', 'categories' => '11060', 'group' => 'services'),
        'notary' => array('query' => 'notary', 'categories' => '11060', 'group' => 'services'),
        'cell phone repair' => array('query' => 'cell phone repair', 'categories' => '11060', 'group' => 'services'),
        'phone repair' => array('query' => 'phone repair', 'categories' => '11060', 'group' => 'services'),
        'nail salon' => array('query' => 'nail salon', 'categories' => '11057', 'group' => 'services'),
        'spa' => array('query' => 'spa', 'categories' => '11057', 'group' => 'services'),
        'massage' => array('query' => 'massage', 'categories' => '11057', 'group' => 'services'),

        // --- FACILITIES ---
        'washroom' => array('query' => 'public restroom', 'categories' => '16000', 'group' => 'facilities'),
        'washrooms' => array('query' => 'public restroom', 'categories' => '16000', 'group' => 'facilities'),
        'restroom' => array('query' => 'public restroom', 'categories' => '16000', 'group' => 'facilities'),
        'restrooms' => array('query' => 'public restroom', 'categories' => '16000', 'group' => 'facilities'),
        'bathroom' => array('query' => 'public restroom', 'categories' => '16000', 'group' => 'facilities'),
        'bathrooms' => array('query' => 'public restroom', 'categories' => '16000', 'group' => 'facilities'),
        'toilet' => array('query' => 'public restroom', 'categories' => '16000', 'group' => 'facilities'),
        'toilets' => array('query' => 'public restroom', 'categories' => '16000', 'group' => 'facilities'),
        'parking' => array('query' => 'parking', 'categories' => '19020', 'group' => 'facilities'),
        'parking lot' => array('query' => 'parking lot', 'categories' => '19020', 'group' => 'facilities'),
        'parking garage' => array('query' => 'parking garage', 'categories' => '19020', 'group' => 'facilities'),
        'atm' => array('query' => 'ATM', 'categories' => '11044', 'group' => 'facilities'),
        'atms' => array('query' => 'ATM', 'categories' => '11044', 'group' => 'facilities'),
        'transit' => array('query' => 'transit station', 'categories' => '19042', 'group' => 'transit'),
        'transit stop' => array('query' => 'transit stop', 'categories' => '19042', 'group' => 'transit'),
        'bus stop' => array('query' => 'bus stop', 'categories' => '19042', 'group' => 'transit'),
        'subway station' => array('query' => 'subway station', 'categories' => '19043', 'group' => 'transit'),
        'subway' => array('query' => 'subway station', 'categories' => '19043', 'group' => 'transit'),
        'ttc' => array('query' => 'TTC station', 'categories' => '19043', 'group' => 'transit'),
        'water fountain' => array('query' => 'water fountain', 'categories' => '16000', 'group' => 'facilities'),
        'wifi' => array('query' => 'free wifi', 'categories' => '13032', 'group' => 'facilities'),
        'public wifi' => array('query' => 'free wifi', 'categories' => '13032', 'group' => 'facilities'),

        // --- ACCOMMODATION ---
        'hotel' => array('query' => 'hotel', 'categories' => '19014', 'group' => 'accommodation'),
        'hotels' => array('query' => 'hotel', 'categories' => '19014', 'group' => 'accommodation'),
        'hostel' => array('query' => 'hostel', 'categories' => '19014', 'group' => 'accommodation'),
        'hostels' => array('query' => 'hostel', 'categories' => '19014', 'group' => 'accommodation'),
        'motel' => array('query' => 'motel', 'categories' => '19014', 'group' => 'accommodation'),
        'motels' => array('query' => 'motel', 'categories' => '19014', 'group' => 'accommodation'),
        'bed and breakfast' => array('query' => 'bed and breakfast', 'categories' => '19014', 'group' => 'accommodation'),
        'bnb' => array('query' => 'bed and breakfast', 'categories' => '19014', 'group' => 'accommodation'),
        'airbnb' => array('query' => 'bed and breakfast', 'categories' => '19014', 'group' => 'accommodation'),
        'lodging' => array('query' => 'hotel', 'categories' => '19014', 'group' => 'accommodation'),

        // --- ENTERTAINMENT ---
        'movie theater' => array('query' => 'movie theater', 'categories' => '10024', 'group' => 'entertainment'),
        'movie theatre' => array('query' => 'movie theater', 'categories' => '10024', 'group' => 'entertainment'),
        'movies' => array('query' => 'movie theater', 'categories' => '10024', 'group' => 'entertainment'),
        'cinema' => array('query' => 'cinema', 'categories' => '10024', 'group' => 'entertainment'),
        'theater' => array('query' => 'theater', 'categories' => '10025', 'group' => 'entertainment'),
        'theatre' => array('query' => 'theatre', 'categories' => '10025', 'group' => 'entertainment'),
        'park' => array('query' => 'park', 'categories' => '16032', 'group' => 'entertainment'),
        'parks' => array('query' => 'park', 'categories' => '16032', 'group' => 'entertainment'),
        'playground' => array('query' => 'playground', 'categories' => '16032', 'group' => 'entertainment'),
        'museum' => array('query' => 'museum', 'categories' => '10027', 'group' => 'entertainment'),
        'museums' => array('query' => 'museum', 'categories' => '10027', 'group' => 'entertainment'),
        'art gallery' => array('query' => 'art gallery', 'categories' => '10025', 'group' => 'entertainment'),
        'gallery' => array('query' => 'art gallery', 'categories' => '10025', 'group' => 'entertainment'),
        'gym' => array('query' => 'gym', 'categories' => '18021', 'group' => 'entertainment'),
        'gyms' => array('query' => 'gym', 'categories' => '18021', 'group' => 'entertainment'),
        'fitness' => array('query' => 'fitness center', 'categories' => '18021', 'group' => 'entertainment'),
        'yoga' => array('query' => 'yoga studio', 'categories' => '18021', 'group' => 'entertainment'),
        'bowling' => array('query' => 'bowling alley', 'categories' => '10003', 'group' => 'entertainment'),
        'bowling alley' => array('query' => 'bowling alley', 'categories' => '10003', 'group' => 'entertainment'),
        'arcade' => array('query' => 'arcade', 'categories' => '10001', 'group' => 'entertainment'),
        'arcades' => array('query' => 'arcade', 'categories' => '10001', 'group' => 'entertainment'),
        'karaoke' => array('query' => 'karaoke', 'categories' => '10032', 'group' => 'entertainment'),
        'escape room' => array('query' => 'escape room', 'categories' => '10001', 'group' => 'entertainment'),
        'escape rooms' => array('query' => 'escape room', 'categories' => '10001', 'group' => 'entertainment'),
        'pool hall' => array('query' => 'pool hall billiards', 'categories' => '10001', 'group' => 'entertainment'),
        'billiards' => array('query' => 'billiards pool hall', 'categories' => '10001', 'group' => 'entertainment'),
        'comedy club' => array('query' => 'comedy club', 'categories' => '10025', 'group' => 'entertainment'),
        'concert venue' => array('query' => 'concert venue', 'categories' => '10025', 'group' => 'entertainment'),
        'live music' => array('query' => 'live music venue', 'categories' => '10025', 'group' => 'entertainment'),
        'zoo' => array('query' => 'zoo', 'categories' => '10056', 'group' => 'entertainment'),
        'aquarium' => array('query' => 'aquarium', 'categories' => '10056', 'group' => 'entertainment'),
        'amusement park' => array('query' => 'amusement park', 'categories' => '10001', 'group' => 'entertainment'),
        'skating' => array('query' => 'skating rink', 'categories' => '18021', 'group' => 'entertainment'),
        'skating rink' => array('query' => 'skating rink', 'categories' => '18021', 'group' => 'entertainment'),
        'ice skating' => array('query' => 'ice skating rink', 'categories' => '18021', 'group' => 'entertainment'),
        'rec center' => array('query' => 'recreation center', 'categories' => '18021', 'group' => 'entertainment'),
        'recreation center' => array('query' => 'recreation center', 'categories' => '18021', 'group' => 'entertainment'),
        'swimming pool' => array('query' => 'swimming pool', 'categories' => '18021', 'group' => 'entertainment'),
        'pool' => array('query' => 'swimming pool', 'categories' => '18021', 'group' => 'entertainment'),
        'beach' => array('query' => 'beach', 'categories' => '16032', 'group' => 'entertainment'),
        'trampoline park' => array('query' => 'trampoline park', 'categories' => '10001', 'group' => 'entertainment'),
        'mini golf' => array('query' => 'mini golf', 'categories' => '10001', 'group' => 'entertainment'),
        'golf' => array('query' => 'golf course', 'categories' => '18021', 'group' => 'entertainment'),
        'tennis' => array('query' => 'tennis court', 'categories' => '18021', 'group' => 'entertainment'),
        'basketball court' => array('query' => 'basketball court', 'categories' => '18021', 'group' => 'entertainment'),

        // --- SHOPPING ---
        'grocery store' => array('query' => 'grocery store', 'categories' => '17069', 'group' => 'retail'),
        'grocery stores' => array('query' => 'grocery store', 'categories' => '17069', 'group' => 'retail'),
        'grocery' => array('query' => 'grocery store', 'categories' => '17069', 'group' => 'retail'),
        'groceries' => array('query' => 'grocery store', 'categories' => '17069', 'group' => 'retail'),
        'supermarket' => array('query' => 'supermarket', 'categories' => '17069', 'group' => 'retail'),
        'mall' => array('query' => 'shopping mall', 'categories' => '17114', 'group' => 'retail'),
        'malls' => array('query' => 'shopping mall', 'categories' => '17114', 'group' => 'retail'),
        'shopping mall' => array('query' => 'shopping mall', 'categories' => '17114', 'group' => 'retail'),
        'convenience store' => array('query' => 'convenience store', 'categories' => '17069', 'group' => 'retail'),
        'corner store' => array('query' => 'convenience store', 'categories' => '17069', 'group' => 'retail'),
        'bookstore' => array('query' => 'bookstore', 'categories' => '17018', 'group' => 'retail'),
        'book store' => array('query' => 'bookstore', 'categories' => '17018', 'group' => 'retail'),
        'clothing store' => array('query' => 'clothing store', 'categories' => '17028', 'group' => 'retail'),
        'clothes' => array('query' => 'clothing store', 'categories' => '17028', 'group' => 'retail'),
        'thrift store' => array('query' => 'thrift store', 'categories' => '17028', 'group' => 'retail'),
        'thrift shop' => array('query' => 'thrift store', 'categories' => '17028', 'group' => 'retail'),
        'electronics store' => array('query' => 'electronics store', 'categories' => '17040', 'group' => 'retail'),
        'electronics' => array('query' => 'electronics store', 'categories' => '17040', 'group' => 'retail'),
        'computer parts' => array('query' => 'computer store electronics', 'categories' => '17040', 'group' => 'retail'),
        'computer store' => array('query' => 'computer store', 'categories' => '17040', 'group' => 'retail'),
        'phone store' => array('query' => 'mobile phone store', 'categories' => '17040', 'group' => 'retail'),
        'pet store' => array('query' => 'pet store', 'categories' => '17089', 'group' => 'retail'),
        'pet shop' => array('query' => 'pet store', 'categories' => '17089', 'group' => 'retail'),
        'hardware store' => array('query' => 'hardware store', 'categories' => '17072', 'group' => 'retail'),
        'home depot' => array('query' => 'Home Depot', 'categories' => '17072', 'group' => 'retail'),
        'dollar store' => array('query' => 'dollar store', 'categories' => '17000', 'group' => 'retail'),
        'dollarama' => array('query' => 'Dollarama', 'categories' => '17000', 'group' => 'retail'),
        'liquor store' => array('query' => 'liquor store', 'categories' => '17073', 'group' => 'retail'),
        'lcbo' => array('query' => 'LCBO', 'categories' => '17073', 'group' => 'retail'),
        'beer store' => array('query' => 'Beer Store', 'categories' => '17073', 'group' => 'retail'),
        'wine' => array('query' => 'wine store', 'categories' => '17073', 'group' => 'retail'),
        'cannabis' => array('query' => 'cannabis dispensary', 'categories' => '17000', 'group' => 'retail'),
        'dispensary' => array('query' => 'cannabis dispensary', 'categories' => '17000', 'group' => 'retail'),
        'weed store' => array('query' => 'cannabis dispensary', 'categories' => '17000', 'group' => 'retail'),
        'sporting goods' => array('query' => 'sporting goods store', 'categories' => '17000', 'group' => 'retail'),
        'sports store' => array('query' => 'sporting goods store', 'categories' => '17000', 'group' => 'retail'),
        'toy store' => array('query' => 'toy store', 'categories' => '17000', 'group' => 'retail'),
        'flower shop' => array('query' => 'flower shop florist', 'categories' => '17000', 'group' => 'retail'),
        'florist' => array('query' => 'florist', 'categories' => '17000', 'group' => 'retail'),
        'gift shop' => array('query' => 'gift shop', 'categories' => '17000', 'group' => 'retail'),
        'hand warmers' => array('query' => 'convenience store outdoor supplies', 'categories' => '17069,17000', 'group' => 'retail'),
        'walmart' => array('query' => 'Walmart', 'categories' => '17000', 'group' => 'retail'),
        'canadian tire' => array('query' => 'Canadian Tire', 'categories' => '17072', 'group' => 'retail'),
        'costco' => array('query' => 'Costco', 'categories' => '17069', 'group' => 'retail'),
        'winners' => array('query' => 'Winners', 'categories' => '17028', 'group' => 'retail'),

        // --- HEALTHCARE ---
        'hospital' => array('query' => 'hospital', 'categories' => '15014', 'group' => 'healthcare'),
        'hospitals' => array('query' => 'hospital', 'categories' => '15014', 'group' => 'healthcare'),
        'emergency room' => array('query' => 'emergency room hospital', 'categories' => '15014', 'group' => 'healthcare'),
        'er' => array('query' => 'emergency room hospital', 'categories' => '15014', 'group' => 'healthcare'),
        'walk in clinic' => array('query' => 'walk-in clinic', 'categories' => '15014', 'group' => 'healthcare'),
        'walk-in clinic' => array('query' => 'walk-in clinic', 'categories' => '15014', 'group' => 'healthcare'),
        'clinic' => array('query' => 'medical clinic', 'categories' => '15014', 'group' => 'healthcare'),
        'doctor' => array('query' => 'doctor medical clinic', 'categories' => '15014', 'group' => 'healthcare'),
        'dentist' => array('query' => 'dentist', 'categories' => '15014', 'group' => 'healthcare'),
        'dental' => array('query' => 'dentist dental', 'categories' => '15014', 'group' => 'healthcare'),
        'vet' => array('query' => 'veterinarian', 'categories' => '15014', 'group' => 'healthcare'),
        'veterinarian' => array('query' => 'veterinarian', 'categories' => '15014', 'group' => 'healthcare'),
        'animal hospital' => array('query' => 'animal hospital veterinarian', 'categories' => '15014', 'group' => 'healthcare'),
        'urgent care' => array('query' => 'urgent care clinic', 'categories' => '15014', 'group' => 'healthcare'),
        'optometrist' => array('query' => 'optometrist eye care', 'categories' => '15014', 'group' => 'healthcare'),
        'eye doctor' => array('query' => 'optometrist', 'categories' => '15014', 'group' => 'healthcare'),
        'physiotherapy' => array('query' => 'physiotherapy', 'categories' => '15014', 'group' => 'healthcare'),
        'physio' => array('query' => 'physiotherapy', 'categories' => '15014', 'group' => 'healthcare'),
        'chiropractor' => array('query' => 'chiropractor', 'categories' => '15014', 'group' => 'healthcare'),
        'mental health' => array('query' => 'mental health clinic', 'categories' => '15014', 'group' => 'healthcare'),
        'therapist' => array('query' => 'therapist counseling', 'categories' => '15014', 'group' => 'healthcare'),

        // --- TRANSPORTATION ---
        'car rental' => array('query' => 'car rental', 'categories' => '19004', 'group' => 'transit'),
        'car rentals' => array('query' => 'car rental', 'categories' => '19004', 'group' => 'transit'),
        'taxi' => array('query' => 'taxi stand', 'categories' => '19042', 'group' => 'transit'),
        'taxi stand' => array('query' => 'taxi stand', 'categories' => '19042', 'group' => 'transit'),
        'uber' => array('query' => 'uber pickup point', 'categories' => '19042', 'group' => 'transit'),
        'bike share' => array('query' => 'bike share', 'categories' => '19042', 'group' => 'transit'),
        'bike rental' => array('query' => 'bike rental', 'categories' => '19042', 'group' => 'transit'),
        'ev charging' => array('query' => 'EV charging station', 'categories' => '19007', 'group' => 'transit'),
        'ev charger' => array('query' => 'EV charging station', 'categories' => '19007', 'group' => 'transit'),
        'electric vehicle charging' => array('query' => 'EV charging station', 'categories' => '19007', 'group' => 'transit'),
        'train station' => array('query' => 'train station', 'categories' => '19043', 'group' => 'transit'),
        'go station' => array('query' => 'GO Transit station', 'categories' => '19043', 'group' => 'transit'),
        'go train' => array('query' => 'GO Transit station', 'categories' => '19043', 'group' => 'transit'),
        'airport' => array('query' => 'airport', 'categories' => '19040', 'group' => 'transit'),

        // --- COMMUNITY ---
        'library' => array('query' => 'library', 'categories' => '12063', 'group' => 'community'),
        'libraries' => array('query' => 'library', 'categories' => '12063', 'group' => 'community'),
        'school' => array('query' => 'school', 'categories' => '12058', 'group' => 'community'),
        'university' => array('query' => 'university', 'categories' => '12058', 'group' => 'community'),
        'college' => array('query' => 'college', 'categories' => '12058', 'group' => 'community'),
        'church' => array('query' => 'church', 'categories' => '12101', 'group' => 'community'),
        'churches' => array('query' => 'church', 'categories' => '12101', 'group' => 'community'),
        'mosque' => array('query' => 'mosque', 'categories' => '12101', 'group' => 'community'),
        'mosques' => array('query' => 'mosque', 'categories' => '12101', 'group' => 'community'),
        'temple' => array('query' => 'temple', 'categories' => '12101', 'group' => 'community'),
        'synagogue' => array('query' => 'synagogue', 'categories' => '12101', 'group' => 'community'),
        'gurdwara' => array('query' => 'gurdwara', 'categories' => '12101', 'group' => 'community'),
        'police station' => array('query' => 'police station', 'categories' => '12072', 'group' => 'community'),
        'police' => array('query' => 'police station', 'categories' => '12072', 'group' => 'community'),
        'fire station' => array('query' => 'fire station', 'categories' => '12072', 'group' => 'community'),
        'community center' => array('query' => 'community center', 'categories' => '12058', 'group' => 'community'),
        'community centre' => array('query' => 'community centre', 'categories' => '12058', 'group' => 'community'),
        'food bank' => array('query' => 'food bank', 'categories' => '12058', 'group' => 'community'),
        'food banks' => array('query' => 'food bank', 'categories' => '12058', 'group' => 'community'),
        'shelter' => array('query' => 'shelter', 'categories' => '12058', 'group' => 'community'),
        'shelters' => array('query' => 'shelter', 'categories' => '12058', 'group' => 'community'),
        'homeless shelter' => array('query' => 'homeless shelter', 'categories' => '12058', 'group' => 'community'),
        'warming center' => array('query' => 'warming center shelter', 'categories' => '12058', 'group' => 'community'),
        'warming centre' => array('query' => 'warming centre shelter', 'categories' => '12058', 'group' => 'community'),
        'drop in' => array('query' => 'drop in center', 'categories' => '12058', 'group' => 'community')
    );
    return $map;
}


// ============================================================
// B. DIETARY / RESTRICTION TAGS
// ============================================================

function nearme_get_dietary_keywords() {
    return array(
        'halal' => array('modifier' => 'halal', 'note' => 'Halal certified'),
        'kosher' => array('modifier' => 'kosher', 'note' => 'Kosher certified'),
        'vegan' => array('modifier' => 'vegan', 'note' => 'Vegan options'),
        'vegetarian' => array('modifier' => 'vegetarian', 'note' => 'Vegetarian options'),
        'gluten free' => array('modifier' => 'gluten free', 'note' => 'Gluten-free options'),
        'gluten-free' => array('modifier' => 'gluten free', 'note' => 'Gluten-free options'),
        'dairy free' => array('modifier' => 'dairy free', 'note' => 'Dairy-free options'),
        'dairy-free' => array('modifier' => 'dairy free', 'note' => 'Dairy-free options'),
        'nut free' => array('modifier' => '', 'note' => 'Nut-free -- call ahead to confirm'),
        'nut-free' => array('modifier' => '', 'note' => 'Nut-free -- call ahead to confirm'),
        'organic' => array('modifier' => 'organic', 'note' => 'Organic options'),
        'keto' => array('modifier' => 'keto', 'note' => 'Keto-friendly options'),
        'paleo' => array('modifier' => 'paleo', 'note' => 'Paleo-friendly options')
    );
}


// ============================================================
// C. TORONTO LANDMARKS GEOCODING TABLE
// ============================================================

function nearme_get_landmarks() {
    return array(
        // Major landmarks
        'eaton centre' => array('lat' => 43.6544, 'lng' => -79.3807),
        'toronto eaton centre' => array('lat' => 43.6544, 'lng' => -79.3807),
        'cn tower' => array('lat' => 43.6426, 'lng' => -79.3871),
        'union station' => array('lat' => 43.6453, 'lng' => -79.3806),
        'dundas square' => array('lat' => 43.6561, 'lng' => -79.3802),
        'yonge dundas square' => array('lat' => 43.6561, 'lng' => -79.3802),
        'yonge-dundas square' => array('lat' => 43.6561, 'lng' => -79.3802),
        'harbourfront' => array('lat' => 43.6389, 'lng' => -79.3815),
        'harbourfront centre' => array('lat' => 43.6389, 'lng' => -79.3815),
        'distillery district' => array('lat' => 43.6503, 'lng' => -79.3596),
        'distillery' => array('lat' => 43.6503, 'lng' => -79.3596),
        'rom' => array('lat' => 43.6677, 'lng' => -79.3948),
        'royal ontario museum' => array('lat' => 43.6677, 'lng' => -79.3948),
        'scotiabank arena' => array('lat' => 43.6435, 'lng' => -79.3791),
        'rogers centre' => array('lat' => 43.6414, 'lng' => -79.3894),
        'skydome' => array('lat' => 43.6414, 'lng' => -79.3894),
        'nathan phillips square' => array('lat' => 43.6525, 'lng' => -79.3834),
        'city hall' => array('lat' => 43.6525, 'lng' => -79.3834),
        'toronto city hall' => array('lat' => 43.6525, 'lng' => -79.3834),
        'st lawrence market' => array('lat' => 43.6487, 'lng' => -79.3716),
        'st. lawrence market' => array('lat' => 43.6487, 'lng' => -79.3716),
        'kensington market' => array('lat' => 43.6547, 'lng' => -79.4005),
        'kensington' => array('lat' => 43.6547, 'lng' => -79.4005),
        'high park' => array('lat' => 43.6465, 'lng' => -79.4637),
        'exhibition place' => array('lat' => 43.6353, 'lng' => -79.4178),
        'cne' => array('lat' => 43.6353, 'lng' => -79.4178),
        'ontario place' => array('lat' => 43.6291, 'lng' => -79.4120),
        'ago' => array('lat' => 43.6536, 'lng' => -79.3925),
        'art gallery of ontario' => array('lat' => 43.6536, 'lng' => -79.3925),
        'casa loma' => array('lat' => 43.6780, 'lng' => -79.4094),
        'toronto islands' => array('lat' => 43.6205, 'lng' => -79.3782),
        'centre island' => array('lat' => 43.6205, 'lng' => -79.3782),
        'toronto zoo' => array('lat' => 43.8174, 'lng' => -79.1853),
        'ripleys aquarium' => array('lat' => 43.6424, 'lng' => -79.3860),
        'ripley aquarium' => array('lat' => 43.6424, 'lng' => -79.3860),

        // Major malls
        'scarborough town centre' => array('lat' => 43.7764, 'lng' => -79.2578),
        'yorkdale' => array('lat' => 43.7254, 'lng' => -79.4522),
        'yorkdale mall' => array('lat' => 43.7254, 'lng' => -79.4522),
        'square one' => array('lat' => 43.5932, 'lng' => -79.6441),
        'sherway gardens' => array('lat' => 43.6127, 'lng' => -79.5573),
        'fairview mall' => array('lat' => 43.7778, 'lng' => -79.3465),
        'dufferin mall' => array('lat' => 43.6556, 'lng' => -79.4344),
        'woodbine mall' => array('lat' => 43.7200, 'lng' => -79.5557),
        'gerrard square' => array('lat' => 43.6638, 'lng' => -79.3482),
        'pacific mall' => array('lat' => 43.8264, 'lng' => -79.3016),

        // Neighborhoods
        'downtown' => array('lat' => 43.6532, 'lng' => -79.3832),
        'downtown toronto' => array('lat' => 43.6532, 'lng' => -79.3832),
        'the annex' => array('lat' => 43.6716, 'lng' => -79.4050),
        'annex' => array('lat' => 43.6716, 'lng' => -79.4050),
        'yorkville' => array('lat' => 43.6709, 'lng' => -79.3933),
        'liberty village' => array('lat' => 43.6379, 'lng' => -79.4215),
        'leslieville' => array('lat' => 43.6621, 'lng' => -79.3312),
        'the beaches' => array('lat' => 43.6677, 'lng' => -79.2930),
        'beaches' => array('lat' => 43.6677, 'lng' => -79.2930),
        'queen west' => array('lat' => 43.6459, 'lng' => -79.4116),
        'king west' => array('lat' => 43.6445, 'lng' => -79.3984),
        'entertainment district' => array('lat' => 43.6461, 'lng' => -79.3890),
        'financial district' => array('lat' => 43.6486, 'lng' => -79.3812),
        'chinatown' => array('lat' => 43.6531, 'lng' => -79.3979),
        'little italy' => array('lat' => 43.6556, 'lng' => -79.4198),
        'greektown' => array('lat' => 43.6801, 'lng' => -79.3383),
        'the danforth' => array('lat' => 43.6801, 'lng' => -79.3383),
        'danforth' => array('lat' => 43.6801, 'lng' => -79.3383),
        'koreatown' => array('lat' => 43.6639, 'lng' => -79.4138),
        'little portugal' => array('lat' => 43.6492, 'lng' => -79.4283),
        'parkdale' => array('lat' => 43.6372, 'lng' => -79.4450),
        'junction' => array('lat' => 43.6648, 'lng' => -79.4668),
        'the junction' => array('lat' => 43.6648, 'lng' => -79.4668),
        'ossington' => array('lat' => 43.6584, 'lng' => -79.4218),
        'bloor west village' => array('lat' => 43.6506, 'lng' => -79.4771),
        'roncevalles' => array('lat' => 43.6478, 'lng' => -79.4518),
        'cabbagetown' => array('lat' => 43.6668, 'lng' => -79.3644),
        'regent park' => array('lat' => 43.6583, 'lng' => -79.3606),
        'moss park' => array('lat' => 43.6564, 'lng' => -79.3659),
        'st james town' => array('lat' => 43.6684, 'lng' => -79.3707),
        'north york' => array('lat' => 43.7615, 'lng' => -79.4111),
        'scarborough' => array('lat' => 43.7731, 'lng' => -79.2577),
        'etobicoke' => array('lat' => 43.6205, 'lng' => -79.5132),
        'east york' => array('lat' => 43.6936, 'lng' => -79.3274),
        'mimico' => array('lat' => 43.6146, 'lng' => -79.4922),
        'midtown' => array('lat' => 43.6966, 'lng' => -79.3969),
        'uptown' => array('lat' => 43.7113, 'lng' => -79.3989),

        // Transit hubs
        'pearson airport' => array('lat' => 43.6777, 'lng' => -79.6248),
        'billy bishop airport' => array('lat' => 43.6275, 'lng' => -79.3962),
        'bus terminal' => array('lat' => 43.6611, 'lng' => -79.3825),

        // Common Toronto postal codes (FSAs) — hardcoded for consistent resolution
        'm5g 2h5' => array('lat' => 43.6545, 'lng' => -79.3867),
        'm5g2h5' => array('lat' => 43.6545, 'lng' => -79.3867),
        'm5g' => array('lat' => 43.6555, 'lng' => -79.3870),
        'm5b' => array('lat' => 43.6555, 'lng' => -79.3775),
        'm5v' => array('lat' => 43.6430, 'lng' => -79.3930),
        'm5h' => array('lat' => 43.6490, 'lng' => -79.3810),
        'm5j' => array('lat' => 43.6440, 'lng' => -79.3770),
        'm5a' => array('lat' => 43.6500, 'lng' => -79.3640),
        'm5t' => array('lat' => 43.6530, 'lng' => -79.3970),
        'm5s' => array('lat' => 43.6600, 'lng' => -79.3950),
        'm5r' => array('lat' => 43.6710, 'lng' => -79.3950),
        'm4w' => array('lat' => 43.6730, 'lng' => -79.3790),
        'm4x' => array('lat' => 43.6660, 'lng' => -79.3660),
        'm4y' => array('lat' => 43.6660, 'lng' => -79.3830),
        'm6g' => array('lat' => 43.6580, 'lng' => -79.4200),
        'm6j' => array('lat' => 43.6460, 'lng' => -79.4200),
        'm6k' => array('lat' => 43.6380, 'lng' => -79.4260),
        'm4m' => array('lat' => 43.6590, 'lng' => -79.3480),
        'm4l' => array('lat' => 43.6630, 'lng' => -79.3200),
        'm4e' => array('lat' => 43.6680, 'lng' => -79.2930),
        'm4k' => array('lat' => 43.6810, 'lng' => -79.3540)
    );
}


// ============================================================
// D. TORONTO INTERSECTION COORDINATES
//    Major streets with approximate lat/lng at key cross-streets
// ============================================================

function nearme_get_intersection_coords() {
    // Major Toronto streets with their base coordinates
    // Intersections are computed by averaging the two streets
    $streets = array(
        'yonge' => array('lat' => 43.6561, 'lng' => -79.3802, 'dir' => 'ns'),
        'bay' => array('lat' => 43.6555, 'lng' => -79.3834, 'dir' => 'ns'),
        'university' => array('lat' => 43.6540, 'lng' => -79.3883, 'dir' => 'ns'),
        'spadina' => array('lat' => 43.6535, 'lng' => -79.3963, 'dir' => 'ns'),
        'bathurst' => array('lat' => 43.6525, 'lng' => -79.4115, 'dir' => 'ns'),
        'ossington' => array('lat' => 43.6500, 'lng' => -79.4218, 'dir' => 'ns'),
        'dufferin' => array('lat' => 43.6495, 'lng' => -79.4344, 'dir' => 'ns'),
        'lansdowne' => array('lat' => 43.6490, 'lng' => -79.4470, 'dir' => 'ns'),
        'jarvis' => array('lat' => 43.6568, 'lng' => -79.3733, 'dir' => 'ns'),
        'church' => array('lat' => 43.6575, 'lng' => -79.3769, 'dir' => 'ns'),
        'parliament' => array('lat' => 43.6565, 'lng' => -79.3641, 'dir' => 'ns'),
        'sherbourne' => array('lat' => 43.6565, 'lng' => -79.3700, 'dir' => 'ns'),
        'broadview' => array('lat' => 43.6630, 'lng' => -79.3518, 'dir' => 'ns'),
        'pape' => array('lat' => 43.6680, 'lng' => -79.3397, 'dir' => 'ns'),
        'coxwell' => array('lat' => 43.6700, 'lng' => -79.3240, 'dir' => 'ns'),
        'woodbine' => array('lat' => 43.6700, 'lng' => -79.3100, 'dir' => 'ns'),
        'victoria park' => array('lat' => 43.6700, 'lng' => -79.2892, 'dir' => 'ns'),
        'warden' => array('lat' => 43.7100, 'lng' => -79.2792, 'dir' => 'ns'),
        'kennedy' => array('lat' => 43.7300, 'lng' => -79.2633, 'dir' => 'ns'),
        'keele' => array('lat' => 43.6650, 'lng' => -79.4600, 'dir' => 'ns'),
        'jane' => array('lat' => 43.6700, 'lng' => -79.4850, 'dir' => 'ns'),

        'bloor' => array('lat' => 43.6677, 'lng' => -79.3870, 'dir' => 'ew'),
        'dundas' => array('lat' => 43.6555, 'lng' => -79.3802, 'dir' => 'ew'),
        'queen' => array('lat' => 43.6520, 'lng' => -79.3802, 'dir' => 'ew'),
        'king' => array('lat' => 43.6490, 'lng' => -79.3802, 'dir' => 'ew'),
        'front' => array('lat' => 43.6454, 'lng' => -79.3802, 'dir' => 'ew'),
        'college' => array('lat' => 43.6600, 'lng' => -79.3958, 'dir' => 'ew'),
        'carlton' => array('lat' => 43.6620, 'lng' => -79.3780, 'dir' => 'ew'),
        'wellesley' => array('lat' => 43.6653, 'lng' => -79.3833, 'dir' => 'ew'),
        'gerrard' => array('lat' => 43.6610, 'lng' => -79.3760, 'dir' => 'ew'),
        'st clair' => array('lat' => 43.6884, 'lng' => -79.4115, 'dir' => 'ew'),
        'eglinton' => array('lat' => 43.7060, 'lng' => -79.3980, 'dir' => 'ew'),
        'lawrence' => array('lat' => 43.7250, 'lng' => -79.3990, 'dir' => 'ew'),
        'sheppard' => array('lat' => 43.7520, 'lng' => -79.3990, 'dir' => 'ew'),
        'finch' => array('lat' => 43.7800, 'lng' => -79.4150, 'dir' => 'ew'),
        'steeles' => array('lat' => 43.7990, 'lng' => -79.4180, 'dir' => 'ew'),
        'danforth' => array('lat' => 43.6801, 'lng' => -79.3383, 'dir' => 'ew'),
        'lakeshore' => array('lat' => 43.6370, 'lng' => -79.3900, 'dir' => 'ew'),
        'lake shore' => array('lat' => 43.6370, 'lng' => -79.3900, 'dir' => 'ew'),
        'adelaide' => array('lat' => 43.6500, 'lng' => -79.3802, 'dir' => 'ew'),
        'richmond' => array('lat' => 43.6510, 'lng' => -79.3802, 'dir' => 'ew'),
        'harbour' => array('lat' => 43.6400, 'lng' => -79.3780, 'dir' => 'ew'),
        'queens quay' => array('lat' => 43.6385, 'lng' => -79.3780, 'dir' => 'ew'),
        'dupont' => array('lat' => 43.6745, 'lng' => -79.4060, 'dir' => 'ew'),
        'davenport' => array('lat' => 43.6720, 'lng' => -79.4000, 'dir' => 'ew')
    );
    return $streets;
}

/**
 * Resolve an intersection string like "Yonge and Dundas" to lat/lng
 * Returns array('lat' => ..., 'lng' => ...) or null
 */
function nearme_resolve_intersection($text) {
    $streets = nearme_get_intersection_coords();
    $text = strtolower(trim($text));

    // Match "X and Y", "X & Y", "X at Y"
    $parts = preg_split('/\s+(?:and|&|at)\s+/', $text);
    if (count($parts) !== 2) return null;

    $street1 = trim($parts[0]);
    $street2 = trim($parts[1]);

    // Remove common suffixes
    $suffixes = array(' street', ' st', ' ave', ' avenue', ' rd', ' road', ' blvd', ' boulevard', ' dr', ' drive');
    foreach ($suffixes as $suf) {
        $street1 = str_replace($suf, '', $street1);
        $street2 = str_replace($suf, '', $street2);
    }
    $street1 = trim($street1);
    $street2 = trim($street2);

    $s1 = isset($streets[$street1]) ? $streets[$street1] : null;
    $s2 = isset($streets[$street2]) ? $streets[$street2] : null;

    if ($s1 === null || $s2 === null) return null;

    // For intersection: use NS street's lng, EW street's lat
    if ($s1['dir'] === 'ns' && $s2['dir'] === 'ew') {
        return array('lat' => $s2['lat'], 'lng' => $s1['lng']);
    }
    if ($s1['dir'] === 'ew' && $s2['dir'] === 'ns') {
        return array('lat' => $s1['lat'], 'lng' => $s2['lng']);
    }

    // Same direction: just average
    return array(
        'lat' => ($s1['lat'] + $s2['lat']) / 2,
        'lng' => ($s1['lng'] + $s2['lng']) / 2
    );
}


// ============================================================
// E. CRISIS RESOURCES DATABASE
// ============================================================

function nearme_get_crisis_resources() {
    return array(
        array(
            'name' => 'Emergency Services',
            'phone' => '911',
            'hours' => '24/7',
            'type' => 'Emergency',
            'address' => '',
            'maps_url' => ''
        ),
        array(
            'name' => 'City of Toronto Central Intake (Shelter)',
            'phone' => '416-338-4766',
            'hours' => '24/7',
            'type' => 'Shelter Intake',
            'address' => '129 Peter St, Toronto, ON',
            'maps_url' => 'https://www.google.com/maps/search/?api=1&query=129+Peter+St+Toronto+ON'
        ),
        array(
            'name' => 'Toronto 311 (City Services)',
            'phone' => '311',
            'hours' => '24/7',
            'type' => 'City Services',
            'address' => '',
            'maps_url' => ''
        ),
        array(
            'name' => 'Gerstein Crisis Centre',
            'phone' => '416-929-5200',
            'hours' => '24/7',
            'type' => 'Mental Health Crisis',
            'address' => '100 Charles St E, Toronto, ON',
            'maps_url' => 'https://www.google.com/maps/search/?api=1&query=100+Charles+St+E+Toronto+ON'
        ),
        array(
            'name' => 'Toronto Distress Centres',
            'phone' => '416-408-4357',
            'hours' => '24/7',
            'type' => 'Distress Line',
            'address' => '',
            'maps_url' => ''
        ),
        array(
            'name' => 'Assaulted Women\'s Helpline',
            'phone' => '416-863-0511',
            'hours' => '24/7',
            'type' => 'Domestic Violence',
            'address' => '',
            'maps_url' => ''
        ),
        array(
            'name' => 'Kids Help Phone',
            'phone' => '1-800-668-6868',
            'hours' => '24/7',
            'type' => 'Youth Crisis',
            'address' => '',
            'maps_url' => ''
        ),
        array(
            'name' => 'Covenant House Toronto',
            'phone' => '416-598-4898',
            'hours' => '24/7',
            'type' => 'Youth Shelter',
            'address' => '20 Gerrard St E, Toronto, ON',
            'maps_url' => 'https://www.google.com/maps/search/?api=1&query=20+Gerrard+St+E+Toronto+ON'
        ),
        array(
            'name' => 'Good Shepherd Ministries',
            'phone' => '416-869-3619',
            'hours' => '24/7',
            'type' => 'Men\'s Shelter',
            'address' => '412 Queen St E, Toronto, ON',
            'maps_url' => 'https://www.google.com/maps/search/?api=1&query=412+Queen+St+E+Toronto+ON'
        ),
        array(
            'name' => 'Fred Victor Centre',
            'phone' => '416-364-8228',
            'hours' => 'Various',
            'type' => 'Shelter/Services',
            'address' => '145 Queen St E, Toronto, ON',
            'maps_url' => 'https://www.google.com/maps/search/?api=1&query=145+Queen+St+E+Toronto+ON'
        ),
        array(
            'name' => 'Talk Suicide Canada',
            'phone' => '1-833-456-4566',
            'hours' => '24/7',
            'type' => 'Suicide Prevention',
            'address' => '',
            'maps_url' => ''
        ),
        array(
            'name' => 'ConnexOntario (Addiction/Mental Health)',
            'phone' => '1-866-531-2600',
            'hours' => '24/7',
            'type' => 'Addiction/Mental Health',
            'address' => '',
            'maps_url' => ''
        )
    );
}

/** Check if a query matches crisis keywords */
function nearme_is_crisis_query($query) {
    $crisis_keywords = array(
        'homeless shelter', 'shelter', 'shelters', 'warming centre', 'warming center',
        'crisis', 'crisis help', 'crisis line', 'crisis centre', 'crisis center',
        'suicide', 'suicidal', 'self harm', 'self-harm',
        'abuse', 'abused', 'domestic violence', 'assault', 'assaulted',
        'distress', 'mental health crisis',
        'emergency shelter', 'food bank', 'food banks',
        'drop in centre', 'drop in center', 'drop-in'
    );
    $q = strtolower(trim($query));
    foreach ($crisis_keywords as $kw) {
        if (strpos($q, $kw) !== false) {
            return true;
        }
    }
    return false;
}


// ============================================================
// F. DELIVERY SERVICE SUGGESTIONS
// ============================================================

function nearme_get_delivery_tip($group) {
    if ($group === 'food') {
        return 'Also check Uber Eats, DoorDash, or SkipTheDishes for delivery options.';
    }
    if ($group === 'retail') {
        return 'Check Uber Eats, Instacart, or the store website for delivery options.';
    }
    if ($group === 'pharmacy') {
        return 'Many pharmacies offer delivery -- call to confirm or check their app.';
    }
    return '';
}


// ============================================================
// G. HELPER: look up category info for a query string
// ============================================================

function nearme_lookup_category($query) {
    $map = nearme_get_category_map();
    $q = strtolower(trim($query));

    // Direct match
    if (isset($map[$q])) {
        return $map[$q];
    }

    // Try without trailing 's' (simple depluralize)
    $qs = rtrim($q, 's');
    if ($qs !== $q && isset($map[$qs])) {
        return $map[$qs];
    }

    // Partial match: check if any key is contained in the query
    $best_match = null;
    $best_len = 0;
    foreach ($map as $key => $val) {
        if (strpos($q, $key) !== false && strlen($key) > $best_len) {
            $best_match = $val;
            $best_len = strlen($key);
        }
    }
    if ($best_match !== null) {
        return $best_match;
    }

    // No match: return generic with the original query
    return array('query' => $q, 'categories' => '', 'group' => 'other');
}


// ============================================================
// H. OSM TAG MAPPINGS (for Overpass API provider)
//    Maps search terms to OpenStreetMap amenity/shop/cuisine tags
// ============================================================

function nearme_get_osm_tags() {
    return array(
        // --- Coffee & Tea ---
        'coffee' => array('amenity' => 'cafe', 'extra' => ''),
        'coffee shop' => array('amenity' => 'cafe', 'extra' => ''),
        'coffee shops' => array('amenity' => 'cafe', 'extra' => ''),
        'cafe' => array('amenity' => 'cafe', 'extra' => ''),
        'cafes' => array('amenity' => 'cafe', 'extra' => ''),
        'tea' => array('amenity' => 'cafe', 'extra' => '"cuisine"~"tea"'),
        'bubble tea' => array('amenity' => 'cafe', 'extra' => '"cuisine"~"bubble_tea"'),
        'boba' => array('amenity' => 'cafe', 'extra' => '"cuisine"~"bubble_tea"'),

        // --- Restaurants ---
        'restaurant' => array('amenity' => 'restaurant', 'extra' => ''),
        'restaurants' => array('amenity' => 'restaurant', 'extra' => ''),
        'chinese restaurant' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"chinese"'),
        'chinese food' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"chinese"'),
        'indian restaurant' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"indian"'),
        'indian food' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"indian"'),
        'italian restaurant' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"italian"'),
        'italian food' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"italian"'),
        'mexican restaurant' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"mexican"'),
        'mexican food' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"mexican"'),
        'thai restaurant' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"thai"'),
        'thai food' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"thai"'),
        'japanese restaurant' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"japanese"'),
        'japanese food' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"japanese"'),
        'korean restaurant' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"korean"'),
        'korean food' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"korean"'),
        'vietnamese restaurant' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"vietnamese"'),
        'greek restaurant' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"greek"'),
        'caribbean restaurant' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"caribbean"'),
        'french restaurant' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"french"'),
        'turkish restaurant' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"turkish"'),
        'lebanese restaurant' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"lebanese"'),
        'mediterranean restaurant' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"mediterranean"'),

        // --- Specific food types ---
        'pizza' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"pizza"'),
        'pizza place' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"pizza"'),
        'sushi' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"sushi"'),
        'ramen' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"ramen"'),
        'burger' => array('amenity' => 'fast_food', 'extra' => '"cuisine"~"burger"'),
        'burgers' => array('amenity' => 'fast_food', 'extra' => '"cuisine"~"burger"'),
        'sandwich' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"sandwich"'),
        'sandwiches' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"sandwich"'),
        'deli' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"deli"'),
        'seafood' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"seafood"'),
        'steak' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"steak"'),
        'steakhouse' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"steak"'),
        'bbq' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"bbq"'),
        'kebab' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"kebab"'),
        'shawarma' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"kebab|shawarma"'),
        'falafel' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"falafel|middle_eastern"'),
        'poutine' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"poutine|canadian"'),
        'tacos' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"mexican|taco"'),
        'pho' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"vietnamese|pho"'),
        'dim sum' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"chinese|dim_sum"'),
        'curry' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"indian|curry"'),

        // --- Fast food ---
        'fast food' => array('amenity' => 'fast_food', 'extra' => ''),
        'mcdonalds' => array('amenity' => 'fast_food', 'extra' => '"name"~"McDonald",i'),
        'tim hortons' => array('amenity' => 'cafe', 'extra' => '"name"~"Tim Horton",i'),
        'starbucks' => array('amenity' => 'cafe', 'extra' => '"name"~"Starbucks",i'),
        'subway' => array('amenity' => 'fast_food', 'extra' => '"name"~"Subway",i'),

        // --- Bakery & Dessert ---
        'bakery' => array('amenity' => '', 'extra' => '"shop"="bakery"'),
        'donut' => array('amenity' => '', 'extra' => '"shop"="bakery"'),
        'donuts' => array('amenity' => '', 'extra' => '"shop"="bakery"'),
        'ice cream' => array('amenity' => 'ice_cream', 'extra' => ''),
        'dessert' => array('amenity' => 'ice_cream', 'extra' => ''),

        // --- Bars & Nightlife ---
        'bar' => array('amenity' => 'bar', 'extra' => ''),
        'bars' => array('amenity' => 'bar', 'extra' => ''),
        'pub' => array('amenity' => 'pub', 'extra' => ''),
        'pubs' => array('amenity' => 'pub', 'extra' => ''),
        'nightclub' => array('amenity' => 'nightclub', 'extra' => ''),

        // --- Brunch & Meals ---
        'brunch' => array('amenity' => 'restaurant', 'extra' => ''),
        'breakfast' => array('amenity' => 'restaurant', 'extra' => ''),

        // --- Services ---
        'gas station' => array('amenity' => 'fuel', 'extra' => ''),
        'gas' => array('amenity' => 'fuel', 'extra' => ''),
        'pharmacy' => array('amenity' => 'pharmacy', 'extra' => ''),
        'drug store' => array('amenity' => 'pharmacy', 'extra' => ''),
        'bank' => array('amenity' => 'bank', 'extra' => ''),
        'atm' => array('amenity' => 'atm', 'extra' => ''),
        'post office' => array('amenity' => 'post_office', 'extra' => ''),
        'laundromat' => array('amenity' => '', 'extra' => '"shop"="laundry"'),
        'laundry' => array('amenity' => '', 'extra' => '"shop"="laundry"'),
        'car wash' => array('amenity' => 'car_wash', 'extra' => ''),
        'hair salon' => array('amenity' => '', 'extra' => '"shop"="hairdresser"'),
        'barber' => array('amenity' => '', 'extra' => '"shop"="hairdresser"'),

        // --- Facilities ---
        'washroom' => array('amenity' => 'toilets', 'extra' => ''),
        'restroom' => array('amenity' => 'toilets', 'extra' => ''),
        'bathroom' => array('amenity' => 'toilets', 'extra' => ''),
        'parking' => array('amenity' => 'parking', 'extra' => ''),

        // --- Healthcare ---
        'hospital' => array('amenity' => 'hospital', 'extra' => ''),
        'clinic' => array('amenity' => 'clinic', 'extra' => ''),
        'walk in clinic' => array('amenity' => 'clinic', 'extra' => ''),
        'walk-in clinic' => array('amenity' => 'clinic', 'extra' => ''),
        'dentist' => array('amenity' => 'dentist', 'extra' => ''),
        'doctor' => array('amenity' => 'doctors', 'extra' => ''),
        'vet' => array('amenity' => 'veterinary', 'extra' => ''),
        'veterinarian' => array('amenity' => 'veterinary', 'extra' => ''),

        // --- Shopping ---
        'grocery store' => array('amenity' => '', 'extra' => '"shop"="supermarket"'),
        'grocery' => array('amenity' => '', 'extra' => '"shop"="supermarket"'),
        'supermarket' => array('amenity' => '', 'extra' => '"shop"="supermarket"'),
        'convenience store' => array('amenity' => '', 'extra' => '"shop"="convenience"'),
        'bookstore' => array('amenity' => '', 'extra' => '"shop"="books"'),
        'clothing store' => array('amenity' => '', 'extra' => '"shop"="clothes"'),
        'electronics store' => array('amenity' => '', 'extra' => '"shop"="electronics"'),
        'hardware store' => array('amenity' => '', 'extra' => '"shop"="hardware"'),
        'liquor store' => array('amenity' => '', 'extra' => '"shop"="alcohol"'),
        'pet store' => array('amenity' => '', 'extra' => '"shop"="pet"'),

        // --- Entertainment ---
        'gym' => array('amenity' => '', 'extra' => '"leisure"="fitness_centre"'),
        'fitness' => array('amenity' => '', 'extra' => '"leisure"="fitness_centre"'),
        'park' => array('amenity' => '', 'extra' => '"leisure"="park"'),
        'museum' => array('amenity' => '', 'extra' => '"tourism"="museum"'),
        'cinema' => array('amenity' => 'cinema', 'extra' => ''),
        'movie theater' => array('amenity' => 'cinema', 'extra' => ''),
        'movie theatre' => array('amenity' => 'cinema', 'extra' => ''),
        'library' => array('amenity' => 'library', 'extra' => ''),

        // --- Accommodation ---
        'hotel' => array('amenity' => '', 'extra' => '"tourism"="hotel"'),
        'hostel' => array('amenity' => '', 'extra' => '"tourism"="hostel"'),

        // --- Transit ---
        'subway station' => array('amenity' => '', 'extra' => '"railway"="station"'),
        'bus stop' => array('amenity' => '', 'extra' => '"highway"="bus_stop"'),
        'ev charger' => array('amenity' => 'charging_station', 'extra' => ''),
        'ev charging' => array('amenity' => 'charging_station', 'extra' => ''),

        // --- Community ---
        'church' => array('amenity' => 'place_of_worship', 'extra' => '"religion"="christian"'),
        'mosque' => array('amenity' => 'place_of_worship', 'extra' => '"religion"="muslim"'),
        'temple' => array('amenity' => 'place_of_worship', 'extra' => ''),
        'synagogue' => array('amenity' => 'place_of_worship', 'extra' => '"religion"="jewish"'),
        'school' => array('amenity' => 'school', 'extra' => ''),
        'police station' => array('amenity' => 'police', 'extra' => ''),
        'fire station' => array('amenity' => 'fire_station', 'extra' => '')
    );
}
