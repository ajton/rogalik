import libtcodpy as libtcod
from math import sqrt
import textwrap

DIRECTIONS = {
	libtcod.KEY_UP:		(0, -1),
	libtcod.KEY_DOWN:	(0, 1),
	libtcod.KEY_LEFT:	(-1, 0),
	libtcod.KEY_RIGHT:	(1, 0),
	libtcod.KEY_KP1:	(-1, 1),
	libtcod.KEY_KP2:	(0, 1),
	libtcod.KEY_KP3:	(1, 1),
	libtcod.KEY_KP4:	(-1, 0),
	libtcod.KEY_KP6:	(1, 0),
	libtcod.KEY_KP7:	(-1, -1),
	libtcod.KEY_KP8:	(0, -1),
	libtcod.KEY_KP9:	(1, -1)
	}

#window size
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
DEBUG_ON = False

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
FIREBALL_DAMAGE = 12
FIREBALL_RADIUS = 3
FIREBALL_RANGE = 5

class Object:
	'''a generic object: player/monster/item/stairs/whatever. always represented by a character.'''

	global fov_map
	def __init__(self, x, y, char='@', name='OBJECT', color=libtcod.red, blocks=False, fighter=None, ai=None, item=None, interact=None):
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
		
	def move(self, dx, dy, ghost = False, leash = 0):
		#move by a given amount. returns a bool for messages and checks
		nx = self.x+dx
		ny = self.y+dy
		
		if leash > 0 and distance(player.x, player.y, nx, ny) > leash - 1:
			return False
		
		if nx < MAP_WIDTH and ny < MAP_HEIGHT and nx >= 0 and ny >= 0:
			if not is_blocked(nx, ny) or ghost:
				self.x = nx
				self.y = ny
				return True
		
		return False
		
	def place(self, x, y):
		#move without any checks
		self.x = x
		self.y = y

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
			libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_SET)
	
	def send_to_back(self):
		#make this object drawn first, so it's covered by any other object
		global objects
		objects.remove(self)
		objects.insert(0, self)
	
	def clear(self):
		if self.known:
			libtcod.console_put_char(con, self.x, self.y, map[self.x][self.y].symbol, libtcod.BKGND_NONE)
		

#####################
# OBJECT SUBCLASSES #
#####################

class Fighter:
	#this is a widget with all the functionality for fighting.
	#it includes stats (see init), functions for taking damage and attacking.
	#dying and possibly skills will be relegated to outside functions.

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
			message('{0} attacks {1} ineffectually.'.format(self.owner.name.capitalize(), target.name))
			
			
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
			if self.use_function() != False:
				inventory.remove(self.owner)
				
	def drop(self):
		#add item to map at player's coords and remove from inventory
		objects.append(self.owner)
		inventory.remove(self.owner)
		self.owner.place(player.x, player.y)
		message("Dropped a {0}.".format(self.owner.name), libtcod.yellow)
				
class Interact:
	#A subtype for implementing usable objects, such as doors or NPCs. If use_command is None, it activates when the player moves into it.
	#TODO: some actual NPCs that take advantage of this; doors were eventually implemented in a different way
	def __init__(self, use_command=None, use_action=None):
		self.use_command = use_command
		self.use_action = use_action
		
	def activate(self):
		self.use_action

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
			#print a message if move fails
			if not self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1)):
				message('The {0} stumbles in its confusion!'.format(self.owner.name), libtcod.light_grey)
			self.num_turns -= 1
		else:
			self.owner.ai = self.old_ai
			message('The {0} is no longer confused!'.format(self.owner.name), libtcod.red)

################
# MAP HANDLING #
################
class Tile:
	#a tile of the map and its properties
	
	def __init__(self, blocked, block_sight = None, symbol = '&', usable=None):
		#the default state is just a normal wall.
		self.blocked = blocked
		if block_sight == None: block_sight = blocked
		self.block_sight = block_sight
		self.explored = False
		self.symbol = symbol
		self.usable = usable
		if self.usable:
			self.usable.owner = self

