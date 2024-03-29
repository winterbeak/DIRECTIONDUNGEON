################################################################################
###                            DIRECTIONDUNGEON!                             ###
################################################################################

# sorry for the code anarchy but when I started this I didn't
# even know what an object was


################################################################################
###                    STUFF THAT IS ONLY LOADED ONCE                        ###
################################################################################

import os
import sys

import math
import random

import copy

import pygame



##################################
### CONSTANTS AND WINDOW SETUP ###
##################################

### GRAPHICAL CONSTANTS ###
# INITIAL WINDOW SETUP
os.environ['SDL_VIDEO_CENTERED'] = '1'           # centers window

pygame.mixer.init(22050, -16, 16, 64)   # NOTE TO FIX: SOMETIMES SOUNDS CUT OFF EVEN WITH 32 CHANNELS
pygame.mixer.set_num_channels(16)
pygame.init()

icon = pygame.image.load("images\\icon1.png")
pygame.display.set_caption('DIRECTIONDUNGEON!')  # gives window a title
pygame.display.set_icon(icon)

# PIXEL SIZE CONSTANTS
mult = 8            # pixel multiplier

TILE = 4 * mult     # size in pixels of a tile
SIDE = 2 * mult     # size in pixels of the side of a tile
MARG = 2 * mult     # size in pixels of the margin between dungeons

WIDTH  = 5          # width  in tiles of a dungeon
HEIGHT = 5          # height in tiles of a dungeon
DUNGW = TILE*WIDTH  # width  in pixels of a dungeon
DUNGH = TILE*HEIGHT # height in pixels of a dungeon

# AFTERWARDS WINDOW SETUP
# the size of the screen, based on how things are laid out
SCREENLENGTH = DUNGH*3 + MARG*4 + SIDE

SCREENSIZE = (SCREENLENGTH, SCREENLENGTH)

# initializes the display so that sprites can be loaded
postDisplay = pygame.display.set_mode(SCREENSIZE)

plateLockColor = (238, 0, 0)



### GAMEPLAY CONSTANTS ###
# DIRECTIONS
LEFT = 0
UP = 1
RIGHT = 2
DOWN = 3

# TILE TYPES
VOID = 0
EMPTY = 1
WALL = 2
WALLSIDE = 3 # only used in tilesheets, not used in level generation
GOAL = 4
SWIRL = 5
BOX = 6
BOXSIDE = 7
PLATE = 8
GOALLOCK = 9

# DUNGEON POSITIONS
origDungX = [MARG, DUNGW + MARG*2, DUNGW*2 + MARG*3, DUNGW + MARG*2]
origDungY = [DUNGH + MARG*2, MARG, DUNGH + MARG*2, DUNGH*2 + MARG*3]

# centers dungeons (because of sides, height of dungeon is more than width)
for dung in range(4):
    origDungX[dung] += SIDE / 2







###############
### SPRITES ###
###############

### LOADS SPRITES ###
def loadSprite(path, mult):
    sprite = pygame.image.load(path) # load sprite

    w = sprite.get_width()           # resize sprite
    h = sprite.get_height()
    sprite = pygame.transform.scale(sprite, (w * mult, h * mult))

    sprite.convert()                 # convert sprite

    sprite.set_colorkey((0, 255, 0)) # transparentize sprite

    return sprite


### TILESHEETS ###
# VAR does not mean VARIABLE, it means VARIATIONS
class Tilesheet:
    def __init__(self, path, mult, varCount):
        self.surface = loadSprite(path, mult)

        # a tuple that stores the amount of variations for each tileType
        self.varCount = varCount


    # draws a tile based on its tileType and variant
    def drawTile(self, surf, pos, tile, variant):
        if tile == WALLSIDE or tile == BOXSIDE:
            height = SIDE
        else:
            height = TILE

        # cuts out the tile from the tilesheet and draws it
        tileRect = ((tile - 1)*TILE, variant*height, TILE, height)
        surf.blit(self.surface, pos, tileRect)

# a test tilesheet.  multiple can be made
TESTSHEET = Tilesheet(os.path.join("images", "testSheet.png"), mult, (0, 1, 3, 3, 1, 1, 4, 4, 1, 1))
# intro levels.
INTROSHEET = Tilesheet(os.path.join("images", "00 introSheet.png"), mult, (0, 1, 1, 1, 1, 1, 4, 4, 1, 1))
DIRECTIONSHEET = Tilesheet(os.path.join("images", "01 directionSheet.png"), mult, (0, 4, 1, 1, 1, 1, 4, 4, 1, 1))
SWIRLSHEET = Tilesheet(os.path.join("images", "02 swirlSheet.png"), mult, (0, 3, 4, 4, 1, 3, 4, 4, 1, 1))
DIZZYSHEET = Tilesheet(os.path.join("images", "03 dizzySheet.png"), mult, (0, 3, 3, 3, 1, 3, 4, 4, 1, 1))
BOXSHEET = Tilesheet(os.path.join("images", "04 boxSheet.png"), mult, (0, 3, 4, 4, 1, 3, 4, 4, 1, 1))
PLATESHEET = Tilesheet(os.path.join("images", "05 plateSheet.png"), mult, (0, 6, 6, 6, 1, 6, 6, 4, 1, 1))
ENDSHEET = Tilesheet(os.path.join("images", "03 scrappedSheet.png"), mult, (0, 3, 4, 4, 1, 3, 1, 1, 1, 1, 1))

##################
### ANIMATIONS ###
##################

animQueue = []    # a queue that plays animations in order
animSameTime = [] # a queue for animations that play at the same time

### THE ANIMATION CLASS ###
# THERE ARE DIFFERENT TYPES OF ANIMATIONS
SPRITE     = 1 # based off of sprites rather than values
COUNTER    = 2 # counts by ones
LINEAR     = 3 # counts by a certain value
QUADRATIC  = 4 # counts by a changing value (slow then speeds up)
RQUADRATIC = 5 # counts by a changing value, reversed (fast then slows down)

class Animation:

    # I USE "args" BECAUSE SPRITE AND VALUE ANIMS TAKE DIFFERENT ARGUMENTS
    def __init__ (self, lastFrame, kind, arg0 = None, arg1 = None,
                                         arg2 = None, arg3 = None, arg4 = ()):
        #      kind: I couldn't use "type" because Python
        #     frame: counts up the frame number of the animation
        # lastFrame: the last frame number of the animation
        #     value: stores the value of the animation
        # peakValue: the highest/lowest point the value will reach
        #      tied: references any animations that play at the same time
        self.kind = kind

        self.frame = 0
        self.lastFrame = lastFrame


        ### SPRITE-BASED ANIMATION ###
        if kind == SPRITE:
            # DEFINE WHAT THE ARGUMENTS MEAN
            filePath  = arg0
            width     = arg1
            height    = arg2
            mult      = arg3
            self.tied = arg4

            # WIDTH AND HEIGHT USED TO "CUT OUT" CERTAIN FRAMES
            self.width = width * mult
            self.height = height * mult

            # STORES EVERY FRAME ON A SINGLE SURFACE
            self.surface = loadSprite(filePath, mult)


        ### VALUE-BASED ANIMATION ###
        else:
            # DEFINE WHAT THE ARGUMENTS MEAN
            peakValue = arg0
            if arg1:  # only defines tied animations when arg1 exists
                self.tied = arg1
            else:
                self.tied = ()

            # CREATES COUNTERS BASED ON THE TYPE OF ANIMATION
            if kind == LINEAR:
                self.lastValue = peakValue
                self.value = 0
                self.DIFF = peakValue / lastFrame

            elif kind == QUADRATIC or kind == RQUADRATIC:
                # wow look math, wow look parabolas
                h = lastFrame
                k = peakValue
                a = k / h**2
                self.value = 0
                self.DIFF2 = a * 2

                if kind == QUADRATIC:
                    self.lastValue = peakValue
                    self.diff1 = a

                elif kind == RQUADRATIC:
                    # goes through the parabola and records the pre-vertex value
                    # it's inefficient but I spent forever trying something else
                    diff1 = a

                    for x in range (lastFrame - 1):
                        diff1 += self.DIFF2

                    self.firstDiff1 = diff1
                    self.diff1 = diff1


    ### FUNCTIONS ###
    # DRAWS A SPECIFIC FRAME, BY CUTTING IT OUT FROM THE SURFACE (sprite only)
    def blitFrame(self, dest, position, frameNum = -1):
        if frameNum == -1:
            frameNum = self.frame

        frameRect = (0, self.height * frameNum, self.width, self.height)
        dest.blit(self.surface, position, frameRect)


    # ADVANCES THE FRAME
    def nextFrame(self):
        self.frame += 1

        if self.kind == LINEAR:
            self.value += self.DIFF

        elif self.kind == QUADRATIC:
            self.value += self.diff1
            self.diff1 += self.DIFF2

        elif self.kind == RQUADRATIC:
            self.value += self.diff1
            self.diff1 -= self.DIFF2

        # also advances each tied animation
        for anim in self.tied:
            anim.nextFrame()


    # RESETS ANIMATION BACK TO FRAME 0
    def resetAnim(self):
        self.frame = 0

        # self.value doesn't exist on SPRITES
        if self.kind != SPRITE:
            self.value = 0

        if self.kind == QUADRATIC:
            self.diff1 = self.DIFF2 / 2

        elif self.kind == RQUADRATIC:
            self.diff1 = self.firstDiff1

        # also resets all tied animations
        for anim in self.tied:
            anim.resetAnim()

# PLATE LOCKS
animLockBox = Animation(7, RQUADRATIC, mult)
animUnlockBox = Animation(7, LINEAR, mult)
animGoalUnlock = Animation(7, RQUADRATIC, SIDE)
animGoalLock = Animation(7, RQUADRATIC, SIDE)


### PLAYER ANIMATIONS ###

# sliding boxes (should actually be 6 frames but that breaks it kinda
animBoxSlide = Animation(8, LINEAR, TILE)
# you can change this to RQUADRATIC if you think it looks better

# creates and loads all the ghost/player animations from file
directionStrings = ["Left", "Up", "Right", "Down"]
playMovement = []
ghostMovement = []
for direction in directionStrings:
    path =  "images\\play" + direction + ".png"

    # creates ghost animation, equal to the player animation except transparent
    tempGhostAnim = Animation(6, SPRITE, path, 12, 14, mult)
    tempGhostAnim.surface.set_alpha(75)
    ghostMovement.append(tempGhostAnim)

    # the ghost animation is then tied to the player animation
    tempPlayAnim = Animation(6, SPRITE, path, 12, 14, mult, [tempGhostAnim, animBoxSlide, animUnlockBox])
    playMovement.append(tempPlayAnim)

