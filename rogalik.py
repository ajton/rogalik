import libtcodpy as libtcod
from math import sqrt

#window size
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
DEBUG_ON = True

FOV_ALGO = 0
FOV_LIGHT_WALLS = True
TORCH_RADIUS = 10

color_dark_wall = libtcod.Color(50,50,50)
color_lit_wall = libtcod.Color(110,110,110)
color_dark_ground = libtcod.Color(50,50,50)
color_lit_ground = libtcod.Color(180,180,180)

#dungeon specs
ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30
MAX_ROOM_MONSTERS = 3

class Object:
	global fov_map
	#a generic object: player/monster/item/stairs/whatever.
	#always represented by a character.
	def __init__(self, x, y, char, name, color, blocks=False, fighter=None, ai=None):
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
		
	def clear(self):
		if self.known:
			libtcod.console_put_char(con, self.x, self.y, '.', libtcod.BKGND_NONE)

###################
# FIGHTER CLASSES #
###################
			
class Fighter:
	def __init__(self, hp, defence, power):
		self.max_hp = hp
		self.hp = hp
		self.defence = defence
		self.power = power
		
##############
# AI CLASSES #
##############
class BasicMelee:
	def take_turn(self):
		#turn of a basic monster. they run on ostrich logic, see player only if player sees them
		monster = self.owner
		if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
			if monster.distance_to(player) >= 2:
				monster.move_towards(player.x, player.y)
			elif player.fighter.hp > 0:
				print 'The attack of the ' + monster.name + ' bounces off your head!'
		
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
	
	for i in range(num_monsters):
		x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
		y = libtcod.random_get_int(0, room.y1+1, room.y2-1)
		
		if not is_blocked(x, y):
		#create monster if tile is free
			if libtcod.random_get_int(0, 0, 100) < 80:
				#kobold
				monster = Object(x, y, 'k', 'kobold', libtcod.dark_blue, True, fighter=Fighter(10,0,3), ai=BasicMelee())
			else:
				#dragon
				monster = Object(x, y, 'D', 'dragon', libtcod.darker_green, True, fighter=Fighter(16,1,4), ai=BasicMelee())
		
			objects.append(monster)
		
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
MAP_HEIGHT = 45

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

def render_all():
	global fov_map, color_dark_wall, color_lit_wall
	global color_dark_ground, color_lit_ground
	global fov_recompute

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
							libtcod.console_put_char_ex(con,x,y,'#', color_dark_wall, libtcod.black)
						else:
							libtcod.console_put_char_ex(con,x,y,'.', color_dark_ground, libtcod.black)
				else:
					map[x][y].explored = True
					if wall:
						libtcod.console_put_char_ex(con,x,y,'#', color_lit_wall, libtcod.black)
					else:
						libtcod.console_put_char_ex(con,x,y,'.', color_lit_ground, libtcod.black)
	
	for object in objects:
		object.draw()
	
	libtcod.console_blit(con,0,0,SCREEN_WIDTH,SCREEN_HEIGHT,0,0,0)
	
def handle_keys():
	global playerx, playery
	global fov_recompute
	
	key = libtcod.console_wait_for_keypress(True)
		
	if key.vk == libtcod.KEY_ESCAPE:
		return 'exit'

	if game_state == 'playing':
		if libtcod.console_is_key_pressed(libtcod.KEY_UP) or libtcod.console_is_key_pressed(libtcod.KEY_KP8):
			player_move_or_attack(0, -1)
			
		elif libtcod.console_is_key_pressed(libtcod.KEY_DOWN) or libtcod.console_is_key_pressed(libtcod.KEY_KP2):
			player_move_or_attack(0, 1)
			
		elif libtcod.console_is_key_pressed(libtcod.KEY_LEFT) or libtcod.console_is_key_pressed(libtcod.KEY_KP4):
			player_move_or_attack(-1, 0)
			
		elif libtcod.console_is_key_pressed(libtcod.KEY_RIGHT) or libtcod.console_is_key_pressed(libtcod.KEY_KP6):
			player_move_or_attack(1, 0)
		
		elif libtcod.console_is_key_pressed(libtcod.KEY_KP1):
			player_move_or_attack(-1, 1)
			
		elif libtcod.console_is_key_pressed(libtcod.KEY_KP3):
			player_move_or_attack(1, 1)
			
		elif libtcod.console_is_key_pressed(libtcod.KEY_KP7):
			player_move_or_attack(-1, -1)
			
		elif libtcod.console_is_key_pressed(libtcod.KEY_KP9):
			player_move_or_attack(1, -1)
			
		elif libtcod.console_is_key_pressed(libtcod.KEY_KP5): #wait
			fov_recompute = False
			
		else:
			return 'didnt-take-turn'
			
def player_move_or_attack(dx, dy):
	global fov_recompute
	
	x = player.x + dx
	y = player.y + dy
	
	target = None
	for object in objects:
		if object.x == x and object.y == y:
			target = object
			break
			
	if target is not None:
		print 'You punch the ' + target.name + ' ineffectually.'
	else:
		player.move(dx, dy)
		fov_recompute = True
		
# INITIALIZATION
		
libtcod.console_set_custom_font('celtic_garamond_10x10_gs_tc.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'Testowy Rogalik', False)
con = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)

game_state = 'playing'
player_action = None

player = Object(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, '@', 'player', libtcod.white, True, fighter = Fighter(hp=30, defence=2, power=5))
objects = [player]

make_map()

fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
for y in range(MAP_HEIGHT):
	for x in range(MAP_WIDTH):
		libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)
fov_recompute = True

# MAIN LOOP
while not libtcod.console_is_window_closed():
	render_all()
	
	libtcod.console_flush()
	
	#clear objects
	for object in objects:
		object.clear()
	
	#handle keys and exit if requested
	player_action = handle_keys()
	
	if game_state == 'playing' and player_action != 'didnt-take-turn':
		for object in objects:
			if object.ai:
				object.ai.take_turn()
	
	
	
	if player_action == 'exit':
		break