class Usable:
	def __init__(self, use_function):
		self.use_function = use_function
		
	def activate(self):
		self.use_function(self.owner)
		
def open_door(door):
	#a creak for flavour
	if libtcod.random_get_int(0, 1, 4) > 3:
		message('The door creaks loudly!', libtcod.light_grey)
	door.symbol = '\''
	door.block_sight = False
	door.blocked = False
	door.usable = None
	update_fovmap()

class Rect:
	#a rectangle on the map.
	def __init__(self, x, y, w, h):
		self.x1 = x
		self.y1 = y
		self.x2 = x+w
		self.y2 = y+h
		
	def __contains__(self, (x, y)):
		#probably overkill but good training
		if x > self.x1 and x < self.x2 and y > self.y1 and y < self.y2:
			return True
		else:
			return False
		
	def center(self):
		center_x = (self.x1 + self.x2) / 2
		center_y = (self.y1 + self.y2) / 2
		return (center_x, center_y)
		
	def intersect(self, other):
		#returns true if this rectangle intersects another
		return (self.x1 <= other.x2 and self.x2 >= other.x1 and self.y1 <= other.y2 and self.y2 >= other.y1)
		
	def borders(self):
		#for placing doors and custom walls!
		border = []
		for x in range(self.x1, self.x2+1):
			for y in range(self.y1, self.y2+1):
				if (x, y) not in self:
					border.append((x,y))
		return border
		
def create_room(room, doors = False):
	global map
	
	for x in range(room.x1+1, room.x2):
		for y in range(room.y1+1, room.y2):
			map[x][y].blocked = False
			map[x][y].block_sight = False
			map[x][y].symbol = '.'

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
			if dice < 60:
				#potion
				item = Object(x, y, "!", "healing potion", libtcod.flame, item=Item(cast_heal))
			elif dice < 60+10:
				#scroll of lightning bolt
				item = Object(x, y, "?", "scroll of lightning bolt", libtcod.light_yellow, item=Item(cast_lightning))
			elif dice < 60+20:
				#scroll of confuse monster
				item = Object(x, y, "?", "scroll of confuse monster", libtcod.violet, item=Item(cast_confuse))
			else:
				#scroll of fireball
				item = Object(x, y, "?", "scroll of fireball", libtcod.red, item=Item(cast_fireball))
			objects.append(item)
			item.send_to_back()

def create_h_tunnel(x1, x2, y):
	global map
	#horizontal tunnel
	
	for x in range(min(x1, x2), max(x1, x2)+1):
		map[x][y].blocked = False
		map[x][y].block_sight = False
		map[x][y].symbol = '.'

def create_v_tunnel(y1, y2, x):
	global map
	#vertical tunnel
	for y in range(min(y1, y2), max(y1, y2)+1):
		map[x][y].blocked = False
		map[x][y].block_sight = False
		map[x][y].symbol = '.'

	
def connect_rooms(room1, room2):
	'''Take two rooms and dig a corridor between them.'''
	(prev_x, prev_y) = room1.center()
	(new_x, new_y) = room2.center()
	
	if libtcod.random_get_int(0,0,1) == 1:
		#flip a coin: either create h tunnel first and v second
		create_h_tunnel(prev_x, new_x, prev_y)
		create_v_tunnel(prev_y, new_y, new_x)
	else:
		#or the other way around
		create_v_tunnel(prev_y, new_y, prev_x)
		create_h_tunnel(prev_x, new_x, new_y)

def is_blocked(x, y):
	#check if given tile is blocked
	#test for impassable terrain
	if x >= MAP_WIDTH or y >= MAP_HEIGHT:
		return True
		
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
rooms = []