# idle doesn't have to be animation, but it just makes things easier
playIdle = Animation(0, SPRITE, "images\\playIdle.png",  12, 14, mult)
ghostIdle = Animation(0, SPRITE, "images\\playIdle.png",  12, 14, mult)
ghostIdle.surface.set_alpha(75)
playAnim = playIdle
ghostAnim = ghostIdle


### LEVEL ANIMATIONS ###
animRotate = Animation(18, RQUADRATIC, 90)
ROTATERADIUS = DUNGW + MARG
ROTATEMIDX = DUNGW + MARG*2 + SIDE // 2
ROTATEMIDY = DUNGH + MARG*2

animPlayDrop = Animation(6, QUADRATIC, SIDE)



# these two animations are "tied" together and will play at the same time
animNexLvlUp = Animation(34, RQUADRATIC, -SIDE)
animCurLvlUp = Animation(34, QUADRATIC, -SCREENLENGTH, [animNexLvlUp])

LEVELSDOWN = 8  # how many levels below current level to show
SHADOWINTERVAL = 255 / LEVELSDOWN
NEXTSHADOWINTERVAL = SHADOWINTERVAL / animNexLvlUp.lastFrame



### MISC GRAPHICAL STUFF ###
# CREATES A NEW LAYER, WITH COLORKEY TRANSPARENCY
def newSurf(dimensions):
    layer = pygame.Surface(dimensions)
    layer.set_colorkey((0, 255, 0))
    layer.fill((0, 255, 0))
    return layer


# SURFACE WHERE EACH DUNGEON IS DRAWN TO
curDungs = newSurf((DUNGW * 4, DUNGH + SIDE))
nexDungs = newSurf((DUNGW * 4, DUNGH + SIDE * LEVELSDOWN))
normRects = []  # cut dungs from normal positions
alignRects = [] # cut dungeons from curDungs
nextRects = []  # cut dungeons from nexDungs, including sides
sideRects = []  # cut sides only from nexDungs

for dung in range(4):
    normRects.append((origDungX[dung], origDungY[dung], DUNGW, DUNGH + TILE))
    alignRects.append((dung * DUNGW, 0, DUNGW, DUNGH + SIDE))
    nextRects.append((dung * DUNGW, 0, DUNGW, DUNGH + SIDE * LEVELSDOWN))
    sideRects.append((dung * DUNGW, DUNGH + SIDE, DUNGW, SIDE * LEVELSDOWN))


# BLITS DUNGEON SIDES FROM SIDESURFS
def blitSide(surf, dung, x, y):
    if levelsLeft != 0:
        if levelsLeft <= LEVELSDOWN:
            height = SIDE * (LEVELSDOWN - (LEVELSDOWN - levelsLeft) - 1)
        else:
            height = SIDE * LEVELSDOWN
        segment = (dung * DUNGW, (levelNum + 3) * SIDE, DUNGW, height)
        surf.blit(sideSurfs, (x, y), segment)



# CAMERA
camX = 0
camY = 0
camXLock = 0  # locks camera in direction for several frames
camYLock = 0
CAMLIMIT = mult * 2
CAMMAXFRAME = 60


# SHADOW: a black surface that changes opacity
shadow = pygame.Surface((DUNGW, DUNGH + SIDE))

sideShadow = (0, 0, DUNGW, SIDE) # used to fade out the level sides
wallShadow = (0, 0, TILE, SIDE)  # (un)used to add shadows below walls
tileShadow = (0, 0, TILE, TILE)  # used as a fix during next level transition


##############
### LEVELS ###
##############
class Box:
    def __init__(self, dungs, col, row, variant):
        self.origDungs = copy.copy(dungs)
        self.origCol = col
        self.origRow = row
        self.dungs = dungs
        self.col = col
        self.row = row
        self.xOff = 0
        self.yOff = 0
        self.variant = variant
        self.direction = None
        self.undos = []

        # only if it is visually locked (as in no wall / other box covers it)
        self.locked = [False, False, False, False]
        self.origLocked = [False, False, False, False]

moveBoxes = [] # all boxes that should be moved during animation

player = None
def initPlayer(dung, col, row):
    global player
    # only col and row are important
    player = Box([None, None, None, None], col, row, 0)
    player.dungs[dung] = True
    player.dung = dung
    player.origDung = dung
    player.fallOff = 0
    player.fallDiff = 8

# checks, recursively, if boxes are valid to push
def checkBox(direction, dung, col, row):
    global moveBoxes

    # determine direction to check
    if direction == LEFT:
        col -= 1
    elif direction == RIGHT:
        col += 1
    elif direction == UP:
        row -= 1
    elif direction == DOWN:
        row += 1

    # search for any boxes at this new position
    valid = True
    for box in curLvl.boxes:
        if box.col == col and box.row == row and box.dungs[dung] != None:
            if box not in moveBoxes:
                moveBoxes.append(box)

            # check each of the directions this box occupies
            for newDung in range(4):
                if box.dungs[newDung] != None:
                    if not (checkBox(direction, newDung, col, row)):
                        valid = False

            return valid

    # if there are no boxes, depending on the tile type, return if pushable
    if curLvl.tileAt(dung, col, row) in (WALL, VOID):
         False
    else:
        return True



### LEVEL CLASS ###
class Level:
    def __init__(self, layout, tileSheet, boxes):
        # origLayout: when resetting the level, revert to this.  don't modify
        #     layout: stores the layout of the level.  modify if you want
        #  tileSheet: stores which tilesheet the level is using
        #   tileVars: stores which sprite variant each tile uses
        self.origLayout = layout
        self.layout = copy.deepcopy(layout)
        self.tileSheet = tileSheet
        self.boxes = boxes

        # position variables
        self.x = 0
        self.y = 0
        self.dungX = copy.copy(origDungX)
        self.dungY = copy.copy(origDungY)

        # manages the plates and the locking of goals in the level
        self.locked = False
        self.plates = 0
        self.totPlates = 0

        tileVars = [[[0, 0, 0, 0, 0] for x in range(WIDTH)] for x in range(4)]

        for dung in range(4):
            for col in range(WIDTH):
                for row in range(HEIGHT):
                    tile = self.tileAt(dung, col, row)

                    variant = random.randint(0, tileSheet.varCount[tile] - 1)
                    tileVars[dung][col][row] = variant

        self.origTileVars = tileVars
        self.tileVars = copy.deepcopy(tileVars)


    ### RETURNS THE TILE AT A SPECIFIC LOCATION ###
    def tileAt(self, dung, col, row):
        if 0 <= col < WIDTH and 0 <= row < HEIGHT:
            tile = self.layout[dung][col][row]
            if type(tile) == Box:
                return BOX
            else:
                return tile

        # out of bounds tiles
        else:
            return VOID


    ### DRAWS A TILE FROM THE LEVEL ###
    def drawTile(self, surf, dung, col, row):
        x = math.ceil(self.dungX[dung] + col * TILE)
        y = math.ceil(self.dungY[dung] + row * TILE)

        # pulls some variables from self
        tile      = self.tileAt(dung, col, row)
        tileSheet = self.tileSheet
        variant   = self.tileVars[dung][col][row]

        # wall tiles consist of two potential parts, and are drawn higher
        if tile == WALL:
            tileSheet.drawTile(surf, (x, y), WALL, variant)

            # draws side if tile below is not also a wall
            if self.tileAt(dung, col, row + 1) != WALL:
                tileSheet.drawTile(surf, (x, y + TILE), WALLSIDE, variant)

        elif tile == GOAL:
            if self.locked:
                tileSheet.drawTile(surf, (x, y + SIDE), GOALLOCK, variant)
            else:
                tileSheet.drawTile(surf, (x, y + SIDE), GOAL, variant)

        # all other tiles only consist of one part, and are drawn lower
        elif tile != VOID:
            tileSheet.drawTile(surf, (x, y + SIDE), tile, variant)

            # (doesn't look good) draw shadow if tile above is a wall
            # if self.tileAt(dung, col, row - 1) == WALL:
                # shadow.set_alpha(50)
                # surf.blit(shadow, pos, wallShadow)



    ### DRAWS AN ENTIRE DUNGEON ###
    def drawDung(self, surf, dung):
        # basically just loops through and draws each tile
        for col in range(WIDTH):
            for row in range(HEIGHT):
                self.drawTile(surf, dung, col, row)




### LOADS THE LEVELS FROM FILE ###
# the level file uses singular letters to represent tiles
V = VOID
E = EMPTY
W = WALL
G = GOAL
S = SWIRL
B = BOX
P = PLATE

# READ FILE
levels = []
levelFile = open("levels.txt", "r")
levelFile = levelFile.read().split()

# REMOVES THE LEVEL DESCRIPTIONS (level00, level01, level02 and so on)
for x in reversed(range(len(levelFile))):
    if levelFile[x][:3] == "SET":
        levelFile.pop(x)

# CONVERTS ALL THE STRINGS TO THEIR RESPECTIVE CONSTANTS
for x in range(len(levelFile)):
    levelFile[x] = eval(levelFile[x])

# KEEPS TRACK OF LEVELS WHERE THE MUSIC CHANGES
currentLevel = 0
currentTileSheet = INTROSHEET
musicChanges = []

