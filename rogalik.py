import libtcodpy as libtcod
from math import sqrt
import textwrap

#window size
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
DEBUG_ON = True

color_dark_wall = libtcod.Color(50,50,50)
color_lit_wall = libtcod.Color(110,110,110)
color_dark_ground = libtcod.Color(50,50,50)
color_lit_ground = libtcod.Color(180,180,180)

#dungeon specs
ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30
MAX_ROOM_MONSTERS = 3
MAX_ROOM_ITEMS = 2

FOV_ALGO = 0
FOV_LIGHT_WALLS = True
TORCH_RADIUS = 10

#GUI specs
BAR_WIDTH = 20
PANEL_HEIGHT = 7
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT
INVENTORY_WIDTH = 50

MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1

LIMIT_FPS = 20

#Item specs
LIGHTNING_DAMAGE = 20
LIGHTNING_RANGE = 5
CONFUSE_NUM_TURNS = 5
CONFUSE_RANGE = 8

class Object:
	global fov_map
	#a generic object: player/monster/item/stairs/whatever.
	#always represented by a character.
	def __init__(self, x, y, char, name, color, blocks=False, fighter=None, ai=None, item=None):
		self.x = x
		self.y = y
		self.char = char
		self.name = name
		self.color = color
		self.known = False
		self.blocks = blocks
		self.fighter = fighter
		if self.fighter:
			self.fighter.owner = self
		self.ai = ai
		if self.ai:
			self.ai.owner = self
		self.item = item
		if self.item:
			self.item.owner = self
		
	def move(self, dx, dy):
		#move by a given amount
		if not is_blocked(self.x+dx, self.y+dy):
			self.x += dx
			self.y += dy
	
	def distance_to(self, other):
		dx = other.x - self.x
		dy = other.y - self.y
		return sqrt(dx ** 2 + dy ** 2)
	
	def move_towards(self, target_x, target_y):
		#vector from this object to target
		dx = target_x - self.x
		dy = target_y - self.y
		distance = sqrt(dx ** 2 + dy ** 2)
		
		dx = int(round(dx / distance))
		dy = int(round(dy / distance))
		self.move(dx, dy)
		
	def draw(self):
		if not self.known and libtcod.map_is_in_fov(fov_map, self.x, self.y):
			self.known = True
		if self.known:
			libtcod.console_set_default_foreground(con, self.color)
			libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)
	
	def send_to_back(self):
		#make this object drawn first, so it's covered by any other object
		global objects
		objects.remove(self)
		objects.insert(0, self)
	
	def clear(self):
		if self.known:
			libtcod.console_put_char(con, self.x, self.y, ".", libtcod.BKGND_NONE)

#####################
# OBJECT SUBCLASSES #
#####################
			
class Fighter:
	#this is a widget with all the functionality for fighting.
	#it includes stats (see init), functions for taking damage and attacking.
	#dying and possibly skills will be delegated to outside functions.

	def __init__(self, hp, defence, power, death_function = None):
		#all ints except death_function, which is a function
		self.max_hp = hp
		self.hp = hp
		self.defence = defence
		self.power = power
		self.death_function = death_function
		
	def take_damage(self, damage):
		#apply damage if possible. damage is an int.
		if damage > 0:
			self.hp -= damage
			if self.hp <= 0:
				function = self.death_function
				if function is not None:
					function(self.owner)
				else:
					monster_death(self.owner)
					
	def heal(self, amount):
		#heal by the amount given in an int
		self.hp += amount
		if self.hp > self.max_hp:
			self.hp = self.max_hp
			
			
	def attack(self, target):
		#fire emblem type damage calculation. target arg is an Object with a defined Fighter class.
		damage = self.power - target.fighter.defence
		if damage > 0:
			message("{0} attacks {1} for {2} hit points! [{3}/{4}]".format(self.owner.name.capitalize(), target.name, damage, target.fighter.hp - damage, target.fighter.max_hp), libtcod.lighter_flame)
			target.fighter.take_damage(damage)
		else:
			print self.owner.name.capitalize() + ' attacks ' + target.name + ' ineffectually.'
			
			
def player_death(player):
	#the game ends
	global game_state
	message('You died!', libtcod.red)
	game_state = 'dead'
	
	player.char = '%'
	player.color = libtcod.dark_red
	
