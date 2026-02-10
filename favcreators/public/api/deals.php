<?php
/**
 * Deals & Freebies API for findtorontoevents.ca
 *
 * Actions:
 *   ?action=birthday       — Birthday freebies (all categories)
 *   ?action=free_today      — Free things available today
 *   ?action=calendar        — Weekly calendar of free things
 *   ?action=canadian_deals  — Current Canadian deals/coupons/samples
 *   ?action=all             — Everything
 *   ?action=search&q=...    — Search across all deals
 *
 * Filters (apply to all actions):
 *   &category=food|beauty|retail|entertainment|kids|bubble_tea|coffee|dessert|bakery|mexican|pets|wellness|digital|samples
 *   &type=free|purchase_required|discount|bogo
 *   &near=lat,lng           — Sort by distance (for deals with locations)
 */

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

// ── Cache ──
$cache_dir = dirname(__FILE__) . '/cache';
if (!is_dir($cache_dir)) { @mkdir($cache_dir, 0755, true); }

$action = isset($_GET['action']) ? $_GET['action'] : 'all';
$category = isset($_GET['category']) ? strtolower($_GET['category']) : '';
$type_filter = isset($_GET['type']) ? strtolower($_GET['type']) : '';
$search_q = isset($_GET['q']) ? strtolower(trim($_GET['q'])) : '';
$near = isset($_GET['near']) ? $_GET['near'] : '';

// ── Sort comparison (PHP 5.2 compatible - no anonymous functions) ──
function _deals_cmp_distance($a, $b) {
    return $a['distance_m'] - $b['distance_m'];
}

// ── Haversine distance ──
function _deals_haversine($lat1, $lon1, $lat2, $lon2) {
    $R = 6371000;
    $dLat = deg2rad($lat2 - $lat1);
    $dLon = deg2rad($lon2 - $lon1);
    $a = sin($dLat/2)*sin($dLat/2) + cos(deg2rad($lat1))*cos(deg2rad($lat2))*sin($dLon/2)*sin($dLon/2);
    return $R * 2 * atan2(sqrt($a), sqrt(1-$a));
}