while levelFile:   # stops loading once there is nothing to load
    boxCount = 0   # counts the amount of box declarations needed
    boxVar = 0

    # FIRST ITEM SHOULD BE THE LEVEL'S TILESHEET
    buildSheet = levelFile.pop(0)

    boxPositions = []
    finalBoxes = []

    # BUILDS THE LEVEL BY POPPING EACH ITEM OFF
    buildLayout = [[[0 for x in range(HEIGHT)] for x in range(WIDTH)] for x in range(4)]

    for row in range(HEIGHT):    # creates up dungeon
        for col in range(WIDTH):
            if levelFile[0] == BOX:
                boxPositions.append((UP, col, row))
                levelFile.pop(0)
            else:
                buildLayout[   UP][col][row] = (levelFile.pop(0))

    for row in range(HEIGHT):    # creates left and right; they occupy same line
        for col in range(WIDTH):
            if levelFile[0] == BOX:
                boxPositions.append((LEFT, col, row))
                levelFile.pop(0)
            else:
                buildLayout[ LEFT][col][row] = (levelFile.pop(0))

        for col in range(WIDTH):
            if levelFile[0] == BOX:
                boxPositions.append((RIGHT, col, row))
                levelFile.pop(0)
            else:
                buildLayout[RIGHT][col][row] = (levelFile.pop(0))

    for row in range(HEIGHT):    # finally, creates down
        for col in range(WIDTH):
            if levelFile[0] == BOX:
                boxPositions.append((DOWN, col, row))
                levelFile.pop(0)
            else:
                buildLayout[ DOWN][col][row] = (levelFile.pop(0))

    for box in boxPositions:
        boxVar = (boxVar + 1) % (buildSheet.varCount[BOX])
        buildDungs = []
        buildLayout[box[0]][box[1]][box[2]] = levelFile.pop(0)
        for dung in range(4):
            if levelFile.pop(0) == None:
                buildDungs.append(None)
            else:
                buildDungs.append(True)

        finalBoxes.append(Box(buildDungs, box[1], box[2], boxVar))

    if currentTileSheet != buildSheet:
        musicChanges.append(currentLevel)
        currentTileSheet = buildSheet

    # CREATES A LEVEL OBJECT AND ADDS IT TO THE LEVEL LIST
    levels.append(Level(buildLayout, buildSheet, finalBoxes))

    currentLevel += 1


# IMPROMPTU PLATE COUNTING
for level in levels:
    for dung in range(4):
        for col in range(WIDTH):
            for row in range(HEIGHT):
                tile = level.layout[dung][col][row]

                if tile == PLATE:
                    level.totPlates += 1

    for box in level.boxes:
        for dung in range(4):
            if box.dungs[dung]:
                if level.tileAt(dung, box.col, box.row) == PLATE:
                    level.plates += 1

    level.locked = level.plates != level.totPlates


#######################
### MISC / UNSORTED ###
#######################
moveQueue = []  # keeps track of inputs
clock = pygame.time.Clock()                 # stabilizes fps
TAHOMA = pygame.font.SysFont("Tahoma", 10)  # font used for debug purposes
running = True        # game loop finishes once this is set to false
debugPressed = False  # tracks if the debug button is being pressed

# DRAWS SHADOW ON THE NEXT LAYER & SIDES
def drawNextShadow(surf, dung, x, y, shadowOffset):
    shadowAlpha = shadowOffset
    shadowAlpha += SHADOWINTERVAL
    if levelsLeft != 0:
        # blit over entire dungeon first
        shadow.set_alpha(shadowAlpha)
        surf.blit(shadow, (x, y))

    # chops off the darkened green above non-wall tiles
    for col in range(WIDTH):
        if nexLvl.tileAt(dung, col, 0) != WALL:
            pygame.draw.rect(surf, (0, 255, 0), (x + col * TILE, y, TILE, SIDE))
            pygame.draw.rect(surf, (0, 255, 0), (x + col * TILE, y, TILE, SIDE))

    y += DUNGH + SIDE

    # blit each side shadow with a different opacity
    for layer in range(1, LEVELSDOWN + 2):
        if levelsLeft - layer <= 0:
            break

        shadowAlpha += SHADOWINTERVAL

        shadow.set_alpha(shadowAlpha)
        surf.blit(shadow, (x, y), sideShadow)

        y += SIDE



def drawObjs(surf, dung, x, y, drawPlayer):
    for goal in goals[dung]:
        goalX = x + goal[0] * TILE
        goalY = y + goal[1] * TILE + SIDE

        width = TILE
        if notCover(dung, goal[0], goal[1] + 1):
            height = TILE
        else:
            height = SIDE

        var = curLvl.tileVars[dung][goal[0]][goal[1]]

        if curLvl.locked:
            rect = (GOALLOCK * TILE - TILE, var * TILE, width, height)
        else:
            rect = (GOAL * TILE - TILE, var * TILE, width, height)

        surf.blit(curTileSheet.surface, (goalX, goalY), rect)

    ### PLAYER ALPHA FIX ###
    if drawPlayer and player.row == 0:
        if curLvl.tileAt(dung, player.col, 0) != WALL:
            fixX = x + curLvl.x + player.col * TILE
            fixY = y + curLvl.y
            pygame.draw.rect(preDisplay, (0, 0, 0), (fixX, fixY, TILE, SIDE))

    ### LOCKS UNLOCKING ###
    if animCur is playAnim:
        # draws plate locks
        for plate in platesToUnlock:
            if plate[0] == dung:
                curLvl.drawTile(preDisplay, plate[0], plate[1], plate[2])

                h = math.ceil(mult - animUnlockBox.value)
                plateX = x + plate[1] * TILE + mult
                plateY = y + plate[2] * TILE + TILE + SIDE - mult + (mult - h)

                pygame.draw.rect(preDisplay, plateLockColor, (plateX, plateY, mult * 2, h))

    ### OBJECTS ###
    for row in objBuff:
        walls = []
        for obj in row:
            isPlayer = obj is player
            if (not isPlayer and obj.dungs[dung] != None) or (isPlayer and drawPlayer):

                # PLAYER
                if isPlayer:
                    objX = x + obj.col * TILE - TILE
                    objY = y + obj.row * TILE - TILE

                    if player.dung == dung:
                        playAnim.blitFrame(surf, (objX, objY))
                    else:
                        ghostAnim.blitFrame(surf, (objX, objY))

                # BOXES
                else:
                    objX = math.ceil(x + obj.col * TILE + obj.xOff)
                    objY = math.ceil(y + obj.row * TILE + obj.yOff + curLvl.y)

                    curTileSheet.drawTile(surf, (objX, objY), BOX, obj.variant)
                    curTileSheet.drawTile(surf, (objX, objY + TILE), BOXSIDE, obj.variant)

                # WALLS THAT SHOULD COVER THE OBJECT
                if obj.direction != DOWN:
                    walls.append((obj.col, obj.row + 1))

                    if obj.direction == LEFT:
                        walls.append((obj.col - 1, obj.row + 1))
                    elif obj.direction == RIGHT:
                        walls.append((obj.col + 1, obj.row + 1))

                else:
                    walls.append((obj.col, obj.row + 2))

                # if obj.dungs[dung] != None and obj.direction == None:
                #     # PLATE "LOCK" which doesn't actually lock anything
                #     if curLvl.tileAt(dung, obj.col, obj.row) == PLATE:
                #         covRect = (x + obj.col * TILE + mult,
                #                    y + obj.row * TILE + TILE + SIDE - mult,
                #                    mult * 2, mult)
                #         pygame.draw.rect(surf, plateLockColor, covRect)

                # LOCKS
                if obj.locked[dung] and notCover(dung, obj.col, obj.row + 1):
                    if obj is not player:
                        lockX = x + obj.col * TILE + mult
                        lockY = y + obj.row * TILE + TILE + SIDE - mult

                        pygame.draw.rect(surf, plateLockColor, (lockX, lockY, mult * 2, mult))

        for wall in walls:
            if curLvl.tileAt(dung, wall[0], wall[1]) == WALL:
                wallX = x + wall[0] * TILE
                wallY = y + wall[1] * TILE
                var = curLvl.tileVars[dung][wall[0]][wall[1]]

                # error drawing this wall
                curTileSheet.drawTile(surf, (wallX, wallY), WALL, var)


def notCover(dung, col, row, skipPlayer = False):

    if row == HEIGHT:
        return True

    if curLvl.tileAt(dung, col, row) == WALL:
        return False

    for box in curLvl.boxes:
        if box.dungs[dung] and box.col == col and box.row == row:
            return False

    if not skipPlayer:
        if player.dung == dung and player.col == col and player.row == row:
            return False

    return True


def debugCircle(surf, x, y, col):
    if col == 0:
        color = (255, 255, 0)
    elif col == 1:
        color = (255, 0, 255)
    else:
        color = (0, 255, 255)

    pygame.draw.circle(surf, color, (int(x), int(y)), 5)

def debugRect(surf, rect, col):
    if col == 0:
        color = (255, 255, 0)
    elif col == 1:
        color = (255, 0, 255)
    else:
        color = (0, 255, 255)

    pygame.draw.rect(surf, color, rect)


################################################################################
###                           ALMOST DONE SETUP                              ###
################################################################################
# (ruins all the comments)

title = loadSprite(os.path.join("images", "title.png"), mult)
titleKeys = loadSprite(os.path.join("images", "keys.png"), 4)
zKey = loadSprite(os.path.join("images", "zKey.png"), 4)
rKey = loadSprite(os.path.join("images", "rKey.png"), 4)
mKeyOn = loadSprite(os.path.join("images", "mKeyOn.png"), 4)
mKeyOff = loadSprite(os.path.join("images", "mKeyOff.png"), 4)
nKeyOn = loadSprite(os.path.join("images", "nKeyOn.png"), 4)
nKeyOff = loadSprite(os.path.join("images", "nKeyOff.png"), 4)
blackScreen = pygame.Surface(SCREENSIZE)
fadeAlpha = 255

SHOW = 1
FADE = 2
titleState = SHOW
titleAlpha = 255

titleX = mult * 3
titleY = mult * 5

titleKeysAlpha = 0
titleKeysDelay = 300
titleKeysX = SCREENLENGTH // 2 - titleKeys.get_width() // 2
titleKeysY = SCREENLENGTH // 2 - mult * 2

otherKeysAlpha = 0
otherKeysCounter = 0
otherKeysWait = 300
otherKeysX = SCREENLENGTH - rKey.get_width() - mult * 5
nKeyY = SCREENLENGTH - nKeyOn.get_height() - mult * 4
mKeyY = nKeyY - mKeyOn.get_height()
rKeyY = mKeyY - rKey.get_height()
zKeyY = rKeyY - zKey.get_height()

def otherKeysSetAlpha(alpha):
    zKey.set_alpha(alpha)
    rKey.set_alpha(alpha)
    mKeyOn.set_alpha(alpha)
    mKeyOff.set_alpha(alpha)
    nKeyOn.set_alpha(alpha)
    nKeyOff.set_alpha(alpha)