def monster_death(monster):
	#transform monster into a corpse that doesn't block
	message (str(monster.name.capitalize() + ' dies!'), libtcod.orange)
	monster.char = '%'
	monster.color = libtcod.dark_red
	monster.blocks = False
	monster.fighter = None
	monster.ai = None
	monster.name = 'remains of ' + monster.name
	monster.send_to_back()
	


class Item:
	def __init__(self, use_function=None):
		self.use_function = use_function

	def pick_up(self):
		if len(inventory) >= 26:
			message('Your inventory is full, cannot pick up {0}.'.format(self.owner.name), libtcod.red)
		else:
			inventory.append(self.owner)
			objects.remove(self.owner)
			message('You pick up a {0}.'.format(self.owner.name), libtcod.green)
			
	def use(self):
		if self.use_function is None:
			message('You cannot use this right now!')
		else:
			if self.use_function() != 'no-use':
				inventory.remove(self.owner)
	
##############
# AI CLASSES #
##############
#Each of those must have a take_turn method.

class BasicMelee:
	'''AI for a generic monster that approaches the player and attacks them.'''
	def take_turn(self):
		#turn of a basic monster. they run on ostrich logic, see player only if player sees them
		monster = self.owner
		if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
			if monster.distance_to(player) >= 2:
				monster.move_towards(player.x, player.y)
			elif player.fighter.hp > 0:
				monster.fighter.attack(player)

class Confused:
	'''AI for a confused monster. Moves in a random direction and lasts a set number of turns.'''
	def __init__(self, old_ai, num_turns = CONFUSE_NUM_TURNS):
		self.old_ai = old_ai
		self.num_turns = num_turns
	
	def take_turn(self):
		if self.num_turns > 0:
			self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
			self.num_turns -= 1
		else:
			self.owner.ai = self.old_ai
			message('The {0} is no longer confused!'.format(self.owner.name), libtcod.red)

################
# MAP HANDLING #
################
class Tile:
	#a tile of the map and its properties
	
	def __init__(self, blocked, block_sight = None):
		self.blocked = blocked
		if block_sight == None: block_sight = blocked
		self.block_sight = block_sight
		self.explored = False

class Rect:
	#a rectangle on the map.
	def __init__(self, x, y, w, h):
		self.x1 = x
		self.y1 = y
		self.x2 = x+w
		self.y2 = y+h
		
	def center(self):
		center_x = (self.x1 + self.x2) / 2
		center_y = (self.y1 + self.y2) / 2
		return (center_x, center_y)
		
	def intersect(self, other):
		#returns true if this rectangle intersects another
		return (self.x1 <= other.x2 and self.x2 >= other.x1 and self.y1 <= other.y2 and self.y2 >= other.y1)
		
def create_room(room):
	global map
	
	for x in range(room.x1+1, room.x2):
		for y in range(room.y1+1, room.y2):
			map[x][y].blocked = False
			map[x][y].block_sight = False

def place_objects(room):
	num_monsters = libtcod.random_get_int(0, 0, MAX_ROOM_MONSTERS)
	num_items = libtcod.random_get_int(0, 0, MAX_ROOM_ITEMS)
	
	for i in range(num_monsters):
		x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
		y = libtcod.random_get_int(0, room.y1+1, room.y2-1)
		
		if not is_blocked(x, y):
		#create monster if tile is free. TODO: will have to delegate the monster stats to a table or something later
			dice = libtcod.random_get_int(0, 0, 100)
			if dice < 80:
				#kobold
				monster = Object(x, y, 'k', 'kobold', libtcod.dark_blue, True, fighter=Fighter(10,0,3), ai=BasicMelee())
			else:
				#dragon
				monster = Object(x, y, 'D', 'dragon', libtcod.darker_green, True, fighter=Fighter(16,1,4), ai=BasicMelee())
			objects.append(monster)
			
	for i in range(num_items):
		x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
		y = libtcod.random_get_int(0, room.y1+1, room.y2-1)
		if not is_blocked(x, y):
			dice = libtcod.random_get_int(0, 0, 100)
			if dice < 70:
				#potion
				item = Object(x, y, "!", "healing potion", libtcod.flame, item=Item(cast_heal))
			elif dice < 70+15:
				#scroll of lightning bolt
				item = Object(x, y, "?", "scroll of lightning bolt", libtcod.light_yellow, item=Item(cast_lightning))
			else:
				#scroll of confuse monster
				item = Object(x, y, "?", "scroll of confuse monster", libtcod.violet, item=Item(cast_confuse))
			objects.append(item)
			item.send_to_back()
		