// ── Birthday Freebies Data ──
function _get_birthday_deals() {
    return array(
        // ── RESTAURANTS — Full Meals ──
        array('id'=>'b1','name'=>'Denny\'s','freebie'=>'Free Build Your Own Grand Slam breakfast','category'=>'food','subcategory'=>'restaurant','type'=>'free','value_est'=>14,'conditions'=>'Show valid photo ID on your actual birthday. No signup needed.','signup_days_before'=>0,'redemption_window'=>'Birthday day only','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>4,'lat'=>43.6735,'lng'=>-79.5888),
        array('id'=>'b2','name'=>'Mandarin Restaurant','freebie'=>'Free buffet meal during birthday week','category'=>'food','subcategory'=>'restaurant','type'=>'free','value_est'=>35,'conditions'=>'Must bring 3 paying adults. Sign up for Mandarin Dish newsletter in advance.','signup_days_before'=>14,'redemption_window'=>'Birthday week','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>3,'lat'=>43.7701,'lng'=>-79.4103),
        array('id'=>'b3','name'=>'The Works Burger','freebie'=>'Free burger coupon','category'=>'food','subcategory'=>'restaurant','type'=>'free','value_est'=>16,'conditions'=>'Sign up for Burgers With Benefits club at least 9 days before birthday.','signup_days_before'=>9,'redemption_window'=>'Birthday week','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>2),
        array('id'=>'b4','name'=>'Perkins American Food Co.','freebie'=>'Free Magnificent Seven breakfast','category'=>'food','subcategory'=>'restaurant','type'=>'free','value_est'=>16,'conditions'=>'Sign up for newsletter. GTA locations only.','signup_days_before'=>7,'redemption_window'=>'Birthday week','source_url'=>'https://www.thebirthdayfreebies.ca/offers/totally-free','sources_verified'=>2),
        array('id'=>'b5','name'=>'Copa Cabana','freebie'=>'Complimentary birthday rodizio meal','category'=>'food','subcategory'=>'restaurant','type'=>'free','value_est'=>35,'conditions'=>'Toronto, Niagara Falls, Vaughan locations.','signup_days_before'=>0,'redemption_window'=>'Birthday day','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>1),
        array('id'=>'b6','name'=>'Wok of Fame','freebie'=>'Free buffet meal','category'=>'food','subcategory'=>'restaurant','type'=>'free','value_est'=>28,'conditions'=>'Must bring 3 paying guests (age 5+). Show ID.','signup_days_before'=>0,'redemption_window'=>'Birthday day','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>1),
        array('id'=>'b7','name'=>'LOCAL Public Eatery','freebie'=>'Free birthday meal','category'=>'food','subcategory'=>'restaurant','type'=>'free','value_est'=>20,'conditions'=>'Sign up for LPE League Rewards. Make a reservation.','signup_days_before'=>7,'redemption_window'=>'Birthday day','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>1),
        array('id'=>'b8','name'=>'Tracie\'s Restaurant & Karaoke','freebie'=>'Free meal — NO signup required','category'=>'food','subcategory'=>'restaurant','type'=>'free','value_est'=>18,'conditions'=>'Show up on your birthday. No signup needed.','signup_days_before'=>0,'redemption_window'=>'Birthday day only','source_url'=>'https://www.thebirthdayfreebies.ca/offers/totally-free','sources_verified'=>1),

        // ── RESTAURANTS — Desserts / Sides with purchase ──
        array('id'=>'b9','name'=>'The Keg Steakhouse','freebie'=>'Free Billy Miner Pie','category'=>'food','subcategory'=>'restaurant','type'=>'purchase_required','value_est'=>12,'conditions'=>'Must purchase a meal. Tell your server. No signup needed.','signup_days_before'=>0,'redemption_window'=>'Birthday day','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>3,'lat'=>43.6507,'lng'=>-79.3746),
        array('id'=>'b10','name'=>'Boston Pizza','freebie'=>'Free dessert on birthday + free starter at signup','category'=>'food','subcategory'=>'restaurant','type'=>'free','value_est'=>10,'conditions'=>'Sign up for MyBP. Dine-in only. ~60 days to redeem.','signup_days_before'=>7,'redemption_window'=>'Birthday month','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>4),
        array('id'=>'b11','name'=>'Montana\'s BBQ','freebie'=>'Free dessert + 10% off meal. Kids 12 & under: free birthday kids meal.','category'=>'food','subcategory'=>'restaurant','type'=>'purchase_required','value_est'=>10,'conditions'=>'Sign up for Grill Lover\'s Club. Minimum $30 purchase.','signup_days_before'=>7,'redemption_window'=>'Birthday week','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>3),
        array('id'=>'b12','name'=>'Swiss Chalet','freebie'=>'Free dessert or appetizer coupon','category'=>'food','subcategory'=>'restaurant','type'=>'free','value_est'=>8,'conditions'=>'Subscribe to Rotisserie Mail newsletter.','signup_days_before'=>7,'redemption_window'=>'Birthday week','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>3),
        array('id'=>'b13','name'=>'Harvey\'s','freebie'=>'Free slice of pie (with burger purchase)','category'=>'food','subcategory'=>'fast_food','type'=>'purchase_required','value_est'=>5,'conditions'=>'Sign up for Burger Boss Club newsletter. ~14 days to redeem.','signup_days_before'=>7,'redemption_window'=>'14 days','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>5),
        array('id'=>'b14','name'=>'Kelseys','freebie'=>'Free birthday dessert','category'=>'food','subcategory'=>'restaurant','type'=>'purchase_required','value_est'=>8,'conditions'=>'Must purchase a meal. Sign up for newsletter.','signup_days_before'=>7,'redemption_window'=>'Birthday week','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>2),
        array('id'=>'b15','name'=>'Red Lobster','freebie'=>'Surprise birthday offer (appetizer or dessert)','category'=>'food','subcategory'=>'restaurant','type'=>'free','value_est'=>10,'conditions'=>'Sign up for Fresh Catch News at least 10 days before birthday.','signup_days_before'=>10,'redemption_window'=>'Birthday week','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>3),

        // ── FAST FOOD & QUICK SERVICE ──
        array('id'=>'b16','name'=>'Jersey Mike\'s Subs','freebie'=>'Free regular sub and 16oz soft drink','category'=>'food','subcategory'=>'fast_food','type'=>'free','value_est'=>15,'conditions'=>'Sign up for Email Club at least 8 days before birthday.','signup_days_before'=>8,'redemption_window'=>'7 days','source_url'=>'https://curiocity.com/toronto-birthday-freebies-free-gifts/','sources_verified'=>3),
        array('id'=>'b17','name'=>'Firehouse Subs','freebie'=>'Free medium sub','category'=>'food','subcategory'=>'fast_food','type'=>'free','value_est'=>12,'conditions'=>'Sign up for Firehouse Rewards.','signup_days_before'=>7,'redemption_window'=>'Birthday day','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>1),
        array('id'=>'b18','name'=>'Mr. Sub','freebie'=>'Free small classic sub','category'=>'food','subcategory'=>'fast_food','type'=>'free','value_est'=>8,'conditions'=>'Join Mr. Sub Rewards. ~30 days to redeem.','signup_days_before'=>7,'redemption_window'=>'30 days','source_url'=>'https://www.overheretoronto.com/best-birthday-freebies-in-toronto/','sources_verified'=>2),
        array('id'=>'b19','name'=>'South St. Burger','freebie'=>'BOGO free burger','category'=>'food','subcategory'=>'fast_food','type'=>'bogo','value_est'=>14,'conditions'=>'Join Birthday Club at least 72 hours before birthday.','signup_days_before'=>3,'redemption_window'=>'Birthday day','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>2),
        array('id'=>'b20','name'=>'Burger\'s Priest','freebie'=>'Free milkshake + free cheeseburger at signup','category'=>'food','subcategory'=>'fast_food','type'=>'free','value_est'=>12,'conditions'=>'Download app / join The Priest\'s Congregation.','signup_days_before'=>1,'redemption_window'=>'Birthday day','source_url'=>'https://www.overheretoronto.com/best-birthday-freebies-in-toronto/','sources_verified'=>3),
        array('id'=>'b21','name'=>'Chick-fil-A','freebie'=>'Free cookie/brownie (base tier), milkshake (silver), entree (signature)','category'=>'food','subcategory'=>'fast_food','type'=>'free','value_est'=>6,'conditions'=>'Sign up for app loyalty program.','signup_days_before'=>7,'redemption_window'=>'Birthday day','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>2),
        array('id'=>'b22','name'=>'Subway','freebie'=>'Free cookie','category'=>'food','subcategory'=>'fast_food','type'=>'free','value_est'=>2,'conditions'=>'Join MVP Rewards.','signup_days_before'=>7,'redemption_window'=>'Birthday day','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>2),
        array('id'=>'b23','name'=>'Score Pizza','freebie'=>'Free pizza','category'=>'food','subcategory'=>'fast_food','type'=>'free','value_est'=>12,'conditions'=>'Join loyalty program.','signup_days_before'=>7,'redemption_window'=>'Birthday day','source_url'=>'https://www.thebirthdayfreebies.ca/offers/totally-free','sources_verified'=>1),
        array('id'=>'b24','name'=>'Chopped Leaf','freebie'=>'Free salad or bowl','category'=>'food','subcategory'=>'fast_food','type'=>'free','value_est'=>12,'conditions'=>'Download Feel Good Rewards app.','signup_days_before'=>7,'redemption_window'=>'Birthday day','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>1),
        array('id'=>'b25','name'=>'Freshii','freebie'=>'Free bowl','category'=>'food','subcategory'=>'fast_food','type'=>'free','value_est'=>12,'conditions'=>'Download app, become ViiP.','signup_days_before'=>7,'redemption_window'=>'Birthday day','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>2),
        array('id'=>'b26','name'=>'KFC','freebie'=>'Free popcorn chicken coupon','category'=>'food','subcategory'=>'fast_food','type'=>'free','value_est'=>5,'conditions'=>'Must have the KFC app.','signup_days_before'=>7,'redemption_window'=>'30 days','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>1),
        array('id'=>'b27','name'=>'New York Fries','freebie'=>'Free regular fries','category'=>'food','subcategory'=>'fast_food','type'=>'free','value_est'=>6,'conditions'=>'Join NYF Fry Society. Must have spent $50 in prior year.','signup_days_before'=>7,'redemption_window'=>'Birthday day','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>2),
        array('id'=>'b28','name'=>'Panera Bread','freebie'=>'Free pastry or baked good','category'=>'food','subcategory'=>'fast_food','type'=>'free','value_est'=>5,'conditions'=>'Sign up for MyPanera Rewards.','signup_days_before'=>7,'redemption_window'=>'Birthday day','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>3),
        array('id'=>'b29','name'=>'Jollibee','freebie'=>'Free birthday pie','category'=>'food','subcategory'=>'fast_food','type'=>'free','value_est'=>5,'conditions'=>'Sign up for Jollibee Rewards. ~30 days to redeem.','signup_days_before'=>7,'redemption_window'=>'30 days','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>2),

        // ── BUBBLE TEA ──
        array('id'=>'b30','name'=>'The Alley','freebie'=>'Free bubble tea','category'=>'bubble_tea','type'=>'free','value_est'=>7,'conditions'=>'Download The Alley app. Must have made 1 purchase in past year.','signup_days_before'=>7,'redemption_window'=>'5 days','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>3),
        array('id'=>'b31','name'=>'Chatime','freebie'=>'Free bubble tea / milk tea drink','category'=>'bubble_tea','type'=>'free','value_est'=>7,'conditions'=>'Join Chatime Socitea rewards. Register birthday at least 7 days before.','signup_days_before'=>7,'redemption_window'=>'14 days','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>4),
        array('id'=>'b32','name'=>'Gong Cha','freebie'=>'Birthday drink','category'=>'bubble_tea','type'=>'free','value_est'=>6,'conditions'=>'Join rewards program.','signup_days_before'=>7,'redemption_window'=>'Birthday day','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>1),
        array('id'=>'b33','name'=>'Ten Ren\'s Tea','freebie'=>'Free birthday drink','category'=>'bubble_tea','type'=>'free','value_est'=>6,'conditions'=>'Become Rewards Program member.','signup_days_before'=>7,'redemption_window'=>'Birthday day','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>2),
        array('id'=>'b34','name'=>'TP Tea','freebie'=>'Free regular-sized drink within a week of birthday','category'=>'bubble_tea','type'=>'free','value_est'=>6,'conditions'=>'Sign up for TP Tea rewards.','signup_days_before'=>7,'redemption_window'=>'7 days','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>1),

        // ── COFFEE, TEA & SMOOTHIES ──
        array('id'=>'b35','name'=>'Starbucks','freebie'=>'Free handcrafted beverage of any size — any drink on the menu','category'=>'coffee','type'=>'free','value_est'=>8,'conditions'=>'Must be Starbucks Rewards member. At least 1 star-earning purchase recently.','signup_days_before'=>7,'redemption_window'=>'Birthday day','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>4),
        array('id'=>'b36','name'=>'Tim Hortons','freebie'=>'Free reward — choice of drink, sandwich, donut, cookie, or muffin','category'=>'coffee','type'=>'free','value_est'=>5,'conditions'=>'Join Tims Rewards at least a week before birthday.','signup_days_before'=>7,'redemption_window'=>'Birthday day','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>4),
        array('id'=>'b37','name'=>'Booster Juice','freebie'=>'Free regular size smoothie','category'=>'coffee','type'=>'free','value_est'=>7,'conditions'=>'Booster Rewards member. Signup min 7 days before birthday.','signup_days_before'=>7,'redemption_window'=>'Birthday day','source_url'=>'https://www.overheretoronto.com/best-birthday-freebies-in-toronto/','sources_verified'=>2),
        array('id'=>'b38','name'=>'Jugo Juice','freebie'=>'Free large smoothie','category'=>'coffee','type'=>'free','value_est'=>8,'conditions'=>'Register for Jugo Juice Rewards. ~7 days to redeem.','signup_days_before'=>7,'redemption_window'=>'7 days','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>2),
        array('id'=>'b39','name'=>'Good Earth Coffeehouse','freebie'=>'Free drink or food item of your choice','category'=>'coffee','type'=>'free','value_est'=>6,'conditions'=>'Join rewards program. ~7 days to redeem.','signup_days_before'=>7,'redemption_window'=>'7 days','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>2),
        array('id'=>'b40','name'=>'7-Eleven','freebie'=>'Free small Slurpee during birthday month','category'=>'coffee','type'=>'free','value_est'=>3,'conditions'=>'Sign up for 7-Eleven Rewards app.','signup_days_before'=>7,'redemption_window'=>'Birthday month','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>2),

        // ── BAKERIES & BAGELS ──
        array('id'=>'b41','name'=>'Kettleman\'s Bagel','freebie'=>'Free dozen bagels','category'=>'bakery','type'=>'free','value_est'=>14,'conditions'=>'Download app. Must sign up at least 30 days before birthday. ~2 days to redeem.','signup_days_before'=>30,'redemption_window'=>'2 days','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>3),
        array('id'=>'b42','name'=>'What A Bagel','freebie'=>'Buy 6 get 6 free bagels','category'=>'bakery','type'=>'bogo','value_est'=>8,'conditions'=>'Show valid photo ID on birthday. No signup needed.','signup_days_before'=>0,'redemption_window'=>'Birthday day','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>2),
        array('id'=>'b43','name'=>'COBS Bread','freebie'=>'Free birthday cinnamon bun + free scone on half-birthday','category'=>'bakery','type'=>'free','value_est'=>5,'conditions'=>'Sign up for COBS Club at least 7 days before. ~15 days to redeem.','signup_days_before'=>7,'redemption_window'=>'15 days','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>2),
        array('id'=>'b44','name'=>'Nothing Bundt Cakes','freebie'=>'Free Bundtlet (personal-size bundt cake)','category'=>'bakery','type'=>'free','value_est'=>6,'conditions'=>'Join ECLUB / Bundtastic Rewards. ~15 days to redeem.','signup_days_before'=>7,'redemption_window'=>'15 days','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>2),
        array('id'=>'b45','name'=>'Paris Baguette','freebie'=>'Free slice of cake during birthday week','category'=>'bakery','type'=>'free','value_est'=>6,'conditions'=>'Join PB Rewards.','signup_days_before'=>7,'redemption_window'=>'Birthday week','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>1),

        // ── ICE CREAM & DESSERTS ──
        array('id'=>'b46','name'=>'iHalo Krunch','freebie'=>'Free ice cream cone — NO signup required','category'=>'dessert','type'=>'free','value_est'=>7,'conditions'=>'Show ID on birthday. No signup needed.','signup_days_before'=>0,'redemption_window'=>'Birthday day only','source_url'=>'https://www.overheretoronto.com/best-birthday-freebies-in-toronto/','sources_verified'=>4),
        array('id'=>'b47','name'=>'Krispy Kreme','freebie'=>'Free donut — NO purchase, NO signup required','category'=>'dessert','type'=>'free','value_est'=>3,'conditions'=>'Show ID in-store on birthday.','signup_days_before'=>0,'redemption_window'=>'Birthday day','source_url'=>'https://www.thebirthdayfreebies.ca/offers/totally-free','sources_verified'=>1),
        array('id'=>'b48','name'=>'Marble Slab Creamery','freebie'=>'Free regular-sized ice cream','category'=>'dessert','type'=>'free','value_est'=>6,'conditions'=>'Sign up for Marble Mail at least 48 hours before birthday.','signup_days_before'=>2,'redemption_window'=>'Birthday week','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>5),
        array('id'=>'b49','name'=>'Baskin-Robbins','freebie'=>'Free scoop of ice cream','category'=>'dessert','type'=>'free','value_est'=>5,'conditions'=>'Join Club 31.','signup_days_before'=>7,'redemption_window'=>'Birthday day','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>3),
        array('id'=>'b50','name'=>'Dairy Queen','freebie'=>'BOGO Blizzard','category'=>'dessert','type'=>'bogo','value_est'=>6,'conditions'=>'Join DQ Rewards.','signup_days_before'=>7,'redemption_window'=>'Birthday day','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>4),
        array('id'=>'b51','name'=>'Menchie\'s Frozen Yogurt','freebie'=>'$5 Menchie Money coupon','category'=>'dessert','type'=>'free','value_est'=>5,'conditions'=>'Download app, create My Smileage account.','signup_days_before'=>7,'redemption_window'=>'Birthday week','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>3),
        array('id'=>'b52','name'=>'Chocolats Favoris','freebie'=>'Free small dipped ice cream cone — NO signup required','category'=>'dessert','type'=>'free','value_est'=>6,'conditions'=>'Redeem on birthday only.','signup_days_before'=>0,'redemption_window'=>'Birthday day only','source_url'=>'https://www.thebirthdayfreebies.ca/offers/totally-free','sources_verified'=>1),
        array('id'=>'b53','name'=>'Crumbl Cookies','freebie'=>'Free Single Cookie voucher','category'=>'dessert','type'=>'free','value_est'=>5,'conditions'=>'Must reach Silver tier of Rewards program. The Well location.','signup_days_before'=>7,'redemption_window'=>'Birthday week','source_url'=>'https://www.overheretoronto.com/best-birthday-freebies-in-toronto/','sources_verified'=>3,'lat'=>43.6421,'lng'=>-79.4013),
        array('id'=>'b54','name'=>'Cinnabon','freebie'=>'Free Minibon + 16oz cold brew','category'=>'dessert','type'=>'free','value_est'=>7,'conditions'=>'Join Cinnabon Email Club / Rewards.','signup_days_before'=>7,'redemption_window'=>'Birthday week','source_url'=>'https://www.overheretoronto.com/best-birthday-freebies-in-toronto/','sources_verified'=>2),
        array('id'=>'b55','name'=>'Lindt Chocolate Shops','freebie'=>'Free Lindor bag / chocolate treat voucher','category'=>'dessert','type'=>'free','value_est'=>8,'conditions'=>'Sign up for MyLindt Rewards. ~30 days to redeem.','signup_days_before'=>7,'redemption_window'=>'30 days','source_url'=>'https://curiocity.com/toronto-birthday-freebies-free-gifts/','sources_verified'=>3),
        array('id'=>'b56','name'=>'Edible Arrangements','freebie'=>'Free chocolate-dipped fruit cone','category'=>'dessert','type'=>'free','value_est'=>8,'conditions'=>'Join Edible Rewards.','signup_days_before'=>7,'redemption_window'=>'Birthday week','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>2),

        // ── BEAUTY & PERSONAL CARE ──
        array('id'=>'b57','name'=>'Sephora','freebie'=>'Free prestige birthday gift set (~$30 value)','category'=>'beauty','type'=>'free','value_est'=>30,'conditions'=>'Join free Beauty Insider program. Pick up in-store, no purchase required.','signup_days_before'=>7,'redemption_window'=>'Birthday month','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>5),
        array('id'=>'b58','name'=>'The Body Shop','freebie'=>'$10 reward voucher (no minimum purchase)','category'=>'beauty','type'=>'free','value_est'=>10,'conditions'=>'Join Love Your Body Club (free). ~30 days to redeem.','signup_days_before'=>7,'redemption_window'=>'30 days','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>4),
        array('id'=>'b59','name'=>'MAC Cosmetics','freebie'=>'Free birthday lipstick','category'=>'beauty','type'=>'free','value_est'=>24,'conditions'=>'Join M.A.C Lover rewards. In-store, no purchase required.','signup_days_before'=>7,'redemption_window'=>'Birthday month','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>2),
        array('id'=>'b60','name'=>'Kiehl\'s','freebie'=>'Free birthday gift (beauty product)','category'=>'beauty','type'=>'free','value_est'=>15,'conditions'=>'Sign up for Kiehl\'s Rewards Loyalty Program.','signup_days_before'=>7,'redemption_window'=>'Birthday month','source_url'=>'https://curiocity.com/toronto-birthday-freebies-free-gifts/','sources_verified'=>3),
        array('id'=>'b61','name'=>'Bath & Body Works','freebie'=>'Free body care product (~$12 value)','category'=>'beauty','type'=>'free','value_est'=>12,'conditions'=>'Join My Bath & Body Works Rewards. In-store, no purchase required.','signup_days_before'=>7,'redemption_window'=>'Birthday month','source_url'=>'https://www.bathandbodyworks.ca','sources_verified'=>2),
        array('id'=>'b62','name'=>'Lush Cosmetics','freebie'=>'Free fresh face mask (~$16 value)','category'=>'beauty','type'=>'free','value_est'=>16,'conditions'=>'Show photo ID on birthday. No signup needed. Call store to confirm.','signup_days_before'=>0,'redemption_window'=>'Birthday day','source_url'=>'https://www.lush.com/ca/en','sources_verified'=>2),
        array('id'=>'b63','name'=>'Fuzz Wax Bar','freebie'=>'Free wax during birthday month','category'=>'beauty','type'=>'free','value_est'=>25,'conditions'=>'Must be a member.','signup_days_before'=>7,'redemption_window'=>'Birthday month','source_url'=>'https://curiocity.com/toronto-birthday-freebies-free-gifts/','sources_verified'=>1),
        array('id'=>'b64','name'=>'Shoppers Drug Mart','freebie'=>'10,000-20,000 PC Optimum bonus points ($10-$20 value)','category'=>'beauty','type'=>'free','value_est'=>15,'conditions'=>'Must be PC Optimum member. Birthday on profile.','signup_days_before'=>7,'redemption_window'=>'Birthday month','source_url'=>'https://www.pcoptimum.ca','sources_verified'=>2),

        // ── ENTERTAINMENT ──
        array('id'=>'b65','name'=>'Medieval Times','freebie'=>'Free dinner and show (~$80 value)','category'=>'entertainment','type'=>'free','value_est'=>80,'conditions'=>'Sign up for Queen\'s Court Birthday Club. Must bring 1 paying adult. Reserve early.','signup_days_before'=>14,'redemption_window'=>'Birthday week','source_url'=>'https://www.moneywehave.com/birthday-freebies-in-toronto/','sources_verified'=>2,'lat'=>43.5861,'lng'=>-79.6393),
        array('id'=>'b66','name'=>'Cineplex','freebie'=>'Free movie ticket (~$15 value)','category'=>'entertainment','type'=>'free','value_est'=>15,'conditions'=>'SCENE+ member (free). Register birthday 30 days before. Ticket loads to account.','signup_days_before'=>30,'redemption_window'=>'Birthday week','source_url'=>'https://www.scene.ca','sources_verified'=>2),
        array('id'=>'b67','name'=>'Trapped Escape Rooms','freebie'=>'One free admission (within 2 days of birthday)','category'=>'entertainment','type'=>'free','value_est'=>30,'conditions'=>'Select locations only.','signup_days_before'=>0,'redemption_window'=>'2 days','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>1),

        // ── RETAIL ──
        array('id'=>'b68','name'=>'Indigo / Chapters','freebie'=>'20% off for birthday + 2,500 bonus points','category'=>'retail','type'=>'discount','value_est'=>10,'conditions'=>'Join Plum Rewards (free tier available).','signup_days_before'=>7,'redemption_window'=>'Birthday month','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>2),
        array('id'=>'b69','name'=>'Value Village','freebie'=>'20% off a single purchase during birthday month','category'=>'retail','type'=>'discount','value_est'=>10,'conditions'=>'Join Super Savers Club.','signup_days_before'=>7,'redemption_window'=>'Birthday month','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>1),
        array('id'=>'b70','name'=>'Mejuri','freebie'=>'$10 credit + exclusive Birthday Styling Session','category'=>'retail','type'=>'free','value_est'=>10,'conditions'=>'Join free membership. ~30 days to redeem.','signup_days_before'=>7,'redemption_window'=>'30 days','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>2),

        // ── KIDS ──
        array('id'=>'b71','name'=>'LEGO Store','freebie'=>'Free Minifigure — NO signup required','category'=>'kids','type'=>'free','value_est'=>5,'conditions'=>'Visit a store near birthday.','signup_days_before'=>0,'redemption_window'=>'Birthday week','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>2),
        array('id'=>'b72','name'=>'Build-A-Bear','freebie'=>'Pay-your-age bear (turn 5 = $5, normally $25+)','category'=>'kids','type'=>'discount','value_est'=>20,'conditions'=>'Join Build-A-Bear Bonus Club.','signup_days_before'=>7,'redemption_window'=>'Birthday month','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>1),
        array('id'=>'b73','name'=>'Chuck E. Cheese','freebie'=>'Free gameplay, tickets, cotton candy, upgrades','category'=>'kids','type'=>'free','value_est'=>15,'conditions'=>'Join Birthday Club.','signup_days_before'=>7,'redemption_window'=>'Birthday week','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>2),

        // ── MEXICAN / LATIN ──
        array('id'=>'b74','name'=>'Quesada Burritos','freebie'=>'Free churros','category'=>'mexican','type'=>'free','value_est'=>5,'conditions'=>'Join Quesada Qlub loyalty program.','signup_days_before'=>7,'redemption_window'=>'Birthday week','source_url'=>'https://www.overheretoronto.com/best-birthday-freebies-in-toronto/','sources_verified'=>3),
        array('id'=>'b75','name'=>'BarBurrito','freebie'=>'Free Churro + Dip or Oreo Churro','category'=>'mexican','type'=>'free','value_est'=>5,'conditions'=>'Download mobile app, join rewards club.','signup_days_before'=>7,'redemption_window'=>'Birthday week','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>2),

        // ── WELLNESS ──
        array('id'=>'b76','name'=>'Elmwood Spa','freebie'=>'Complimentary 3-course lunch at Terrace Restaurant','category'=>'wellness','type'=>'purchase_required','value_est'=>50,'conditions'=>'Book any spa service valued $180+ Mon-Fri during birthday month.','signup_days_before'=>7,'redemption_window'=>'Birthday month','source_url'=>'https://www.overheretoronto.com/best-birthday-freebies-in-toronto/','sources_verified'=>2,'lat'=>43.6690,'lng'=>-79.3890),

        // ── PETS ──
        array('id'=>'b77','name'=>'PetSmart','freebie'=>'Birthday or Gotcha Day gift coupon for your pet','category'=>'pets','type'=>'free','value_est'=>5,'conditions'=>'Join Treats Rewards.','signup_days_before'=>7,'redemption_window'=>'Birthday month','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>1),
        array('id'=>'b78','name'=>'Pet Valu','freebie'=>'Birthday perk for pet\'s Birthday/Gotcha Day','category'=>'pets','type'=>'free','value_est'=>5,'conditions'=>'Create Pet Profile with rewards program. ~30 days to redeem.','signup_days_before'=>7,'redemption_window'=>'30 days','source_url'=>'https://www.familyfuncanada.com/toronto/birthday-freebies-toronto-gta/','sources_verified'=>2)
    );
}

// ── Free Things Calendar Data ──
function _get_free_calendar() {
    return array(
        'always_free' => array(
            array('id'=>'f1','name'=>'Allan Gardens Conservatory','description'=>'Victorian glass greenhouse with tropical plants, orchids, seasonal flower shows','hours'=>'Daily 10am-5pm','address'=>'19 Horticultural Ave','category'=>'parks','lat'=>43.6614,'lng'=>-79.3745,'source_url'=>'https://www.toronto.ca/explore-enjoy/parks-gardens-beaches/gardens-and-horticulture/conservatories/allan-gardens-conservatory/'),
            array('id'=>'f2','name'=>'High Park + Free Zoo','description'=>'400 acres, hiking trails, free zoo with capybaras, bison, llamas, peacocks','hours'=>'Daily dawn to dusk','address'=>'1873 Bloor St W','category'=>'parks','lat'=>43.6465,'lng'=>-79.4637,'source_url'=>'https://www.highparkzoo.ca/'),
            array('id'=>'f3','name'=>'Riverdale Farm','description'=>'Working farm with cows, pigs, goats, chickens, horses — completely free','hours'=>'Daily 9am-5pm','address'=>'201 Winchester St','category'=>'parks','lat'=>43.6677,'lng'=>-79.3597,'source_url'=>'https://www.toronto.ca/explore-enjoy/parks-gardens-beaches/zoos-farms/riverdalefarm/'),
            array('id'=>'f4','name'=>'The Power Plant Gallery','description'=>'Canada\'s leading contemporary art gallery — always free','hours'=>'Wed-Sun 10am-5pm, Thu until 8pm','address'=>'231 Queens Quay W','category'=>'gallery','lat'=>43.6383,'lng'=>-79.3818,'source_url'=>'https://www.thepowerplant.org/visit'),
            array('id'=>'f5','name'=>'MOCA (Museum of Contemporary Art)','description'=>'Pay-what-you-can contemporary art museum','hours'=>'Thu-Sun 10am-5pm, Fri until 9pm','address'=>'158 Sterling Rd','category'=>'gallery','lat'=>43.6614,'lng'=>-79.4507,'source_url'=>'https://moca.ca/visit/'),
            array('id'=>'f6','name'=>'Rouge National Urban Park','description'=>'Canada\'s first national urban park — 40+ sq km of forest, wetland, beach','hours'=>'Daily dawn to dusk','address'=>'Multiple entrances','category'=>'parks','lat'=>43.8084,'lng'=>-79.1589,'source_url'=>'https://parks.canada.ca/pn-np/on/rouge'),
            array('id'=>'f7','name'=>'Graffiti Alley','description'=>'1 km of street art murals, constantly evolving','hours'=>'24/7','address'=>'Rush Lane (Portland to Spadina)','category'=>'gallery','lat'=>43.6478,'lng'=>-79.4020,'source_url'=>'https://www.destinationtoronto.com/explore-toronto/graffiti-alley'),
            array('id'=>'f8','name'=>'Nathan Phillips Square','description'=>'TORONTO sign, reflecting pool, skating in winter','hours'=>'24/7','address'=>'100 Queen St W','category'=>'parks','lat'=>43.6534,'lng'=>-79.3841,'source_url'=>'https://www.toronto.ca/explore-enjoy/festivals-events/nathan-phillips-square/'),
            array('id'=>'f9','name'=>'Distillery District','description'=>'Pedestrian-only historic district, cobblestones, public art','hours'=>'24/7 (outdoor)','address'=>'55 Mill St','category'=>'gallery','lat'=>43.6503,'lng'=>-79.3596,'source_url'=>'https://www.thedistillerydistrict.com/'),
            array('id'=>'f10','name'=>'Scarborough Bluffs','description'=>'90-metre geological cliffs along Lake Ontario','hours'=>'24/7','address'=>'1 Brimley Rd S','category'=>'parks','lat'=>43.7110,'lng'=>-79.2308,'source_url'=>'https://www.toronto.ca/'),
            array('id'=>'f11','name'=>'Evergreen Brick Works','description'=>'Former quarry: wetlands, trails, free exhibits, Saturday farmers market','hours'=>'Grounds daily','address'=>'550 Bayview Ave','category'=>'parks','lat'=>43.6844,'lng'=>-79.3651,'source_url'=>'https://www.evergreen.ca/evergreen-brick-works/'),
            array('id'=>'f12','name'=>'Harbourfront Centre Galleries','description'=>'Multiple free gallery spaces with rotating contemporary art','hours'=>'Daily 10am-6pm+','address'=>'235 Queens Quay W','category'=>'gallery','lat'=>43.6385,'lng'=>-79.3829,'source_url'=>'https://harbourfrontcentre.com/'),
            array('id'=>'f13','name'=>'Toronto Reference Library','description'=>'Free exhibits, Arthur Conan Doyle Room, digital innovation hub','hours'=>'Mon-Sat varies','address'=>'789 Yonge St','category'=>'gallery','lat'=>43.6725,'lng'=>-79.3869,'source_url'=>'https://www.torontopubliclibrary.ca/torontoreferencelibrary/')
        ),
        'weekly' => array(
            'tuesday' => array(
                array('id'=>'w1','name'=>'Aga Khan Museum — FREE','description'=>'World-class Islamic art, stunning Fumihiko Maki architecture. Normally $20.','hours'=>'10am-5:30pm','address'=>'77 Wynford Dr','category'=>'museum','savings'=>20,'source_url'=>'https://agakhanmuseum.org/visit','lat'=>43.7256,'lng'=>-79.3329),
                array('id'=>'w2','name'=>'ROM — FREE for College/University Students','description'=>'Royal Ontario Museum free with valid student ID. Normally $26.','hours'=>'All day','address'=>'100 Queens Park','category'=>'museum','savings'=>26,'source_url'=>'https://forums.redflagdeals.com/royal-ontario-museum-toronto-rom-free-tuesday-admission-college-university-students-2712456/','lat'=>43.6677,'lng'=>-79.3948)
            ),
            'wednesday' => array(
                array('id'=>'w3','name'=>'Art Gallery of Ontario (AGO) — FREE','description'=>'95,000+ works, Frank Gehry Galleria Italia. Normally $25.','hours'=>'6pm-9pm','address'=>'317 Dundas St W','category'=>'museum','savings'=>25,'source_url'=>'https://ago.ca/visit','lat'=>43.6536,'lng'=>-79.3925),
                array('id'=>'w4','name'=>'Gardiner Museum — FREE','description'=>'Ceramics museum. Normally $15.','hours'=>'4pm-9pm','address'=>'111 Queens Park','category'=>'museum','savings'=>15,'source_url'=>'https://www.gardinermuseum.on.ca/visit/','lat'=>43.6683,'lng'=>-79.3935),
                array('id'=>'w5','name'=>'Aga Khan Museum — FREE (also Wed after 4pm)','description'=>'Also free Wednesday afternoons. Normally $20.','hours'=>'After 4pm','address'=>'77 Wynford Dr','category'=>'museum','savings'=>20,'source_url'=>'https://forums.redflagdeals.com/aga-khan-museum-toronto-aga-khan-museum-free-admission-wednesdays-after-4pm-2529373/','lat'=>43.7256,'lng'=>-79.3329)
            ),
            'wednesday_monthly' => array(
                array('id'=>'w6','name'=>'ROM — FREE 3rd Wednesday','description'=>'Royal Ontario Museum. 13 million objects. Normally $26. Next: Feb 18, 2026.','hours'=>'4:30pm-8:30pm','address'=>'100 Queens Park','category'=>'museum','savings'=>26,'source_url'=>'https://www.rom.on.ca/en/visit-us','lat'=>43.6677,'lng'=>-79.3948)
            ),
            'thursday' => array(
                array('id'=>'w7','name'=>'Bata Shoe Museum — Pay What You Can','description'=>'13,000+ shoes spanning 4,500 years. Normally $14.','hours'=>'5pm-8pm','address'=>'327 Bloor St W','category'=>'museum','savings'=>14,'source_url'=>'https://batashoemuseum.ca/visit/','lat'=>43.6673,'lng'=>-79.4002)
            ),
            'friday' => array(
                array('id'=>'w8','name'=>'MOCA — Late Friday (PWYC)','description'=>'Contemporary art museum, extended hours until 9pm.','hours'=>'10am-9pm','address'=>'158 Sterling Rd','category'=>'museum','savings'=>10,'source_url'=>'https://moca.ca/visit/','lat'=>43.6614,'lng'=>-79.4507),
                array('id'=>'w9','name'=>'First Friday Gallery Crawl (1st Fri/month)','description'=>'Dozens of galleries open late with free receptions.','hours'=>'7pm-11pm','address'=>'Queen West, Ossington, Dundas West','category'=>'gallery','savings'=>0,'source_url'=>'https://www.blogto.com/arts/')
            ),
            'saturday' => array(
                array('id'=>'w10','name'=>'Evergreen Brick Works Farmers Market','description'=>'Local produce, artisan goods, food vendors, live music.','hours'=>'8am-1pm','address'=>'550 Bayview Ave','category'=>'market','savings'=>0,'source_url'=>'https://www.evergreen.ca/evergreen-brick-works/markets/','lat'=>43.6844,'lng'=>-79.3651),
                array('id'=>'w11','name'=>'St. Lawrence Market','description'=>'Operating since 1803. Named world\'s best food market by National Geographic.','hours'=>'5am-3pm','address'=>'93 Front St E','category'=>'market','savings'=>0,'source_url'=>'https://www.stlawrencemarket.com/','lat'=>43.6487,'lng'=>-79.3716),
                array('id'=>'w12','name'=>'Parkrun Free 5K','description'=>'Free timed weekly run/walk. All abilities welcome.','hours'=>'9am','address'=>'High Park (and others)','category'=>'fitness','savings'=>0,'source_url'=>'https://www.parkrun.ca/','lat'=>43.6465,'lng'=>-79.4637),
                array('id'=>'w13','name'=>'Tommy Thompson Park','description'=>'5km peninsula, bird sanctuary, urban wilderness. Weekends only.','hours'=>'Dawn-dusk','address'=>'1 Leslie St','category'=>'parks','savings'=>0,'source_url'=>'https://tommythompsonpark.ca/','lat'=>43.6270,'lng'=>-79.3390)
            ),
            'sunday' => array(
                array('id'=>'w14','name'=>'Bata Shoe Museum — FREE','description'=>'Free all day Sundays. Normally $14.','hours'=>'All day','address'=>'327 Bloor St W','category'=>'museum','savings'=>14,'source_url'=>'https://forums.redflagdeals.com/bata-shoe-museum-toronto-bata-shoe-museum-free-admission-every-sunday-2529340/','lat'=>43.6673,'lng'=>-79.4002),
                array('id'=>'w15','name'=>'Tommy Thompson Park','description'=>'Open weekends only.','hours'=>'Dawn-dusk','address'=>'1 Leslie St','category'=>'parks','savings'=>0,'source_url'=>'https://tommythompsonpark.ca/','lat'=>43.6270,'lng'=>-79.3390)
            )
        )
    );
}

// ── Canadian Deals Data ──
function _get_canadian_deals() {
    return array(
        'active_today' => array(
            array('id'=>'d1','name'=>'FREE Ghirardelli Chocolockets','description'=>'2 free Ghirardelli chocolate pieces','category'=>'food','type'=>'free','expiry'=>'2026-02-10','source_url'=>'https://myfreeproductsamples.com/free-samples-category/chocolockets/'),
            array('id'=>'d2','name'=>'Roy Thomson Hall Free Concert','description'=>'Exultate Chamber Singers at noon — FREE','category'=>'entertainment','type'=>'free','expiry'=>'2026-02-10','source_url'=>'https://forums.redflagdeals.com/roy-thomson-hall-gta-roy-thomson-hall-exultate-chamber-singers-free-concert-feb-10-noon-2801205/'),
            array('id'=>'d3','name'=>'Chick-fil-A Free Iced Coffee (Students)','description'=>'Free iced coffee 10-11am M/W/F through Feb at Eaton Centre','category'=>'food','type'=>'free','expiry'=>'2026-02-28','source_url'=>'https://forums.redflagdeals.com/chick-fil-eaton-centre-free-iced-coffee-students-10-11am-mondays-wednesdays-fridays-february-2800495/'),
            array('id'=>'d4','name'=>'FREE CeraVe Full-Size Moisturizer','description'=>'Free full-size CeraVe body moisturizer every weekday through Feb 27','category'=>'beauty','type'=>'free','expiry'=>'2026-02-27','source_url'=>'https://myfreeproductsamples.com/free-samples-category/moisturizer/'),
            array('id'=>'d5','name'=>'McCain FryDay Free Meal','description'=>'Free fry-based meal — cheer Team Canada or tag McCains online','category'=>'food','type'=>'free','expiry'=>'2026-03-01','source_url'=>'https://forums.redflagdeals.com/mccain-fryday-fanzone-cheer-team-canada-get-free-fry-based-meal-online-free-coupon-when-you-tag-mccains-online-2801449/'),
            array('id'=>'d6','name'=>'El Furniture Warehouse — Free Burger for Healthcare Workers','description'=>'Free burger every Monday FOREVER for healthcare workers / first responders','category'=>'food','type'=>'free','expiry'=>'permanent','source_url'=>'https://forums.redflagdeals.com/el-furniture-warehouse-restaurants-healthcare-workers-first-responders-get-free-burger-every-monday-life-ab-qc-bc-2480936/')
        ),
        'upcoming' => array(
            array('id'=>'d7','name'=>'FREE IKEA Limited-Edition Tote Bag','description'=>'Valentine\'s Day special tote bag','category'=>'retail','type'=>'free','date'=>'2026-02-14','source_url'=>'https://myfreeproductsamples.com/free-samples-category/tote-bag/'),
            array('id'=>'d8','name'=>'FREE Take-Home Meal at Stacktmarket','description'=>'Cook Unity free microwave meal at noon','category'=>'food','type'=>'free','date'=>'2026-02-15','source_url'=>'https://forums.redflagdeals.com/cook-unity-stacktmarket-free-take-home-microwave-meal-noon-sunday-february-15-2801418/'),
            array('id'=>'d9','name'=>'Lumiere: Art of Light at Ontario Place','description'=>'Free illuminated art installation Feb 16 - Mar 27','category'=>'entertainment','type'=>'free','date'=>'2026-02-16','source_url'=>'https://forums.redflagdeals.com/ontario-place-toronto-feb-16-mar-27-lumiu-re-art-light-ontario-place-2800510/'),
            array('id'=>'d10','name'=>'FREE Elvis IMAX Sneak Preview','description'=>'Free IMAX screening at Cineplex Yonge-Dundas','category'=>'entertainment','type'=>'free','date'=>'2026-02-18','source_url'=>'https://forums.redflagdeals.com/toronto-feb-18-epic-elvis-presley-concert-free-imax-sneak-preview-cineplex-yonge-dundas-ymmv-2800513/')
        ),
        'samples_by_mail' => array(
            array('id'=>'s1','name'=>'SampleSource Free Sample Boxes','description'=>'Free product sample boxes (beauty, food, household) shipped to your door 2-3x/year','category'=>'samples','type'=>'free','source_url'=>'https://www.samplesource.com/'),
            array('id'=>'s2','name'=>'Free Dove Hair Therapy Sample','description'=>'Free Dove hair therapy product shipped','category'=>'beauty','type'=>'free','source_url'=>'https://www.bargainmoose.ca/freebies'),
            array('id'=>'s3','name'=>'Free La Roche-Posay Mela B3 Serum Sample','description'=>'Free dark spot correcting serum sample','category'=>'beauty','type'=>'free','source_url'=>'https://myfreeproductsamples.com/free-samples-category/serum-4/'),
            array('id'=>'s4','name'=>'1 Million FREE It\'s a 10 Scalp Products','description'=>'Free hair/scalp treatment — 1M units being given away','category'=>'beauty','type'=>'free','source_url'=>'https://myfreeproductsamples.com/free-samples-category/scalp/'),
            array('id'=>'s5','name'=>'Free INITIO Parfums Fragrance Samples','description'=>'Free luxury fragrance samples by mail','category'=>'beauty','type'=>'free','source_url'=>'https://myfreeproductsamples.com/free-samples-category/fragrance-11/')
        ),
        'deal_sites' => array(
            array('name'=>'RedFlagDeals Freebies','url'=>'https://forums.redflagdeals.com/freebies-f12/','description'=>'Canada\'s largest deal community — 775K+ members'),
            array('name'=>'SmartCanucks','url'=>'https://smartcanucks.ca/','description'=>'Daily Canadian deals, coupons, and flyer roundups'),
            array('name'=>'BargainMoose','url'=>'https://www.bargainmoose.ca/freebies','description'=>'Curated Canadian freebies list'),
            array('name'=>'SampleSource','url'=>'https://www.samplesource.com/','description'=>'Free product sample boxes shipped to your door'),
            array('name'=>'CanadianFreeStuff','url'=>'https://www.canadianfreestuff.com/','description'=>'Running since 1999 — free stuff, coupons, contests'),
            array('name'=>'Save.ca','url'=>'https://www.save.ca/coupons','description'=>'Official Canadian coupon platform — printable & digital'),
            array('name'=>'Flipp','url'=>'https://flipp.com/','description'=>'Digital flyer aggregator for all Canadian retailers'),
            array('name'=>'Checkout 51','url'=>'https://www.checkout51.com/','description'=>'Canadian cashback app — upload receipts, get money back'),
            array('name'=>'Caddle','url'=>'https://www.caddle.ca/','description'=>'Canadian cashback + surveys'),
            array('name'=>'Rakuten Canada','url'=>'https://www.rakuten.ca/','description'=>'Cashback portal for online shopping')
        )
    );
}

// ── Filter logic ──
function _filter_deals($deals, $category, $type_filter, $search_q) {
    $result = array();
    foreach ($deals as $d) {
        if ($category !== '' && isset($d['category']) && $d['category'] !== $category) continue;
        if ($type_filter !== '' && isset($d['type']) && $d['type'] !== $type_filter) continue;
        if ($search_q !== '') {
            $haystack = strtolower(
                (isset($d['name']) ? $d['name'] : '') . ' ' .
                (isset($d['freebie']) ? $d['freebie'] : '') . ' ' .
                (isset($d['description']) ? $d['description'] : '') . ' ' .
                (isset($d['conditions']) ? $d['conditions'] : '') . ' ' .
                (isset($d['category']) ? $d['category'] : '')
            );
            if (strpos($haystack, $search_q) === false) continue;
        }
        $result[] = $d;
    }
    return $result;
}

// ── Sort by distance if near param ──
function _sort_by_distance(&$deals, $user_lat, $user_lng) {
    foreach ($deals as &$d) {
        if (isset($d['lat']) && isset($d['lng'])) {
            $d['distance_m'] = (int)_deals_haversine($user_lat, $user_lng, $d['lat'], $d['lng']);
        } else {
            $d['distance_m'] = 999999;
        }
    }
    unset($d);
    usort($deals, '_deals_cmp_distance');
}

// ── Main dispatch ──
$user_lat = 0;
$user_lng = 0;
if ($near !== '') {
    $parts = explode(',', $near);
    if (count($parts) === 2) {
        $user_lat = (float)$parts[0];
        $user_lng = (float)$parts[1];
    }
}

$response = array('ok' => true, 'action' => $action, 'last_updated' => '2026-02-10T22:00:00-05:00', 'data_version' => '1.0', 'generated_at' => date('c'));

if ($action === 'birthday' || $action === 'all' || $action === 'search') {
    $bday = _get_birthday_deals();
    $bday = _filter_deals($bday, $category, $type_filter, $search_q);
    if ($user_lat != 0) _sort_by_distance($bday, $user_lat, $user_lng);
    $response['birthday_freebies'] = $bday;
    $response['birthday_count'] = count($bday);
}

if ($action === 'free_today' || $action === 'calendar' || $action === 'all' || $action === 'search') {
    $cal = _get_free_calendar();
    $response['free_calendar'] = $cal;

    // Determine what's free today
    $day_names = array('sunday','monday','tuesday','wednesday','thursday','friday','saturday');
    $today_dow = strtolower(date('l'));
    $free_today = $cal['always_free'];
    if (isset($cal['weekly'][$today_dow])) {
        $free_today = array_merge($free_today, $cal['weekly'][$today_dow]);
    }
    if ($user_lat != 0) _sort_by_distance($free_today, $user_lat, $user_lng);
    $response['free_today'] = $free_today;
    $response['free_today_count'] = count($free_today);
    $response['today_day'] = $today_dow;
}

if ($action === 'canadian_deals' || $action === 'all' || $action === 'search') {
    $deals = _get_canadian_deals();
    if ($search_q !== '') {
        $deals['active_today'] = _filter_deals($deals['active_today'], $category, $type_filter, $search_q);
        $deals['upcoming'] = _filter_deals($deals['upcoming'], $category, $type_filter, $search_q);
        $deals['samples_by_mail'] = _filter_deals($deals['samples_by_mail'], $category, $type_filter, $search_q);
    }
    $response['canadian_deals'] = $deals;
}

if ($action === 'categories') {
    $response['categories'] = array(
        array('key'=>'food','label'=>'Food & Drink','icon'=>"\xF0\x9F\x8D\x94"),
        array('key'=>'coffee','label'=>'Coffee & Smoothies','icon'=>"\xE2\x98\x95"),
        array('key'=>'bubble_tea','label'=>'Bubble Tea','icon'=>"\xF0\x9F\xA7\x8B"),
        array('key'=>'dessert','label'=>'Ice Cream & Desserts','icon'=>"\xF0\x9F\x8D\xA6"),
        array('key'=>'bakery','label'=>'Bakeries & Bagels','icon'=>"\xF0\x9F\xA5\x90"),
        array('key'=>'mexican','label'=>'Mexican & Latin','icon'=>"\xF0\x9F\x8C\xAE"),
        array('key'=>'beauty','label'=>'Beauty & Personal Care','icon'=>"\xF0\x9F\x92\x84"),
        array('key'=>'retail','label'=>'Retail & Shopping','icon'=>"\xF0\x9F\x9B\x8D"),
        array('key'=>'entertainment','label'=>'Entertainment','icon'=>"\xF0\x9F\x8E\xAC"),
        array('key'=>'kids','label'=>'Kids & Toys','icon'=>"\xF0\x9F\xA7\xB8"),
        array('key'=>'pets','label'=>'Pets','icon'=>"\xF0\x9F\x90\xBE"),
        array('key'=>'wellness','label'=>'Wellness & Spa','icon'=>"\xF0\x9F\xA7\x96"),
        array('key'=>'museum','label'=>'Museums','icon'=>"\xF0\x9F\x8F\x9B"),
        array('key'=>'parks','label'=>'Parks & Nature','icon'=>"\xF0\x9F\x8C\xB3"),
        array('key'=>'gallery','label'=>'Galleries & Art','icon'=>"\xF0\x9F\x96\xBC"),
        array('key'=>'market','label'=>'Markets','icon'=>"\xF0\x9F\x9B\x92"),
        array('key'=>'fitness','label'=>'Fitness','icon'=>"\xF0\x9F\x8F\x83"),
        array('key'=>'samples','label'=>'Free Samples','icon'=>"\xF0\x9F\x93\xA6"),
        array('key'=>'digital','label'=>'Digital & Online','icon'=>"\xF0\x9F\x92\xBB")
    );
}

echo json_encode($response);