def otherKeysDraw(surface):
    surface.blit(zKey, (otherKeysX, zKeyY))
    surface.blit(rKey, (otherKeysX, rKeyY))
    if musicMuted:
        surface.blit(mKeyOff, (otherKeysX, mKeyY))
    else:
        surface.blit(mKeyOn, (otherKeysX, mKeyY))
    if sfxMuted:
        surface.blit(nKeyOff, (otherKeysX, nKeyY))
    else:
        surface.blit(nKeyOn, (otherKeysX, nKeyY))

### MENU LOOP ###
# the main display, pre-camera
preDisplay = newSurf((SCREENLENGTH, SCREENLENGTH + CAMLIMIT))

# the main display, post-camera
postDisplay.fill((0, 255, 0))

file = open("easilyEditableSaveData.txt", 'r')
saveData = file.read()
file.close()

saveData = saveData.split()
saveData = [int(saveData[x]) for x in range(len(saveData))]
levelNum = saveData[0]

lastLevel = 91
levelsLeft = lastLevel - levelNum

if levelNum <= 91:
    # in the case not all the data is present, find the start point manually
    if len(saveData) < 4:
        if levelNum == 0:
            initPlayer(RIGHT, 0, 2)
        else:
            goalExists = False
            for dungNum, dung in enumerate(levels[levelNum - 1].layout):
                for colNum, col in enumerate(dung):
                    for rowNum, tile in enumerate(col):
                        if tile == GOAL:
                            initPlayer(RIGHT, colNum, rowNum)
                            goalExists = True

            # if somehow no goal was found, default to the middle of the level
            if not goalExists:
                initPlayer(LEFT, 2, 2)

    else:
        initPlayer(saveData[1], saveData[2], saveData[3])

# PREDRAWS THE SIDES OF ALL THE LEVELS
# makes a surface that stores level sides for all four dungeons
sideSurfs = newSurf((DUNGW * 4, (len(levels) + 1)*SIDE + TILE+SIDE))

y = len(levels) * SIDE
for level in reversed(levels):
    y -= SIDE
    for dung in range(4):
        for col in range(WIDTH):
            x = dung * DUNGW + col * TILE
            tile = level.tileAt(dung, col, HEIGHT - 1)
            var = level.tileVars[dung][col][HEIGHT - 1]
            if tile == WALL:
                level.tileSheet.drawTile(sideSurfs, (x, y + SIDE), WALLSIDE, var)
            elif tile == GOAL:
                if level.locked:
                    level.tileSheet.drawTile(sideSurfs, (x, y), GOALLOCK, var)
                else:
                    level.tileSheet.drawTile(sideSurfs, (x, y), GOAL, var)
            else:
                level.tileSheet.drawTile(sideSurfs, (x, y), tile, var)

    for box in level.boxes:
        if box.row == HEIGHT - 1:
            for dung in range(4):
                if box.dungs[dung]:
                    x = dung * DUNGW + box.col * TILE
                    level.tileSheet.drawTile(sideSurfs, (x, y + SIDE), BOXSIDE, box.variant)

                    if level.tileAt(dung, box.col, HEIGHT - 1) == PLATE:
                        covRect = (x + mult, y + SIDE + SIDE - mult,
                                   mult * 2, mult)
                        pygame.draw.rect(sideSurfs, plateLockColor, covRect)


def loadSound(path):
    return pygame.mixer.Sound(os.path.join("sounds", path))


def loadSounds(path, count):
    return [loadSound(path % x) for x in range(1, count + 1)]


class Soundset:
    def __init__(self, path, variants):
        self.sounds = loadSounds(path, variants)
        self.variants = variants
        self.lastPlayed = 0

    def playRandom(self):
        if sfxMuted:
            return

        if self.variants == 1:
            id = 0
        else:
            id = random.randint(0, self.variants - 1)
            while id == self.lastPlayed:
                id = random.randint(0, self.variants - 1)
        self.sounds[id].play()
        self.lastPlayed = id

    def setVolumes(self, volume):
        for sound in self.sounds:
            sound.set_volume(volume)


def currentChannel():
    for x in range(MUSIC_COUNT):
        if levelNum < musicChanges[x]:
            return x

    for x in range(MUSIC_COUNT, 11):
        if levelNum < musicChanges[x]:
            return 11 - x - 1

    return -1

MUSIC_VOLUME = 0.4
MUSIC_FADE_SPEED = 0.003
MUSIC_COUNT = 6
musicTracks = loadSounds("music%i.ogg", MUSIC_COUNT)
musicChannels = [pygame.mixer.Channel(x) for x in range(MUSIC_COUNT)]