def make_map():
	global map, player
	
	#fill map with unblocked tiles
	map = [[ Tile(True) for y in range(MAP_HEIGHT)] for x in range(MAP_WIDTH)]
	
	
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
				room_no.send_to_back()
			
			if num_rooms == 0:
				#the first room always contains the player
				#player = Object(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, '@', 'player', libtcod.white, True, fighter = Fighter(hp=30, defence=2, power=5, death_function=player_death))
				#objects = [player]
				player.place(new_x, new_y)
				
			else:
				#connect all rooms after the first to the previous
				connect_rooms(rooms[num_rooms-1], new_room)
				
			#append created room to rooms list
			place_objects(new_room)
			rooms.append(new_room)
			num_rooms += 1
	
	#create doors
	for room in rooms:
		entrances = []
		for (x, y) in room.borders():
			if not map[x][y].blocked: entrances.append((x, y))
		if len(entrances) < 5:
		#to prevent having entire walls of doors where corridors and rooms touch
			for (x, y) in entrances:
				door = Usable(open_door)
				map[x][y] = Tile(True, True, '+', door)

#########
# INPUT #
#########
def targeting(size=1, maxrange=None):
	global player
	cursor = Object(player.x, player.y, ' ', 'cursor')
	
	while not libtcod.console_is_window_closed():
		draw_target(cursor, size, maxrange)
		render_all()
		libtcod.console_flush()
		clear_target(cursor, maxrange, size)
		
		libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE,key,mouse)
		input = key.vk
		if input in DIRECTIONS:
			dxy = DIRECTIONS[input]
			cursor.move(dxy[0], dxy[1], True, maxrange)
			
		elif input == libtcod.KEY_ESCAPE:
			return None
		elif input == libtcod.KEY_ENTER:
			clear_all()
			return Area(cursor.x, cursor.y, size)
	
class Area:
	#Container for specific points of the map. Can be used to retrieve their coordinates and contained objects.
	global objects
	def __init__(self, x, y, size=1):
		self.x = x
		self.y = y
		self.size = size
		self.caught = []
		for object in objects:
			if (object.x, object.y) in circle(self.x, self.y, self.size):
				self.caught.append(object)

def draw_target(cursor, size=1, maxrange=None):
	global hint
	#draw reticle of stated size
	if maxrange > 0:
		for tile in circle(player.x, player.y, maxrange):
			libtcod.console_set_char_background(con, tile[0], tile[1], libtcod.darkest_red, flag=libtcod.BKGND_LIGHTEN)
	
	for tile in circle(cursor.x, cursor.y, size):
		libtcod.console_set_char_background(con, tile[0], tile[1], libtcod.darkest_yellow, flag=libtcod.BKGND_ADD)
		
	hint = get_names(cursor.x, cursor.y)
	
			
def clear_target(cursor, crange, size):
	if crange > 0:
		#clear the highlighted range
		for tile in circle(player.x, player.y, crange):
			libtcod.console_set_char_background(con, tile[0], tile[1], libtcod.black, flag=libtcod.BKGND_SET)
	for tile in circle(cursor.x, cursor.y, size):
		#clear the reticle itself
		libtcod.console_set_char_background(con, tile[0], tile[1], libtcod.black, flag=libtcod.BKGND_SET)