def create_h_tunnel(x1, x2, y):
	global map
	#horizontal tunnel
	for x in range(min(x1, x2), max(x1, x2)+1):
		map[x][y].blocked = False
		map[x][y].block_sight = False
			
def create_v_tunnel(y1, y2, x):
	global map
	#vertical tunnel
	for y in range(min(y1, y2), max(y1, y2)+1):
		map[x][y].blocked = False
		map[x][y].block_sight = False

def is_blocked(x, y):
	#check if given tile is blocked
	#test for impassable terrain
	if map[x][y].blocked:
		return True
		
	#test for impassable objects
	for object in objects:
		if object.blocks and object.x == x and object.y == y:
			return True
			
	return False
		
#map size and creation
MAP_WIDTH = 80
MAP_HEIGHT = 43

def make_map():
	global map
	
	#fill map with unblocked tiles
	map = [[ Tile(True) for y in range(MAP_HEIGHT)] for x in range(MAP_WIDTH)]
	
	rooms = []
	num_rooms = 0
	for r in range(MAX_ROOMS):
		#randomize size
		w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
		h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
		#restrict position to within map
		x = libtcod.random_get_int(0,0,MAP_WIDTH - w - 1)
		y = libtcod.random_get_int(0,0,MAP_HEIGHT - h - 1)
		#check if it intersects
		new_room = Rect(x, y, w, h)
		failed = False
		for other_room in rooms:
			if new_room.intersect(other_room):
				failed = True
				break
		
		if not failed:
			create_room(new_room)
			(new_x, new_y) = new_room.center()
			
			#DEBUG OPTION: identifies room creation order
			if DEBUG_ON == True:
				room_no = Object(new_x, new_y, chr(65+num_rooms), 'room number', libtcod.white)
				objects.insert(0, room_no)
			
			if num_rooms == 0:
				#the first room always contains the player
				player.x = new_x
				player.y = new_y
				
				
			else:
				#connect all rooms after the first to the previous
				
				(prev_x, prev_y) = rooms[num_rooms-1].center()
				
				if libtcod.random_get_int(0,0,1) == 1:
					#flip a coin: either create h tunnel first and v second
					create_h_tunnel(prev_x, new_x, prev_y)
					create_v_tunnel(prev_y, new_y, new_x)
				else:
					#or the other way around
					create_v_tunnel(prev_y, new_y, prev_x)
					create_h_tunnel(prev_x, new_x, new_y)
					
					
			#append created room to rooms list
			place_objects(new_room)
			rooms.append(new_room)
			num_rooms += 1

#########
# INPUT #
#########
	
def handle_keys():
	global key #necessary only for mouse support
	
	#key = libtcod.console_wait_for_keypress(True)
	
	if key.vk == libtcod.KEY_ENTER and key.lalt:
		#Alt+Enter: toggle fullscreen
		libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
	
	if key.vk == libtcod.KEY_ESCAPE:
		return 'exit'

	elif game_state == 'playing':
		if key.vk == libtcod.KEY_UP or key.vk == libtcod.KEY_KP8:
			player_move_or_attack(0, -1)
			
		elif key.vk == libtcod.KEY_DOWN or key.vk == libtcod.KEY_KP2:
			player_move_or_attack(0, 1)
			
		elif key.vk == libtcod.KEY_LEFT or key.vk == libtcod.KEY_KP4:
			player_move_or_attack(-1, 0)
			
		elif key.vk == libtcod.KEY_RIGHT or key.vk == libtcod.KEY_KP6:
			player_move_or_attack(1, 0)
			
		elif key.vk == libtcod.KEY_KP1:
			player_move_or_attack(-1, 1)
			
		elif key.vk == libtcod.KEY_KP3:
			player_move_or_attack(1, 1)
			
		elif key.vk == libtcod.KEY_KP7:
			player_move_or_attack(-1, -1)
			
		elif key.vk == libtcod.KEY_KP9:
			player_move_or_attack(1, -1)
			
		elif key.vk == libtcod.KEY_KP5: #wait
			fov_recompute = False
			
		elif chr(key.c) == 'g':
			for object in objects: #picks up items in random order
				if object.x == player.x and object.y == player.y and object.item:
					object.item.pick_up()
					break
			else:
				message("Nothing to get.")
			
		else: #everything that doesn't take a turn
			if chr(key.c) == "i":
				chosen_item = inventory_menu("Backpack (press key to use)")
				if chosen_item is not None:
					chosen_item.use()
					return
					
			if chr(key.c) == "?":
				message("[G]et items, use them from your [I]nventory and defeat monsters!")

			return "didnt-take-turn"
		