# STARTUP LOGO
animLogo = Animation(11, SPRITE, "images\\logo.png", 10, 10, mult // 2)
animLogoDelay = 10
animLogoCounter = 0
logoAlpha = 0

logoName = loadSprite("images\\nameWiggly.png", mult // 2)
soundIntro = loadSound("introJingle.ogg")
soundIntro.set_volume(0.3)
soundIntro.play()

for frame in range(270):
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    if logoAlpha < 255 and frame < 30:
        logoAlpha += 20
        animLogo.surface.set_alpha(logoAlpha)
        logoName.set_alpha(logoAlpha)
    elif logoAlpha > 0 and frame > 210:
        logoAlpha -= 10
        animLogo.surface.set_alpha(logoAlpha)
        logoName.set_alpha(logoAlpha)
    elif logoAlpha <= 0:
        animLogo.surface.set_alpha(0)
        logoName.set_alpha(0)
        break
    elif logoAlpha > 255:
        logoAlpha = 255
        animLogo.surface.set_alpha(255)
        logoName.set_alpha(255)
    elif logoAlpha < 0:
        logoAlpha = 0
        animLogo.surface.set_alpha(0)
        logoName.set_alpha(0)

    if animLogo.frame == animLogo.lastFrame:
        animLogo.resetAnim()
    animLogo.blitFrame(postDisplay, (140, 250))
    postDisplay.blit(logoName, (200, 238))
    if animLogoCounter == animLogoDelay:
        animLogo.nextFrame()
        animLogoCounter = 0
    else:
        animLogoCounter += 1

    pygame.display.flip()
    postDisplay.fill((0, 0, 0))
    clock.tick(60)

# MUSIC
for channel in range(MUSIC_COUNT):
    if currentChannel() == channel:
        musicTracks[channel].set_volume(MUSIC_VOLUME)
    else:
        musicTracks[channel].set_volume(0)
    musicChannels[channel].play(musicTracks[channel], -1)

previousMusic = currentChannel()

soundNextLevel = Soundset("levelUp%i.ogg", 3)
soundNextLevel.sounds[0].set_volume(0.98)
soundNextLevel.sounds[1].set_volume(1)
soundNextLevel.sounds[2].set_volume(0.60)

soundMove = Soundset("move%i.ogg", 9)
soundMove.setVolumes(0.7)

soundSwirl = Soundset("swirl%i.ogg", 7)
soundSwirl.setVolumes(0.3)

soundSwirlWoosh = Soundset("swirlWoosh%i.ogg", 6)
soundSwirlWoosh.setVolumes(0.4)

soundBoxSlide = Soundset("boxSlide%i.ogg", 6)
soundBoxSlide.setVolumes(0.7)
soundBoxSlide.sounds[0].set_volume(0.6)
soundBoxSlide.sounds[1].set_volume(0.6)

soundLock = Soundset("switchOn%i.ogg", 4)
soundUnlock = Soundset("switchOff%i.ogg", 4)
soundLock.setVolumes(0.7)
soundUnlock.setVolumes(0.7)

soundGoalOpen = Soundset("goalOpen%i.ogg", 4)
soundGoalClose = Soundset("goalClose%i.ogg", 4)
soundGoalOpen.setVolumes(0.2)
soundGoalClose.setVolumes(0.2)

soundWin = Soundset("win%i.ogg", 3)
soundWin.setVolumes(0.3)

musicMuted = False
sfxMuted = False

beatTheGame = levelNum > lastLevel
### GAMEPLAY LOOP ###
while not beatTheGame:

    ############################################################################
    ###                   STUFF THAT RESETS EACH LEVEL                       ###
    ############################################################################

    saveData = open("easilyEditableSaveData.txt", 'w')
    for dung in range(4):
        if player.dungs[dung]:
            saveData.write(str(levelNum) + ' ' + str(dung) + ' ' +
                           str(player.col) + ' ' + str(player.row))

    saveData.close()

    ### DRAWING LEVELS ###
    curLvl = levels[levelNum]  # stores reference to current level
    nexLvl = levels[levelNum + 1]  # stores reference to next level

    curTileSheet = curLvl.tileSheet
    nexTileSheet = nexLvl.tileSheet



    ### ANIMATION STUFF ###
    # NEXT LEVEL
    nexLvl.y = SIDE  # resets y values
    curLvl.y = 0

    animCur = None



    ### PLATES AND LOCKED GOALS ###
    # check next level so that it can be drawn properly
    nexPlates = 0
    nexTotPlates = 0
    for dung in range(4):
        for col in range(WIDTH):
            for row in range(HEIGHT):
                tile = nexLvl.layout[dung][col][row]

                if tile == PLATE:
                    nexTotPlates += 1

    for box in nexLvl.boxes:
        for dung in range(4):
            if box.dungs[dung]:
                if nexLvl.tileAt(dung, box.col, box.row) == PLATE:
                    nexPlates += 1

    nexLvl.locked = nexPlates != nexTotPlates

    goals = [[], [], [], []]
    totPlates = 0
    origPlates = 0
    for dung in range(4):
        for col in range(WIDTH):
            for row in range(HEIGHT):
                tile = curLvl.layout[dung][col][row]
                if tile == PLATE:
                    totPlates += 1
                elif tile == GOAL:
                    goals[dung].append((col, row))

    origGoals = copy.copy(goals)

    for box in curLvl.boxes:
        for dung in range(4):
            if box.dungs[dung]:
                if curLvl.tileAt(dung, box.col, box.row) == PLATE:
                    origPlates += 1

                    if notCover(dung, box.col, box.row + 1):
                        box.origLocked[dung] = True

        box.locked = copy.copy(box.origLocked)

    player.origLocked = [False, False, False, False]
    if curLvl.tileAt(player.dung, player.col, player.row) == PLATE:
        origPlates += 1

        if notCover(player.dung, player.col, player.row + 1):
            player.origLocked[player.dung] = True

    player.locked = copy.copy(player.origLocked)

    plates = origPlates
    curLvl.locked = plates != totPlates

    switchOn = False
    switchOff = False





    ### PREDRAWS BOTH THE CURRENT LEVEL AND THE NEXT LEVEL ###
    curDungs.fill((0, 255, 0))
    nexDungs.fill((0, 255, 0))

    # for drawing all the boxes onto the next level
    nexObjBuff = [[] for x in range(HEIGHT)]
    for box in nexLvl.boxes:
        nexObjBuff[box.row].append(box)

    for dung in range(4):
        ### DRAW NEXT LEVEL ###
        # postDisplay is used temporarily to draw dungeons in position
        nexLvl.drawDung(postDisplay, dung)

        # DRAW BOXES ONTO NEXT LEVEL (aren't constantly updated like cur level)
        for row in nexObjBuff:
            for box in row:
                if box.dungs[dung] != None:
                    x = nexLvl.dungX[dung] + box.col * TILE
                    y = nexLvl.dungY[dung] + box.row * TILE
                    nexTileSheet.drawTile(postDisplay, (x, y), BOX, box.variant)

                    tile = nexLvl.tileAt(dung, box.col, box.row + 1)

                    if tile != WALL:
                        nexTileSheet.drawTile(postDisplay, (x, y + TILE), BOXSIDE, box.variant)

                        if nexLvl.tileAt(dung, box.col, box.row) == PLATE:
                            if box is not player:
                                covRect = (x + mult, y + TILE + SIDE - mult,
                                           mult * 2, mult)
                                pygame.draw.rect(postDisplay, plateLockColor, covRect)

        nexDungs.blit(postDisplay, (dung * DUNGW, 0), normRects[dung])
        postDisplay.fill((0, 255, 0))

        x = dung * DUNGW
        blitSide(nexDungs, dung, x, DUNGH + SIDE)

        # DRAWS SHADOWS
        drawNextShadow(nexDungs, dung, x, 0, 0)



        ### DRAW CURRENT LEVEL ###
        curLvl.drawDung(postDisplay, dung)
        curDungs.blit(postDisplay, (dung * DUNGW, 0), normRects[dung])

        postDisplay.fill((0, 0, 0))

        if levelsLeft == 0:
            nexDungs.fill((0, 0, 0))

        preDisplay.blit(nexDungs, (nexLvl.dungX[dung], nexLvl.dungY[dung] + nexLvl.y), nextRects[dung])
        preDisplay.blit(curDungs, (curLvl.dungX[dung], curLvl.dungY[dung]), alignRects[dung])



    # MUSIC
    musicTrack = currentChannel()
    if previousMusic != musicTrack:
        fadeTo = musicTrack
        fadeProgress = 0.0
    else:
        fadeTo = -1
        fadeProgress = 1.0


    # UNDOS
    undoStates = []
    undoVars = []
    undoPlayer = []
    undoPlates = []
    undoGoals = []
    holdingUndoKey = False
    undoTimer = 0
    undoGoalWait = False
    UNDODELAY = 8


    # MISC
    objBuff = [[] for x in range(HEIGHT)]
    for box in curLvl.boxes:
        objBuff[box.row].append(box)

    objBuff[player.row].append(player)

    player.origCol = player.col
    player.origRow = player.row
    player.origDung = player.dung
    player.origDungs = copy.copy(player.dungs)

    for dung in range(4):
        drawObjs(preDisplay, dung, curLvl.dungX[dung], curLvl.dungY[dung], True)

    shadowOff = 0

    platesToLock = []
    platesToUnlock = []

    otherKeysCounter = 0





    ############################################################################
    ###                           GAMEPLAY LOOP                              ###
    ############################################################################

    nextLevel = False
    while not nextLevel:

        ##############
        ### EVENTS ###
        ##############
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:

                # inserts inputs into the moveQueue
                if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                    moveQueue.insert(0, LEFT)
                elif event.key == pygame.K_UP or event.key == pygame.K_w:
                    moveQueue.insert(0, UP)
                elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                    moveQueue.insert(0, RIGHT)
                elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                    moveQueue.insert(0, DOWN)

                # debug key
                elif event.key == pygame.K_f:
                    debugPressed = True

                # resets level
                elif event.key == pygame.K_r and animQueue == []:
                    undoStates.append(copy.deepcopy(curLvl.layout))
                    undoVars.append(copy.deepcopy(curLvl.tileVars))
                    for box in curLvl.boxes:
                        box.undos.append((box.col, box.row, copy.copy(box.dungs), copy.copy(box.locked)))
                    undoPlayer.append((player.dung, player.col, player.row, copy.copy(player.dungs)))
                    undoPlates.append(plates)
                    undoGoalWait = True

                    # resets camera
                    camXLock = 0
                    camYLock = 0

                    # resets layout and redraws dungeons
                    curDungs.fill((0, 255, 0))
                    postDisplay.fill((0, 255, 0))
                    # again, postDisplay is used as a temporary surface

                    curLvl.layout = copy.deepcopy(curLvl.origLayout)
                    curLvl.tileVars = copy.deepcopy(curLvl.origTileVars)
                    for dung in range(4):
                        rect = (curLvl.dungX[dung], curLvl.dungY[dung], DUNGW, DUNGH + TILE)
                        curLvl.drawDung(postDisplay, dung)
                        curDungs.blit(postDisplay, (dung * DUNGW, 0), rect)

                    postDisplay.fill((0, 0, 0))

                    # resets all boxes and player
                    player.col = player.origCol
                    player.row = player.origRow
                    player.dung = player.origDung
                    player.dungs = copy.copy(player.origDungs)

                    # resets all boxes
                    for box in curLvl.boxes:
                        box.col = box.origCol
                        box.row = box.origRow
                        box.dungs = copy.copy(box.origDungs)
                        box.locked = copy.copy(box.origLocked)

                    player.locked = copy.copy(player.origLocked)

                    objBuff = [[] for x in range(HEIGHT)]
                    for box in curLvl.boxes:
                        objBuff[box.row].append(box)

                    objBuff[player.row].append(player)

                    # resets goals
                    goals = copy.copy(origGoals)

                    # resets plates
                    plates = origPlates
                    curLvl.locked = plates != totPlates

                    # resets what is drawn in preDisplay
                    for dung in range(4):
                        for tile in range(WIDTH):
                            if curLvl.layout[dung][tile][0] != WALL:
                                x = curLvl.dungX[dung] + tile * TILE
                                y = curLvl.dungY[dung]
                                preDisplay.fill((0, 0, 0), (x, y, TILE, SIDE))

                        preDisplay.blit(curDungs, (curLvl.dungX[dung], curLvl.dungY[dung]), alignRects[dung])

                        drawObjs(preDisplay, dung, curLvl.dungX[dung], curLvl.dungY[dung], True)

                elif event.key == pygame.K_z:
                    holdingUndoKey = True

                # mutes music
                elif event.key == pygame.K_m:
                    if not musicMuted:
                        musicMuted = True
                        for track in musicTracks:
                            track.set_volume(0.0)
                    else:
                        musicMuted = False
                        musicTracks[musicTrack].set_volume(MUSIC_VOLUME)

                elif event.key == pygame.K_n:
                    sfxMuted = not sfxMuted





            elif event.type == pygame.KEYUP:

                # removes inputs from the moveQueue
                liftedKey = 0
                if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                    liftedKey = LEFT
                elif event.key == pygame.K_UP or event.key == pygame.K_w:
                    liftedKey = UP
                elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                    liftedKey = RIGHT
                elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                    liftedKey = DOWN

                elif event.key == pygame.K_f:
                    debugPressed = False

                elif event.key == pygame.K_z:
                    holdingUndoKey = False

                if liftedKey in moveQueue:
                    moveQueue.remove(liftedKey)

            elif event.type == pygame.QUIT:
                running = False



        #############
        ### INPUT ###
        #############

        ### UNDOS ###
        if holdingUndoKey and animQueue == []:
            if undoStates and undoTimer <= 0:
                undoTimer = UNDODELAY

                curLvl.layout = undoStates.pop()
                curLvl.tileVars = undoVars.pop()
                for box in curLvl.boxes:
                    boxInfo = box.undos.pop()
                    box.col = boxInfo[0]
                    box.row = boxInfo[1]
                    box.dungs = boxInfo[2]
                    box.locked = boxInfo[3]
                playerInfo = undoPlayer.pop()

                player.dung = playerInfo[0]
                player.col = playerInfo[1]
                player.row = playerInfo[2]
                player.dungs = playerInfo[3]

                goals = undoGoals.pop()
                plates = undoPlates.pop()
                curLvl.locked = plates != totPlates

                curDungs.fill((0, 255, 0))
                postDisplay.fill((0, 255, 0))
                # postDisplay is used as a temporary surface

                for dung in range(4):
                    rect = (curLvl.dungX[dung], curLvl.dungY[dung], DUNGW, DUNGH + TILE)
                    curLvl.drawDung(postDisplay, dung)
                    curDungs.blit(postDisplay, (dung * DUNGW, 0), rect)

                postDisplay.fill((0, 0, 0))

                objBuff = [[] for x in range(HEIGHT)]
                for box in curLvl.boxes:
                    objBuff[box.row].append(box)

                objBuff[player.row].append(player)

                for dung in range(4):
                    for tile in range(WIDTH):
                        if curLvl.layout[dung][tile][0] != WALL:
                            x = curLvl.dungX[dung] + tile * TILE
                            y = curLvl.dungY[dung]
                            preDisplay.fill((0, 0, 0), (x, y, TILE, SIDE))

                    preDisplay.blit(curDungs, (curLvl.dungX[dung], curLvl.dungY[dung]), alignRects[dung])

                    drawObjs(preDisplay, dung, curLvl.dungX[dung], curLvl.dungY[dung], True)

                otherKeysCounter = 0

            elif not undoStates:
                undoTimer = 0

            elif undoTimer > 0:
                undoTimer -= 1

        else:
            undoTimer = 0



        ### MOVEMENT ###
        # if an input was made and no animation is currently playing
        if moveQueue and animQueue == []:

            moveBoxes = []
            if checkBox(moveQueue[0], moveQueue[0], player.col, player.row):
                undoStates.append(copy.deepcopy(curLvl.layout))
                undoVars.append(copy.deepcopy(curLvl.tileVars))
                for box in curLvl.boxes:
                    box.undos.append((box.col, box.row, copy.copy(box.dungs), copy.copy(box.locked)))
                undoPlayer.append((player.dung, player.col, player.row, copy.copy(player.dungs)))
                undoPlates.append(plates)
                undoGoalWait = True

                otherKeysCounter = 0
                soundMove.playRandom()
                moveBoxes.append(player)

                if len(moveBoxes) > 1:
                    soundBoxSlide.playRandom()

                for box in moveBoxes:
                    box.direction = moveQueue[0]

                    # UNLOCKS PLATES
                    for dung in range(4):
                        if box.dungs[dung]:
                            if curLvl.tileAt(dung, box.col, box.row) == PLATE:
                                plates -= 1
                                switchOff = True

                                if notCover(dung, box.col, box.row + 1):
                                    platesToUnlock.append((dung, box.col, box.row))

                                box.locked[dung] = False



                player.dung = moveQueue[0]   # player changes dung immediately
                player.dungs = [None] * 4
                player.dungs[moveQueue[0]] = True

                playAnim = playMovement[player.direction]
                ghostAnim = ghostMovement[player.direction]

                # a quick fix for the animation not showing the first frame
                playAnim.frame = -1
                ghostAnim.frame = -1

                animQueue.append(playAnim)

            else:
                moveBoxes = []


        # MOVE CAMERA EVEN IF YOU CAN'T MOVE IN THAT DIRECTION
        if moveQueue:
            camDir = moveQueue[0]
            if camDir == LEFT or camDir == RIGHT:
                camXLock = CAMMAXFRAME
            elif camDir == UP or camDir == DOWN:
                camYLock = CAMMAXFRAME



        ##################
        ### ANIMATIONS ###
        ##################
        # all of the game's functionalities are tied to the animations, since
        # things should only happen once animations finish up

        if animQueue:
            animCur = animQueue[0]   # only affects first animation in queue

            ### LAST FRAME THINGS ###
            if animCur.frame == animCur.lastFrame:
                animCur.resetAnim()  # RESETS THE ANIMATION

                ### SPECIFIC TO PLAYER MOVEMENT ###
                if animCur is playAnim:
                    ### UPDATE POSITIONS OF PLAYER AND BOXES ###
                    direction = player.direction

                    # remove objects that moved in the y-buffer
                    if direction == UP or direction == DOWN:
                        for box in moveBoxes:
                            objBuff[box.row].remove(box)


                    for box in moveBoxes:

                        # updates box (and also player)
                        if direction == LEFT:
                            box.col -= 1
                        elif direction == RIGHT:
                            box.col += 1
                        elif direction == UP:
                            box.row -= 1
                        elif direction == DOWN:
                            box.row += 1

                        box.xOff = 0
                        box.yOff = 0

                        box.direction = None


                    # re-add objects that moved in the y-buffer
                    if direction == UP or direction == DOWN:
                        for box in moveBoxes:
                            objBuff[box.row].append(box)

                    # check if any box landed on a swirl or plate
                    for box in moveBoxes:
                        for dung in range(4):
                            if box.dungs[dung]:
                                tile = curLvl.tileAt(dung, box.col, box.row)
                                if tile == SWIRL:
                                    if animRotate not in animQueue:
                                        for dung in range(4):
                                            drawObjs(curDungs, dung, dung * DUNGW, 0, False)

                                        animQueue.append(animRotate)
                                        soundSwirl.playRandom()

                                        break

                                elif tile == PLATE:
                                    plates += 1
                                    switchOn = True

                                    if notCover(dung, box.col, box.row + 1):
                                        platesToLock.append((dung, box))

                    player.locked = [False, False, False, False]
                    platesToUnlock = []

                    previouslyLocked = curLvl.locked
                    currentlyLocked = plates != totPlates

                    if previouslyLocked and not currentlyLocked:
                        soundGoalOpen.playRandom()

                        animSameTime.append(animGoalUnlock)
                        curLvl.locked = False

                        # UPDATES THE GOALS ON CURDUNGS
                        for dung in range(4):
                            for goal in goals[dung]:
                                x = goal[0] * TILE + DUNGW * dung
                                y = goal[1] * TILE + SIDE

                                width = TILE
                                if notCover(dung, goal[0], goal[1] + 1):
                                    height = TILE
                                else:
                                    height = SIDE

                                var = curLvl.tileVars[dung][goal[0]][goal[1]]

                                if curLvl.locked:
                                    rect = (GOALLOCK * TILE - TILE, var * TILE, width, height)
                                else:
                                    rect = (GOAL * TILE - TILE, var * TILE, width, height)

                                curDungs.blit(curTileSheet.surface, (x, y), rect)

                    elif not previouslyLocked and currentlyLocked:
                        soundGoalClose.playRandom()
                        animSameTime.append(animGoalLock)
                        # locked only after the animation plays

                    moveBoxes = []


                    # reset player sprites to idle
                    playAnim = playIdle
                    ghostAnim = ghostIdle


                    tile = curLvl.tileAt(player.dung, player.col, player.row)

                    ### STARTS THE WINNING OF THE LEVEL ###
                    if tile == GOAL and not curLvl.locked:
                        soundNextLevel.playRandom()

                        if animRotate in animQueue:
                            animQueue.remove(animRotate)

                        animQueue.append(animPlayDrop)
                        animQueue.append(animCurLvlUp)

                    animSameTime.append(animLockBox)


                    ### REDRAWS THE LEVEL ###
                    for dung in range(4):
                        x = curLvl.dungX[dung]
                        y = curLvl.dungY[dung]

                        # fix for extra pixels appearing above level
                        pygame.draw.rect(preDisplay, (0, 0, 0), (x, y - SIDE, DUNGW, TILE))

                        preDisplay.blit(curDungs, (x, y), alignRects[dung])
                        drawObjs(preDisplay, dung, x, y, True)



                ### SPECIFIC TO DUNGEON ROTATION ###
                elif animCur is animRotate:
                    # UPDATE PLAYER DUNG
                    player.dung = (player.dung + 1) % 4

                    # UPDATE LAYOUT
                    curLvl.layout.insert(0, curLvl.layout[3])
                    del curLvl.layout[4]

                    # UPDATE BOXES
                    for box in curLvl.boxes:
                        box.dungs.insert(0, box.dungs[3])
                        del box.dungs[4]

                        box.locked.insert(0, box.locked[3])
                        del box.locked[4]

                    # UPDATE LEVEL GOALS
                    goals.insert(0, goals[3])
                    del goals[4]

                    # UPDATE TILE VARIANTS
                    curLvl.tileVars.insert(0, curLvl.tileVars[3])
                    del curLvl.tileVars[4]

                    # UPDATE (RESET) DUNGEON POSITIONS
                    curLvl.dungX = copy.copy(origDungX)
                    curLvl.dungY = copy.copy(origDungY)

                    # SHIFT OVER EACH DUNGEON IN CURDUNGS
                    postDisplay.fill((0, 255, 0))

                    curDungs.fill((0, 255, 0))
                    for dung in range(4):
                        curLvl.drawDung(postDisplay, dung)
                        curDungs.blit(postDisplay, (dung * DUNGW, 0), normRects[dung])

                    postDisplay.fill((0, 0, 0))

                    # REDRAW EVERYTHING
                    preDisplay.fill((0, 0, 0))
                    for dung in range(4):
                        x = curLvl.dungX[dung]
                        y = curLvl.dungY[dung]
                        preDisplay.blit(nexDungs, (x, y + SIDE), nextRects[dung])
                        preDisplay.blit(curDungs, (x, y), alignRects[dung])

                        drawObjs(preDisplay, dung, curLvl.dungX[dung], curLvl.dungY[dung], True)

                    del animQueue[0]
                    continue  # king crimsons a single frame


                ### SPECIFIC TO PLAYER DROPPING INTO GOAL ###
                elif animCur is animPlayDrop:
                    animQueue.remove(animCur)

                    ### WIN THE LEVEL ###
                    for dung in range(4):
                        drawObjs(curDungs, dung, dung * DUNGW, 0, False)

                        ### REDRAWS NEXT LEVEL WITHOUT SHADOWS ###
                        postDisplay.fill((0, 255, 0))
                        nexLvl.drawDung(postDisplay, dung)

                        # determine if the next level should be locked or not
                        if nexLvl.layout[player.dung][player.col][player.row] == PLATE:
                            nexPlates += 1

                        for row in nexObjBuff:
                            for box in row:
                                if box.dungs[dung] != None:
                                    x = nexLvl.dungX[dung] + box.col * TILE
                                    y = nexLvl.dungY[dung] + box.row * TILE
                                    nexTileSheet.drawTile(postDisplay, (x, y), BOX, box.variant)

                                    if nexLvl.tileAt(dung, box.col, box.row + 1) != WALL:
                                        nexTileSheet.drawTile(postDisplay, (x, y + TILE), BOXSIDE, box.variant)

                                        if nexLvl.tileAt(dung, box.col, box.row) == PLATE and box is not player:
                                            covRect = (x + mult, y + TILE + SIDE - mult,
                                                       mult * 2, mult)
                                            pygame.draw.rect(postDisplay, plateLockColor, covRect)

                        nexDungs.blit(postDisplay, (dung * DUNGW, 0), normRects[dung])
                        postDisplay.fill((0, 0, 0))

                        x = dung * DUNGW
                        blitSide(nexDungs, dung, x, DUNGH + SIDE)
                    continue


                ### SPECIFIC TO NEXT LEVEL TRANSITION ###
                elif animCur is animCurLvlUp:
                    if levelsLeft == 0:
                        beatTheGame = True
                        break
                    levelsLeft -= 1
                    levelNum += 1
                    nextLevel = True

                    # exits game loop and goes to the next level
                    del animQueue[0]
                    break    # reload stuff for next level

                del animQueue[0] # deletes animation from queue

            # INCREMENTS FRAME AND VALUES for each other frame
            else:
                animCur.nextFrame()

        else:   # resets if there are no animations playing
            animCur = None



        ##########################
        ### DRAWING EVERYTHING ###
        ##########################

        if animCur is playAnim:
            # slides all boxes
            for box in moveBoxes:

                if box.direction == LEFT:
                    box.xOff = -animBoxSlide.value

                elif box.direction == RIGHT:
                    box.xOff = animBoxSlide.value

                elif box.direction == UP:
                    box.yOff = -animBoxSlide.value

                elif box.direction == DOWN:
                    box.yOff = animBoxSlide.value

            player.xOff = 0  # does not slide the player
            player.yOff = 0

            # redraws all current dungeons
            for dung in range(4):
                rect = (origDungX[dung], origDungY[dung] - SIDE, DUNGW, DUNGH + SIDE * 2)
                preDisplay.fill((0, 0, 0), rect)
                preDisplay.blit(curDungs, (curLvl.dungX[dung], curLvl.dungY[dung]), alignRects[dung])

                drawObjs(preDisplay, dung, curLvl.dungX[dung], curLvl.dungY[dung], True)



        elif animCur is animRotate:
            # UPDATE DUNGEON POSITIONS
            for dung in range(4):  # updates the dungeon positions
                angle = (dung + 2) % 4 * 90
                angle += animCur.value
                angle = math.radians(angle)

                x = ROTATEMIDX + math.cos(angle) * ROTATERADIUS
                y = ROTATEMIDY + math.sin(angle) * ROTATERADIUS

                curLvl.dungX[dung] = x
                curLvl.dungY[dung] = y

            # DRAW DUNGEONS IN UPDATED POSITIONS
            preDisplay.fill((0, 0, 0))

            # NEXT LEVEL
            for dung in range(4):
                x = nexLvl.dungX[dung] + nexLvl.x
                y = nexLvl.dungY[dung] + nexLvl.y
                preDisplay.blit(nexDungs, (x, y), nextRects[dung])

            # CURRENT LEVEL
            for dung in range(4):
                x = curLvl.dungX[dung] + curLvl.x
                y = curLvl.dungY[dung] + curLvl.y
                preDisplay.blit(curDungs, (x, y), alignRects[dung])

                # PLAYER
                x = curLvl.dungX[dung] + player.col * TILE - TILE
                y = curLvl.dungY[dung] + player.row * TILE - TILE + player.yOff
                if player.dung == dung:
                    playAnim.blitFrame(preDisplay, (x, y))
                else:
                    ghostAnim.blitFrame(preDisplay, (x, y))

                # TILE THAT OVERLAPS THE PLAYER
                if player.row != HEIGHT - 1:
                    x += TILE
                    y += TILE * 2
                    if curLvl.tileAt(dung, player.col, player.row + 1) == WALL:
                        var = curLvl.tileVars[dung][player.col][player.row + 1]
                        curTileSheet.drawTile(preDisplay, (x, y), WALL, var)

                    else:
                        for box in objBuff[player.row + 1]:
                            if box.col == player.col and box.dungs[dung]:
                                curTileSheet.drawTile(preDisplay, (x, y), BOX, box.variant)



        elif animCur is animPlayDrop:
            player.yOff = animPlayDrop.value
            for dung in range(4):
                # fixes previous movement frames showing up uninvited
                if player.row == 0:
                    x = curLvl.x + curLvl.dungX[dung] + player.col * TILE
                    y = curLvl.y + curLvl.dungY[dung]
                    pygame.draw.rect(preDisplay, (0, 0, 0), (x, y, TILE, SIDE))

                # draws all the blocks above the player
                x = curLvl.x + curLvl.dungX[dung] + player.col * TILE
                y = curLvl.y + curLvl.dungY[dung]
                rect = (dung * DUNGW + player.col * TILE, 0, TILE, player.row * TILE + TILE + SIDE)

                preDisplay.blit(curDungs, (x, y), rect)

                # draws all boxes on the column
                for box in curLvl.boxes:
                    if box.col == player.col and box.dungs[dung]:
                        x = curLvl.x + curLvl.dungX[dung] + box.col * TILE
                        y = curLvl.y + curLvl.dungY[dung] + box.row * TILE
                        curTileSheet.drawTile(preDisplay, (x, y), BOX, box.variant)
                        if notCover(dung, box.col, box.row + 1, True):
                            curTileSheet.drawTile(preDisplay, (x, y + TILE), BOXSIDE, box.variant)

                            if curLvl.tileAt(dung, box.col, box.row) == PLATE:
                                if box is not player:
                                    rect = (x + mult, y + TILE + mult, mult*2, mult)
                                    pygame.draw.rect(preDisplay, plateLockColor, rect)


                # draws block on next level below player
                if player.row == HEIGHT - 1:
                    y = nexLvl.y + nexLvl.dungY[dung] + HEIGHT * TILE
                    rect = (dung * DUNGW + player.col * TILE, HEIGHT * TILE, TILE, SIDE)
                    preDisplay.blit(nexDungs, (x, y), rect)

                # finally draws the player
                x = curLvl.dungX[dung] + player.col * TILE - TILE
                y = curLvl.dungY[dung] + player.row * TILE - TILE + player.yOff
                if player.dung == dung:
                    playAnim.blitFrame(preDisplay, (x, y))
                else:
                    ghostAnim.blitFrame(preDisplay, (x, y))

                # draw block below player so that they "fall through" the hole
                if player.row != HEIGHT - 1:
                    for box in objBuff[player.row + 1]:
                        if box.col == player.col and box.dungs[dung]:
                            x = curLvl.dungX[dung] + box.col * TILE
                            y = curLvl.dungY[dung] + box.row * TILE
                            curTileSheet.drawTile(preDisplay, (x, y), BOX, box.variant)
                            break
                    else:
                        curLvl.drawTile(preDisplay, dung, player.col, player.row + 1)

                    if player.row != HEIGHT - 2:

                        # this will cover the wall below that tile so draw this
                        if curLvl.tileAt(dung, player.col, player.row + 2) == WALL:
                            x = curLvl.dungX[dung] + player.col * TILE
                            y = curLvl.dungY[dung] + player.row * TILE + TILE * 2
                            var = curLvl.tileVars[dung][player.col][player.row + 2]
                            curTileSheet.drawTile(preDisplay, (x, y), WALL, var)

                        else:
                            for box in objBuff[player.row + 2]:
                                if box.col == player.col and box.dungs[dung]:
                                    x = curLvl.dungX[dung] + box.col * TILE
                                    y = curLvl.dungY[dung] + box.row * TILE
                                    curTileSheet.drawTile(preDisplay, (x, y), BOX, box.variant)
                                    break



        elif animCur is animCurLvlUp:
            ### MOVES EVERYTHING UP ###
            curLvl.y = round(animCurLvlUp.value)
            nexLvl.y = round(animNexLvlUp.value) + SIDE

            player.yOff = nexLvl.y

            # shadows are offset so that a gradual fade occurs
            shadowOff = - NEXTSHADOWINTERVAL * animCur.frame

            camXLock = 0  # resets camera
            camYLock = 0


            # DRAWS EVERYTHING MOVED UP
            preDisplay.fill((0, 0, 0))

            if levelsLeft == 0:
                player.fallOff += player.fallDiff
                player.fallDiff += mult / 6

            for dung in range(4):
                if levelsLeft != 0:
                    # NEXT LEVEL
                    x = nexLvl.dungX[dung]
                    y = nexLvl.dungY[dung] + nexLvl.y
                    preDisplay.blit(nexDungs, (x, y), nextRects[dung])

                # SHADOWS
                x = nexLvl.dungX[dung]
                y = nexLvl.dungY[dung] + nexLvl.y
                drawNextShadow(preDisplay, dung, x, y, shadowOff)

                # FIXES BOXES BEING CUT OFF BY SHADOW
                if levelsLeft != 0:
                    for box in nexLvl.boxes:
                        if box.row == 0 and box.dungs[dung]:
                            x = nexLvl.dungX[dung] + box.col * TILE
                            y = nexLvl.dungY[dung] + nexLvl.y
                            nexTileSheet.drawTile(preDisplay, (x, y), BOX, box.variant)

                # FIXES GREEN APPEARING BEHIND PLAYER
                if player.row == 0:
                    if nexLvl.tileAt(dung, player.col, player.row) != WALL:
                        x = nexLvl.x + nexLvl.dungX[dung] + player.col * TILE
                        y = nexLvl.y + nexLvl.dungY[dung] + player.row * TILE
                        pygame.draw.rect(preDisplay, (0, 0, 0), (x, y, TILE, SIDE))

                # CURRENT LEVEL
                x = curLvl.dungX[dung]
                y = curLvl.dungY[dung] + curLvl.y
                preDisplay.blit(curDungs, (x, y), alignRects[dung])

                # PLAYER
                x = nexLvl.dungX[dung] + player.col * TILE - TILE + player.xOff
                y = nexLvl.dungY[dung] + player.row * TILE - TILE + player.yOff + player.fallOff
                if player.dung == dung:
                    playAnim.blitFrame(preDisplay, (x, y))
                else:
                    ghostAnim.blitFrame(preDisplay, (x, y))

                # WALL BENEATH PLAYER AT NEXT LEVEL
                if player.row != HEIGHT - 1 and levelsLeft != 0:
                    x = nexLvl.x + nexLvl.dungX[dung] + player.col * TILE
                    y = nexLvl.y + nexLvl.dungY[dung] + (player.row + 1) * TILE

                    if nexLvl.tileAt(dung, player.col, player.row + 1) == WALL:
                        var = nexLvl.tileVars[dung][player.col][player.row + 1]

                        nexTileSheet.drawTile(preDisplay, (x, y), WALL, var)

                        shadow.set_alpha((- NEXTSHADOWINTERVAL * animCur.frame) + SHADOWINTERVAL)
                        preDisplay.blit(shadow, (x, y), (0, 0, TILE, TILE))

                    else:
                        for box in nexObjBuff[player.row + 1]:
                            if box.col == player.col and box.dungs[dung] != None:

                                nexTileSheet.drawTile(preDisplay, (x, y), BOX, box.variant)
                                break



                # COLUMN OF TILES BELOW PLAYER IN CUR LEVEL
                # first half, only draw the tiles below player
                if animCur.frame < animCur.lastFrame / 2:
                    if player.row != HEIGHT - 1:
                        if curLvl.tileAt(dung, player.col, player.row + 1) == WALL:
                            start = (player.row + 1) * TILE

                        else:
                            for box in objBuff[player.row + 1]:
                                if box.col == player.col and box.dungs[dung]:
                                    start = (player.row + 1) * TILE
                                    break

                            else:
                                start = (player.row + 1) * TILE + SIDE

                    else:
                        start = DUNGH + SIDE

                # second half, draw all tiles in player's column
                else:
                    start = 0

                x = curLvl.x + curLvl.dungX[dung] + player.col * TILE
                y = curLvl.y + curLvl.dungY[dung] + start

                rect = (dung * DUNGW + player.col * TILE, start, TILE, DUNGH + SIDE - start)
                preDisplay.blit(curDungs, (x, y), rect)



        ### ANIMATIONS THAT PLAY REGARDLESS OF OTHER ANIMATIONS ###
        for anim in animSameTime:
            anim.nextFrame()

            ### EVERY FRAME STUFF ###

            # DRAWS ALL LOCKS ON BOXES ON PLATES
            if anim is animLockBox:
                for plate in platesToLock:
                    box = plate[1]

                    if box not in moveBoxes and box is not player:
                        h = math.ceil(anim.value)

                        x = curLvl.x + curLvl.dungX[plate[0]] + box.col * TILE + mult
                        y = curLvl.y + curLvl.dungY[plate[0]] + box.row * TILE + TILE + SIDE - mult + (mult - h)

                        pygame.draw.rect(preDisplay, plateLockColor, (x, y, mult * 2, h))

            # LOCKS GOALS WHEN ALL PLATES ARE COVERED
            elif anim is animGoalLock:
                w = math.ceil(anim.value)
                for dung in range(4):
                    for goal in goals[dung]:
                        if notCover(dung, goal[0], goal[1]):

                            if notCover(dung, goal[0], goal[1] + 1):
                                h = TILE
                            else:
                                h = SIDE

                            # left half
                            x = curLvl.dungX[dung] + goal[0] * TILE
                            y = curLvl.dungY[dung] + goal[1] * TILE + SIDE
                            rect = (GOALLOCK * TILE - TILE + (SIDE - w), 0, w, h)

                            preDisplay.blit(curTileSheet.surface, (x, y), rect)

                            # right half
                            x += SIDE + (SIDE - w)
                            rect = (GOALLOCK * TILE - TILE + SIDE, 0, w, h)

                            preDisplay.blit(curTileSheet.surface, (x, y), rect)



            # UNLOCK GOALS IF ANY PLATE IS UNCOVERED
            elif anim is animGoalUnlock and anim.frame:
                w = math.floor(SIDE - anim.value)
                for dung in range(4):
                    for goal in goals[dung]:
                        if notCover(dung, goal[0], goal[1]):
                            if notCover(dung, goal[0], goal[1] + 1):
                                h = TILE
                            else:
                                h = SIDE

                            # goal
                            x = curLvl.dungX[dung] + goal[0] * TILE
                            y = curLvl.dungY[dung] + goal[1] * TILE + SIDE
                            rect = (GOAL * TILE - TILE, 0, TILE, h)
                            preDisplay.blit(curTileSheet.surface, (x, y), rect)

                            # left half
                            rect = (GOALLOCK * TILE - TILE + (SIDE - w), 0, w, h)

                            preDisplay.blit(curTileSheet.surface, (x, y), rect)

                            # right half
                            x += SIDE + (SIDE - w)
                            rect = (GOALLOCK * TILE - TILE + SIDE, 0, w, h)

                            preDisplay.blit(curTileSheet.surface, (x, y), rect)



            ### LAST FRAME STUFF ###

            if anim.frame == anim.lastFrame:

                # RESETS PLATE LOCKS
                if anim is animLockBox:

                    # UPDATES THE LOCKEDNESS OF ALL BOXES
                    for box in curLvl.boxes:
                        if box not in moveBoxes:
                            for dung in range(4):
                                if box.dungs[dung]:
                                    if curLvl.tileAt(dung, box.col, box.row) == PLATE:
                                        box.locked[dung] = True

                    # CLEARS ALL PLATES THAT NEED TO BE LOCKED
                    platesToLock = []
                    platesToUnlock = []

                elif anim is animGoalLock:
                    # LOCK THE LEVEL
                    curLvl.locked = True

                anim.resetAnim()
                animSameTime.remove(anim)

        ### UNDO GOAL FIX ###
        if undoGoalWait:
            undoGoalWait = False
            undoGoals.append(goals)

        ### PLATE SOUNDS ###
        if switchOn:
            soundLock.playRandom()
        elif switchOff:
            soundUnlock.playRandom()

        switchOn = False
        switchOff = False


        ### MUSIC ###
        if fadeTo != -1:
            fadeProgress += MUSIC_FADE_SPEED
            if fadeProgress > MUSIC_VOLUME:
                fadeProgress = 0.0
                fadeTo = -1
                if not musicMuted:
                    musicTracks[previousMusic].set_volume(0.0)
                    musicTracks[musicTrack].set_volume(MUSIC_VOLUME)
                previousMusic = musicTrack

            elif not musicMuted:
                musicTracks[previousMusic].set_volume(MUSIC_VOLUME - fadeProgress)
                musicTracks[musicTrack].set_volume(fadeProgress)


        ### CAMERA MOVEMENT ###
        # MOVES THE CAMERA ALONG X AXIS
        if camXLock:
            camXLock -= 1

            if camDir == LEFT:
                camX -= (CAMLIMIT + camX) * 0.1
            elif camDir == RIGHT:
                camX += (CAMLIMIT - camX) * 0.1

        # makes sure x and y both move back together
        elif camYLock:
            pass

        # smooths the movement back, until 0.2 where it snaps
        elif -0.2 > camX or camX > 0.2:
            camX -= camX * 0.1

        # snaps camera to 0
        else:
            camX = 0


        # MOVES THE CAMERA ALONG Y AXIS, BASICALLY THE SAME AS X
        if camYLock:
            camYLock -= 1

            if camDir == UP:
                camY -= (CAMLIMIT + camY) * 0.1
            elif camDir == DOWN:
                camY += (CAMLIMIT - camY) * 0.1

        elif camXLock:
            pass

        elif -0.2 > camY or camY > 0.2:
            camY -= camY * 0.1

        else:
            camY = 0


        postDisplay.blit(preDisplay, (-camX, -camY))



        ### POST CAMERA ###
        # TITLE
        if titleState == SHOW:
            postDisplay.blit(title, (titleX, titleY))
            if moveQueue:
                titleState = FADE

            # TUTORIAL KEYS
            if titleKeysDelay == 0:
                titleKeys.set_alpha(titleKeysAlpha)
                postDisplay.blit(titleKeys, (titleKeysX, titleKeysY))
                if titleKeysAlpha < 255:
                    titleKeysAlpha += 6
                else:
                    titleKeysAlpha = 255
            else:
                titleKeysDelay -= 1

        elif titleState == FADE:
            if titleAlpha >= 0:

                titleAlpha -= 20
                title.set_alpha(titleAlpha)
                postDisplay.blit(title, (titleX, titleY))

                titleKeysAlpha -= 20
                titleKeys.set_alpha(titleKeysAlpha)
                postDisplay.blit(titleKeys, (titleKeysX, titleKeysY))
            else:
                titleState = 0

        # OTHER KEYS DISPLAY
        if otherKeysCounter < otherKeysWait:
            otherKeysCounter += 1

            if otherKeysAlpha > 0:
                otherKeysAlpha -= 20
                otherKeysSetAlpha(otherKeysAlpha)
                otherKeysDraw(postDisplay)
            else:
                otherKeysAlpha = 0
                otherKeysSetAlpha(0)
        else:
            if otherKeysAlpha < 255:
                otherKeysAlpha += 6
                otherKeysSetAlpha(otherKeysAlpha)
            else:
                otherKeysAlpha = 255
                otherKeysSetAlpha(255)
            otherKeysDraw(postDisplay)

        # FADE IN
        if fadeAlpha >= 0:
            blackScreen.set_alpha(fadeAlpha)
            postDisplay.blit(blackScreen, (0, 0))
            fadeAlpha -= 2




        ### DEBUGGING ###
        # postDisplay.blit(nexDungs, (0, 0))

        # fps = TAHOMA.render(str(round(clock.get_fps())), False, (255, 255, 255))
        # postDisplay.blit(fps, (10, 10))

        # debug1 = TAHOMA.render(str(curLvl.locked), False, (255, 255, 255))
        # debug2 = TAHOMA.render(repr(animUnlockBox.frame), False, (255, 255, 255))
        # debug3 = TAHOMA.render(str(levelNum) + " " + str(levelNum * 20), False, (255, 255, 255))
        # debug4 = TAHOMA.render(repr([musicTracks[x].get_volume() for x in range(MUSIC_COUNT)]), False, (255, 255, 255))

        # postDisplay.blit(debug1, (10, 20))
        # postDisplay.blit(debug2, (10, 30))
        # postDisplay.blit(debug3, (10, 40))
        # postDisplay.blit(debug4, (10, 50))

        # if debugPressed:
        #     clockTick = 2   # slow down game when the debug button is pressed
        # else:
        clockTick = 60



        ### FINAL OUTPUT ###
        pygame.display.flip()        # display the screen

        postDisplay.fill((0, 0, 0))  # clear the screen

        clock.tick(clockTick)        # keeps the FPS at a consistent 60

        # exits loops when window is closed
        if not running:
            break

    if not running:
        break


fadeProgress = 0.0
endCredit = loadSprite(os.path.join("images", "credits.png"), mult // 2)
dialogue1 = loadSprite(os.path.join("images", "dialogue1.png"), mult // 2)
dialogue2 = loadSprite(os.path.join("images", "dialogue2.png"), mult // 2)
endFrame = 0
if beatTheGame:
    saveData = open("easilyEditableSaveData.txt", 'w')
    saveData.write("0 2 0 2")
    saveData.close()

    postDisplay.fill((0, 0, 0))
    # END SCREEN LOOP
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        if not musicMuted and fadeProgress < MUSIC_VOLUME:
            fadeProgress += MUSIC_FADE_SPEED
            if fadeProgress >= MUSIC_VOLUME:
                musicTracks[0].set_volume(0.0)
            else:
                musicTracks[0].set_volume(MUSIC_VOLUME - fadeProgress)

        if endFrame < 601:
            endFrame += 1

        if endFrame == 180:
            if not sfxMuted:
                soundWin.sounds[0].play()
            title.set_alpha(255)
            postDisplay.blit(title, (titleX, titleY))
            postDisplay.blit(endCredit, (68, 280))

        elif endFrame == 360:
            if not sfxMuted:
                soundWin.sounds[1].play()
            postDisplay.blit(dialogue1, (144, 332))

        elif endFrame == 540:
            if not sfxMuted:
                soundWin.sounds[2].play()
            postDisplay.blit(dialogue2, (76, 428))

        pygame.display.flip()
        clock.tick(60)

pygame.quit()
sys.exit()