def handle_keys():
	global key #necessary only for mouse support
	global game_state
	
	#key = libtcod.console_wait_for_keypress(True)
	input = key.vk
	if input == libtcod.KEY_ENTER and key.lalt:
		#Alt+Enter: toggle fullscreen
		libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
		
	elif input == libtcod.KEY_ESCAPE:
		return 'exit'
	
	elif game_state == 'playing':
		if input in DIRECTIONS:
			dxy = DIRECTIONS[input]
			player_move_or_attack(dxy[0], dxy[1])
		
		elif input == libtcod.KEY_KP5: #wait
			fov_recompute = False
			
		elif chr(key.c) == 'g':
			for object in objects: #picks up items in random order
				if object.x == player.x and object.y == player.y and object.item:
					object.item.pick_up()
					break
			else:
				message("Nothing to get.")
				
		elif chr(key.c) == 'w': #WHERE AM I
			message(str((player.x, player.y)))
			room_id = None
			for index, room in enumerate(rooms):
				if (player.x, player.y) in room:
					room_id = index+1
					message("You are in room {0}.".format(room_id))
					break
			if room_id == None:
				message("You are not anywhere in particular.")
				
		elif chr(key.c) == 'f': #FIREBALL
			if not cast_fireball(): return 'didnt-take-turn'
			
		else: #everything that doesn't take a turn but happens in player turn
			if chr(key.c) == "i": #INVENTORY
				chosen_item = inventory_menu("Backpack (press key to use)")
				if chosen_item is not None:
					chosen_item.use()
					return
					
			if chr(key.c) == 'x': #EXAMINE
				act_examine()
					
			if chr(key.c) == "?": #HELP
				message("[G]et items, use them from your [I]nventory and defeat monsters!")
				
			return "didnt-take-turn"

def resume_game():
	global game_state
	
	if game_state != 'dead':
		game_state = 'playing'
			
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
			#for theoretical nonfighter objects
			message("You stumble into the {0}!".format(target.name))
	else:
		if not map[x][y].usable:
			player.move(dx, dy)
		else:
			map[x][y].usable.activate()
		fov_recompute = True

def menu(header, options, width):
	if len(options) > 26: raise ValueError("Cannot have a menu with more than 26 options.") #TODO: expand inventory.
	
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
	render_map()
	render_gui()

def render_map():
	global fov_map, color_dark_wall, color_lit_wall
	global color_dark_ground, color_lit_ground
	global fov_recompute

	#draw all objects	
	if fov_recompute:
		#recompute fov if needed
		fov_recompute = False
		libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)
	
		#for now only supports two types of terrain: wall and notwall. now also door!
		for y in range(MAP_HEIGHT):
			for x in range(MAP_WIDTH):
				visible = libtcod.map_is_in_fov(fov_map, x, y)
				wall = map[x][y].block_sight
				symbol = map[x][y].symbol
				if not visible:
					if map[x][y].explored:
						if wall:
							libtcod.console_put_char_ex(con,x,y,symbol, color_dark_wall, libtcod.black)
						else:
							libtcod.console_put_char_ex(con,x,y,symbol, color_dark_ground, libtcod.black)
				else:
					map[x][y].explored = True
					if wall:
						libtcod.console_put_char_ex(con,x,y,symbol, color_lit_wall, libtcod.black)
					else:
						libtcod.console_put_char_ex(con,x,y,symbol, color_lit_ground, libtcod.black)
	
	#eventually i'm gonna need a better system of drawing priority (several lists?) but this'll do for now
	for object in objects:
		if object != player:
			object.draw()
	player.draw()
	
	libtcod.console_blit(con,0,0,SCREEN_WIDTH,SCREEN_HEIGHT,0,0,0)

def render_gui():
	#render GUI
	global game_msgs, hint
	libtcod.console_set_default_background(panel, libtcod.black)
	libtcod.console_clear(panel)
	y = 1
	
	for (line, color) in game_msgs:
		libtcod.console_set_default_foreground(panel, color)
		libtcod.console_print_ex(panel, MSG_X, y, libtcod.BKGND_NONE, libtcod.LEFT, line)
		y += 1
	
	render_bar(1, 1, BAR_WIDTH, "HP", player.fighter.hp, player.fighter.max_hp, libtcod.light_red, libtcod.darker_red)
	#render the mouseview hint
	if hint == "":
		hint = get_names_under_mouse().capitalize()
		
	libtcod.console_set_default_foreground(panel, libtcod.light_gray)
	libtcod.console_print_ex(panel, 1, 0, libtcod.BKGND_NONE, libtcod.LEFT, hint)
	
	#render turncount
	libtcod.console_print_ex(panel, 1, 3, libtcod.BKGND_NONE, libtcod.LEFT, "Turn {0}".format(turncount))
	libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)
	