def player_move_or_attack(dx, dy):
	global fov_recompute
	
	x = player.x + dx
	y = player.y + dy
	
	target = None
	for object in objects:
		if object.x == x and object.y == y and object.blocks:
			target = object
			break
			
	if target is not None:
		if target.fighter:
			player.fighter.attack(target)

		else:
			message("You stumble into the {0}!".format(target.name))
	else:
		player.move(dx, dy)
		fov_recompute = True
		
def menu(header, options, width):
	if len(options) > 26: raise ValueError("Cannot have a menu with more than 26 options.") #TODO: maybe later.
	
	header_height = libtcod.console_get_height_rect(con, 0, 0, width, SCREEN_HEIGHT, header)
	height = len(options) + header_height
	
	window = libtcod.console_new(width, height)
	libtcod.console_set_default_foreground(window, libtcod.white)
	libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)
	
	y = header_height
	letter_index = ord("a") #can be replaced with a list i'll iterate over when i want more positions
	for option_text in options:
		text = "({0}) {1}".format(chr(letter_index), option_text)
		libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
		y += 1
		letter_index += 1
	
	#center and show menu
	x = SCREEN_WIDTH/2 - width/2
	y = SCREEN_HEIGHT/2 - height/2
	libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)
	libtcod.console_flush()
	key = libtcod.console_wait_for_keypress(True)
	index = key.c - ord("a")
	if index >= 0 and index < len(options):
		return index
	else:
		return None

def inventory_menu(header):
	if len(inventory) == 0:
		options = ["EMPTY"]
	else:
		options = [item.name for item in inventory]
	index = menu(header, options, INVENTORY_WIDTH)
	if index is None or len(inventory) == 0:
		return None
	else:
		return inventory[index].item
		
#######
# GUI #
#######
def render_all():
	global fov_map, color_dark_wall, color_lit_wall
	global color_dark_ground, color_lit_ground
	global fov_recompute
	global game_msgs

	#draw all objects
	
	if fov_recompute:
		#recompute fov if needed
		fov_recompute = False
		libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)
	
		#for now only supports two types of terrain: wall and notwall.
		for y in range(MAP_HEIGHT):
			for x in range(MAP_WIDTH):
				visible = libtcod.map_is_in_fov(fov_map, x, y)
				wall = map[x][y].block_sight
				if not visible:
					if map[x][y].explored:
						if wall:
							libtcod.console_put_char_ex(con,x,y,"#", color_dark_wall, libtcod.black)
						else:
							libtcod.console_put_char_ex(con,x,y,".", color_dark_ground, libtcod.black)
				else:
					map[x][y].explored = True
					if wall:
						libtcod.console_put_char_ex(con,x,y,"#", color_lit_wall, libtcod.black)
					else:
						libtcod.console_put_char_ex(con,x,y,".", color_lit_ground, libtcod.black)
	
	#eventually i'm gonna need a better system of drawing priority (several lists?) but this'll do for now
	for object in objects:
		if object != player:
			object.draw()
	player.draw()
	
	libtcod.console_blit(con,0,0,SCREEN_WIDTH,SCREEN_HEIGHT,0,0,0)
	
	#render GUI
	libtcod.console_set_default_background(panel, libtcod.black)
	libtcod.console_clear(panel)
	y = 1
	for (line, color) in game_msgs:
		libtcod.console_set_default_foreground(panel, color)
		libtcod.console_print_ex(panel, MSG_X, y, libtcod.BKGND_NONE, libtcod.LEFT, line)
		y += 1
	render_bar(1, 1, BAR_WIDTH, "HP", player.fighter.hp, player.fighter.max_hp, libtcod.light_red, libtcod.darker_red)
	#render the mouseview hint
	libtcod.console_set_default_foreground(panel, libtcod.light_gray)
	libtcod.console_print_ex(panel, 1, 0, libtcod.BKGND_NONE, libtcod.LEFT, get_names_under_mouse())
	libtcod.console_print_ex(panel, 1, 3, libtcod.BKGND_NONE, libtcod.LEFT, "Turn {0}".format(turncount))
	libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)

