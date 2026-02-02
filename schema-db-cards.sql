describe cards;
oracle_id	char(36)	NO	PRI	NULL		
name	varchar(255)	NO	MUL	NULL		
cmc	float	NO		0		
color_identity	longtext	NO		NULL		
colors	longtext	YES		NULL		
keywords	longtext	NO		NULL		
type_line	varchar(255)	NO		NULL		
legalities	longtext	NO		NULL		


describe cards_prints;
id	int(11)	NO	PRI	NULL	auto_increment	
oracle_id	char(36)	YES	MUL	NULL		
base_card_id	int(11)	NO	MUL	NULL		
set_id	int(11)	NO	MUL	NULL		
cardtrader_id	int(11)	YES	UNI	NULL		
scryfall_id	char(36)	YES		NULL		
collector_number	varchar(20)	YES		NULL		
rarity	varchar(20)	YES		NULL		
condition_default	varchar(20)	YES		NM		
image_path	varchar(255)	YES		NULL		
image_status	enum('pending','ok','rejected')	YES		pending		
available_languages	text	YES		NULL		
has_foil	tinyint(1)	YES		0		
has_signed	tinyint(1)	YES		0		
has_altered	tinyint(1)	YES		0		
condition_options	text	YES		NULL		


describe categories;
id	int(11)	NO	PRI	NULL		
name_en	varchar(100)	NO		NULL		
name_it	varchar(100)	YES		NULL		
is_card	tinyint(1)	YES		0		

describe games;
id	int(11)	NO	PRI	NULL	auto_increment	
name	varchar(50)	NO		NULL		
slug	varchar(50)	NO		NULL		
cardtrader_game_id	int(11)	NO		NULL		

describe op_cards;
card_id	varchar(20)	NO	PRI	NULL		
name_en	varchar(255)	NO		NULL		
color	varchar(50)	YES		NULL		
type	varchar(50)	YES		NULL		
attribute	varchar(50)	YES		NULL		
cost	int(11)	YES		NULL		
power	int(11)	YES		NULL		
counter	int(11)	YES		NULL		
life	int(11)	YES		NULL		
effect	longtext	YES		NULL		
category	varchar(100)	YES		NULL		

describe op_prints;
id	int(11)	NO	PRI	NULL	auto_increment	
card_id	varchar(20)	NO	MUL	NULL		
set_id	int(11)	NO		NULL		
cardtrader_id	int(11)	YES	UNI	NULL		
rarity	varchar(20)	YES		NULL		
image_path	varchar(255)	YES		NULL		
image_status	enum('pending','ok','rejected')	YES		pending		
is_alt_art	tinyint(1)	YES		0		
is_parallel	tinyint(1)	YES		0		

describe pk_cards;
card_id	varchar(50)	NO	PRI	NULL		
name_en	varchar(255)	NO		NULL		
supertype	varchar(50)	YES		NULL		
subtypes	varchar(255)	YES		NULL		
hp	varchar(10)	YES		NULL		
types	varchar(255)	YES		NULL		
evolves_from	varchar(255)	YES		NULL		
attacks	longtext	YES		NULL		
weaknesses	longtext	YES		NULL		
retreat_cost	int(11)	YES		NULL		

describe pk_prints;
id	int(11)	NO	PRI	NULL	auto_increment	
card_id	varchar(50)	NO	MUL	NULL		
set_id	int(11)	NO	MUL	NULL		
cardtrader_id	int(11)	YES	UNI	NULL		
collector_number	varchar(50)	YES		NULL		
rarity	varchar(50)	YES		NULL		
flavor_text	text	YES		NULL		
image_url	varchar(500)	YES		NULL		
image_status	enum('pending','ok','rejected')	YES		pending		

describe sealed_products;
id	int(11)	NO	PRI	NULL	auto_increment	
set_id	int(11)	NO	MUL	NULL		
category_id	int(11)	NO	MUL	NULL		
cardtrader_id	int(11)	YES	UNI	NULL		
name_en	varchar(255)	NO		NULL		
name_it	varchar(255)	YES		NULL		
image_path	varchar(255)	YES		NULL		
image_status	enum('pending','ok','rejected')	YES		pending		

describe sets;
id	int(11)	NO	PRI	NULL	auto_increment	
cardtrader_id	int(11)	YES	UNI	NULL		
code	varchar(20)	YES		NULL		
name	varchar(255)	NO		NULL		
release_date	date	YES		NULL		
created_at	timestamp	YES		current_timestamp()		
game_id	int(11)	NO		1		