def clear_all():
	libtcod.console_set_default_background(panel, libtcod.black)
	libtcod.console_clear(panel)
	#clear objects
	for object in objects:
		object.clear()

def update_fovmap():
	'''Call whenever a tile changes its block_sight status.'''
	global fov_map
	
	for y in range(MAP_HEIGHT):
		for x in range(MAP_WIDTH):
			libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)

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
		
def get_names(x, y):
	names = [obj.name for obj in objects
		if obj.x == x and obj.y == y and libtcod.map_is_in_fov(fov_map, obj.x, obj.y)]
	names = ', '.join(names)
	
	return names
		
		
def get_names_under_mouse():
	global mouse
	return get_names(mouse.cx, mouse.cy)
	
		
####################
# SKILLS AND ITEMS #
####################
def act_examine():
	target = targeting(1)
	if target == None or len(target.caught) == 0:	
		message('Nothing interesting.')
	else:
		for object in target.caught:
			name = get_names(object.x, object.y)
		message('Examined the {2} at {0}, {1}.'.format(target.x, target.y, name))

def cast_heal():
	if player.fighter.hp == player.fighter.max_hp:
		message('You are already at full health.', libtcod.red)
		return 'no-use'
	
	message('Your wounds begin to mend!', libtcod.light_violet)
	player.fighter.heal(10)
	
def cast_lightning():
	monster = closest_monster(LIGHTNING_RANGE)
	if monster is None:
		message("No enemy is close enough to strike.", libtcod.red)
		return False
	else:
		message("A lightning bolt strikes the {0} with a loud thunder for {1} damage!".format(monster.name, LIGHTNING_DAMAGE))
		monster.fighter.take_damage(LIGHTNING_DAMAGE)
		return True
		
def cast_confuse():
	#find closest enemy and confuse it
	monster = closest_monster(CONFUSE_RANGE)
	if monster is None:
		message('No enemy within range to confuse.', libtcod.red)
		return False
	else:
		old_ai = monster.ai
		monster.ai = Confused(old_ai)
		monster.ai.owner = monster
		message("The {0}'s eyes unfocus and glaze over...".format(monster.name), libtcod.light_green)
		return True

def cast_fireball():
	message("What to blow up?")
	aoe = targeting(FIREBALL_RADIUS, FIREBALL_RANGE)
	if aoe == None:
		return False
	else:
		if len(aoe.caught) == 0:
			message("That would be a waste.")
			return False
		else:
			succ_hits = []
			for object in aoe.caught:
				if object.fighter:
					succ_hits.append(object)
			for victim in succ_hits:
				if victim.known:
					message("Your fireball strikes the {0} for {1} damage!!".format(victim.name, FIREBALL_DAMAGE))
				else:
					message("You hear a yelp!")
				victim.fighter.take_damage(FIREBALL_DAMAGE)
		return True

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

def distance(x, y, x2, y2):
	return sqrt((x - x2) ** 2 + (y - y2) ** 2)
	
def circle(x, y, radius):
	'''Returns a list of coordinates within a circle of a certain radius from the center point.'''
	cornerx = x - radius
	cornery = y - radius
	coords = []
	
	for dx in range(cornerx, cornerx + 2*radius):
		for dy in range(cornery, cornery + 2*radius):
			if distance(x, y, dx, dy) <= (radius - 1):
				coords.append((dx, dy))
		
	return coords
	
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

#player = Object(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, '@', 'player', libtcod.white, True, fighter = Fighter(hp=30, defence=2, power=5, death_function=player_death))

inventory = [] #TODO: maybe eventually an inventory for every actor? bound to Fighter???
game_msgs = []
hint = ""
player = Object(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, '@', 'player', libtcod.white, True, fighter = Fighter(hp=30, defence=2, power=5, death_function=player_death))
objects = [player]
make_map()

fov_recompute = True

fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
update_fovmap()

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
	clear_all()
	
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