def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
	global panel
	#render a bar
	bar_width = int(float(value) / maximum * total_width)
	
	libtcod.console_set_default_background(panel, back_color)
	libtcod.console_rect(panel, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)
	
	libtcod.console_set_default_background(panel, bar_color)
	if bar_width > 0:
		libtcod.console_rect(panel, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)
		
	#text
	libtcod.console_set_default_foreground(panel, libtcod.white)
	libtcod.console_print_ex(panel, x+total_width/2, y, libtcod.BKGND_NONE, libtcod.CENTER, "{0}: {1}/{2}".format(name, value, maximum))
	
def message(new_msg, color = libtcod.white):
	#split if necessary
	new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)
	
	for line in new_msg_lines:
		if len(game_msgs) == MSG_HEIGHT:
			del game_msgs[0]
		game_msgs.append((line, color))
		
def get_names_under_mouse():
	global mouse
	(x, y) = (mouse.cx, mouse.cy)
	
	names = [obj.name for obj in objects
		if obj.x == x and obj.y == y and libtcod.map_is_in_fov(fov_map, obj.x, obj.y)]
	names = ', '.join(names)
	
	return names.capitalize()
		
####################
# SKILLS AND ITEMS #
####################

def cast_heal():
	if player.fighter.hp == player.fighter.max_hp:
		message('You are already at full health.', libtcod.red)
		return 'no-use'
	
	message('Your wounds begin to mend!', libtcod.light_violet)
	player.fighter.heal(10)
	
def cast_lightning():
	target = closest_monster(LIGHTNING_RANGE)
	if target is None:
		message("No enemy is close enough to strike.", libtcod.red)
		return "cancelled"
	else:
		message("A lightning bolt strikes the {0} with a loud thunder for {1} damage!".format(target.name, LIGHTNING_DAMAGE))
		target.fighter.take_damage(LIGHTNING_DAMAGE)
		
def cast_confuse():
	#find closest enemy and confuse it
	monster = closest_monster(CONFUSE_RANGE)
	if monster is None:
		message('No enemy within range to confuse.', libtcod.red)
		return 'cancelled'
	else:
		old_ai = monster.ai
		monster.ai = Confused(old_ai)
		monster.ai.owner = monster
		message("The {0}'s eyes unfocus and glaze over...".format(monster.name), libtcod.light_green)
		
def closest_monster(max_range):
	'''Finds the closest visible enemy up to a maximum range'''
	closest_enemy = None
	closest_dist = max_range + 1
	for object in objects: #can be later changed to exclude friendly NPCs, if any
		if object.fighter and not object == player and libtcod.map_is_in_fov(fov_map, object.x, object.y):
			dist = player.distance_to(object)
			if dist < closest_dist:
				closest_enemy = object
				closest_dist = dist
	return closest_enemy
	
##################
# INITIALIZATION #
##################
		
libtcod.console_set_custom_font('resource/celtic_garamond_10x10_gs_tc.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'Testowy Rogalik', False)
libtcod.sys_set_fps(LIMIT_FPS)
con = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)
panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)

game_state = 'playing'
player_action = None

player = Object(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, '@', 'player', libtcod.white, True, fighter = Fighter(hp=30, defence=2, power=5, death_function=player_death))
objects = [player]
inventory = [] #TODO: maybe eventually an inventory for every actor? bound to Fighter???
game_msgs = []

make_map()

fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
for y in range(MAP_HEIGHT):
	for x in range(MAP_WIDTH):
		libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)
fov_recompute = True

# MOUSE SUPPORT
mouse = libtcod.Mouse()
key = libtcod.Key()

message('Welcome to the first and only floor of the Dungeon of Certain Doom.', libtcod.white)
turncount = 0
# MAIN LOOP
while not libtcod.console_is_window_closed():
	libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE,key,mouse)
	render_all()
	
	libtcod.console_flush()
	
	#clear objects
	for object in objects:
		object.clear()
	
	#handle keys and exit if requested
	player_action = handle_keys()
	
	if player_action == 'exit':
		break
	
	#handling a turn
	if game_state == 'playing' and player_action != 'didnt-take-turn':
		for object in objects:
			if object.ai:
				object.ai.take_turn()
		turncount += 1
	