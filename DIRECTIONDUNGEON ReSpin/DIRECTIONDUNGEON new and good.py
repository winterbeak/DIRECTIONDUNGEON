################################################################################
###                            DIRECTIONDUNGEON!                             ###
################################################################################

### LIST OF THINGS TO DO ###

# sokoban blocks, except they can be in less than 4 dungeons
# also need plate for them to go on.  or maybe drop them into holes?

# levels
# (probably 64, since it's 4 cubed, and because of 4 button menu)
# i have decided that 64 is too short....

# optimize - don't draw nexlvl unless animRotate or animNextLevel
# optimize - don't draw layers to preDisplay every single frame

# figure out how to slowly fade the player over time
# (probably by taking the pixel array and recoloring it every few levels or so)
# (or having an original cube spritesheet and drawing a black surface over it
# with changing opacity)

# create the gemstone/star in the center of the dungeons

# main menu
# that sick level select i thought of
# pause function...?  probably not necessary since everything is
#     silent and there's not much action

# sounds, ambient and raindrop-py
# music should be minimal and only at the start/end
# if not, though, outsource music to mustardflu?


### RANDOM IDEAS ###
# should the void cover the bottom tile halfway? to hint at a wall being there?
# different perspectives for each dungeon?
# keys/locks?
# pushable blocks?


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

pygame.init()
pygame.display.set_caption('DIRECTIONDUNGEON!')  # gives window a title

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
covers = (WALL, BOX)  # tile types that cover the player

# DUNGEON POSITIONS
origDungX = [MARG, DUNGW + MARG*2, DUNGW*2 + MARG*3, DUNGW + MARG*2]
origDungY = [DUNGH + MARG*2, MARG, DUNGH + MARG*2, DUNGH*2 + MARG*3]

# centers dungeons (because of sides, height of dungeon is more than width)
for dung in range(4):
    origDungX[dung] += SIDE / 2

dungX = copy.copy(origDungX)
dungY = copy.copy(origDungY)






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
        if tile == WALLSIDE:
            height = SIDE
        elif tile == BOX:
            height = TILE + SIDE
        else:
            height = TILE

        # cuts out the tile from the tilesheet and draws it
        tileRect = ((tile - 1)*TILE, variant*height, TILE, height)
        surf.blit(self.surface, pos, tileRect)

# a test tilesheet.  multiple can be made
TESTSHEET = Tilesheet("images\\testSheet.png", mult, (0, 2, 2, 2, 0, 0, 3))



##################
### ANIMATIONS ###
##################

animQueue = []   # a queue that plays animations in order

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



### PLAYER ANIMATIONS ###

# sliding boxes (should actually be 6 frames but that breaks it kinda
animBoxSlide = Animation(7, RQUADRATIC, TILE)
# you can change this to RQUADRATIC if you think it looks better

# creates and loads all the ghost/player animations from file
directionStrings = ["Left", "Up", "Right", "Down"]
playMovement = []
ghostMovement = []
for direction in directionStrings:
    path =  "images\\play" + direction + ".png"

    # creates ghost animation, equal to the player animation except transparent
    tempGhostAnim = Animation(6, SPRITE, path, 12, 14, mult)
    tempGhostAnim.surface.set_alpha(100)
    ghostMovement.append(tempGhostAnim)

    # the ghost animation is then tied to the player animation
    tempPlayAnim = Animation(6, SPRITE, path, 12, 14, mult, [tempGhostAnim, animBoxSlide])
    playMovement.append(tempPlayAnim)

# idle doesn't have to be animation, but it just makes things easier
playIdle = Animation(0, SPRITE, "images\\playIdle.png",  12, 14, mult)
ghostIdle = Animation(0, SPRITE, "images\\playIdle.png",  12, 14, mult)
ghostIdle.surface.set_alpha(100)
playAnim = playIdle
ghostAnim = ghostIdle



### LEVEL ANIMATIONS ###
animRotate = Animation(18, RQUADRATIC, 90)
ROTATERADIUS = DUNGW + MARG
ROTATEMIDX = DUNGW + MARG*2 + SIDE // 2
ROTATEMIDY = DUNGH + MARG*2

animPlayDrop = Animation(8, LINEAR, SIDE)

# these two animations are "tied" together and will play at the same time
animNexLvlUp = Animation(34, RQUADRATIC, -SIDE)
animCurLvlUp = Animation(34, QUADRATIC, -SCREENLENGTH, [animNexLvlUp])

LEVELSDOWN = 8  # how many levels below current level to show
SHADOWINTERVAL = 255 / (LEVELSDOWN - 1)
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
nexDungs = newSurf((DUNGW * 4, DUNGH + SIDE))
dungRects = []  # used to cut out each dungeon from curDungs
for dung in range(4):
    dungRects.append((dung * DUNGW, 0, DUNGW, DUNGH + SIDE))


# BLITS DUNGEON SIDES FROM SIDESURFS
def blitSide(surf, dung, x, y):
    segment = (dung * DUNGW, sideY + SIDE*2, DUNGW, SIDE * LEVELSDOWN)
    surf.blit(sideSurfs, (x, y), segment)

def drawCov(direction, dung, col, row):
    # IF A WALL IS BELOW YOU, IT SHOULD COVER YOU
    # check two blocks below instead of one when moving down
    if direction == DOWN:
        rowOff = 2
    else:
        rowOff = 1

    # LEFT/RIGHT MOVEMENT REQUIRES A SECOND BLOCK TO BE DRAWN
    # because the sprite extends in that direction
    if direction == LEFT:
        colOff = -1
    elif direction == RIGHT:
        colOff = 1
    else:
        colOff = None

    # draw the other tile that covers the player
    if colOff:
        if curLvl.tileAt(dung, col + colOff, row + 1) in covers:
            curLvl.drawTile(preDisplay, dung, col + colOff, row + 1)

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
        self.origDungs = dungs
        self.origCol = col
        self.origRow = row
        self.dungs = dungs
        self.col = col
        self.row = row
        self.xOff = 0
        self.yOff = 0
        self.variant = variant

moveBoxes = [] # all boxes that should be moved during animation

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
        return False
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

        tileVars = [[[0, 0, 0, 0, 0] for x in range(WIDTH)] for x in range(4)]

        for dung in range(4):
            for col in range(WIDTH):
                for row in range(HEIGHT):
                    tile = self.tileAt(dung, col, row)
                    variant = random.randint(0, tileSheet.varCount[tile])
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
    def drawTile(self, surf, dung, col, row, x = None, y = None):
        # if no position arguments are given, use the default position
        if x == None and y == None:
            pos = (dungX[dung] + col * TILE, dungY[dung] + row * TILE)
        else:
            pos = (x, y)

        # pulls some variables from self
        tile      = self.tileAt(dung, col, row)
        tileSheet = self.tileSheet
        variant   = self.tileVars[dung][col][row]

        # wall tiles consist of two potential parts, and are drawn higher
        if tile == WALL:
            tileSheet.drawTile(surf, pos, WALL, variant)

            # draws side if tile below is not also a wall
            if self.tileAt(dung, col, row + 1) != WALL:
                pos = (pos[0], pos[1] + TILE)
                tileSheet.drawTile(surf, pos, WALLSIDE, variant)



        # all other tiles only consist of one part, and are drawn lower
        elif tile != VOID:
            pos = (pos[0], pos[1] + SIDE)
            tileSheet.drawTile(surf, pos, tile, variant)

            # (doesn't look good) draw shadow if tile above is a wall
            # if self.tileAt(dung, col, row - 1) == WALL:
                # shadow.set_alpha(50)
                # surf.blit(shadow, pos, wallShadow)



    ### DRAWS AN ENTIRE DUNGEON ###
    def drawDung(self, surf, dung, posX = None, posY = None):
        # basically just loops through and draws each tile
        for col in range(WIDTH):
            for row in range(HEIGHT):

                # if no position arguments are given, use the default position
                if posX == None and posY == None:
                    x = dungX[dung] + col*TILE
                    y = dungY[dung] + row*TILE
                else:
                    x = posX + col*TILE
                    y = posY + row*TILE

                self.drawTile(surf, dung, col, row, x, y)




### LOADS THE LEVELS FROM FILE ###
# the level file uses singular letters to represent tiles
V = VOID
E = EMPTY
W = WALL
G = GOAL
S = SWIRL
B = BOX

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
        boxVar = (boxVar + 1) % (buildSheet.varCount[BOX] + 1)
        buildDungs = []
        buildLayout[box[0]][box[1]][box[2]] = levelFile.pop(0)
        for dung in range(4):
            if levelFile.pop(0) == None:
                buildDungs.append(None)
            else:
                buildDungs.append(True)

        finalBoxes.append(Box(buildDungs, box[1], box[2], boxVar))

    # CREATES A LEVEL OBJECT AND ADDS IT TO THE LEVEL LIST
    levels.append(Level(buildLayout, buildSheet, finalBoxes))



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
    oldY = y

    # blit over entire dungeon first
    shadowAlpha = shadowOffset
    shadowAlpha += SHADOWINTERVAL

    shadow.set_alpha(shadowAlpha)
    surf.blit(shadow, (x, y))

    y += DUNGH + SIDE

    # blit each side shadow with a different opacity
    for layer in range(1, LEVELSDOWN + 2):
        shadowAlpha += SHADOWINTERVAL

        shadow.set_alpha(shadowAlpha)
        surf.blit(shadow, (x, y), sideShadow)

        y += SIDE

    # this fixes the green showing overtop of empty tiles during swirl
    for col in range(WIDTH):
        if nexLvl.tileAt(dung, col, 0) != WALL:
            pygame.draw.rect(surf, (0, 255, 0), (x, oldY, TILE, SIDE))
        x += TILE



################################################################################
###                                MENU ..?                                  ###
################################################################################
# the main display, pre-camera
preDisplay = newSurf((SCREENLENGTH, SCREENLENGTH + CAMLIMIT))

# the main display, post-camera
postDisplay = pygame.display.set_mode(SCREENSIZE)


# levelNum can be changed later with the level select
levelNum = 0
if levelNum == 0:
    playDung = RIGHT
    playCol = 0
    playRow = 2

# find the goal in the previous level and start the player from there
else:
    goalExists = False
    for dungNum, dung in enumerate(levels[levelNum - 1].layout):
        for x, col in enumerate(dung):
            for y, tile in enumerate(col):
                if tile == GOAL:
                    playDung = dungNum
                    playCol = x
                    playRow = y
                    goalExists = True

    # if somehow no goal was found, default to the middle of the level
    if not goalExists:
        playDung = LEFT
        playCol = 2
        playRow = 2


# PREDRAWS THE SIDES OF ALL THE LEVELS
# makes a surface that stores level sides for all four dungeons
sideSurfs = newSurf((DUNGW * 4, (len(levels) + 1)*SIDE + TILE+SIDE))

# draws the four dungeons for each level
y = len(levels) * SIDE
for level in reversed(levels):
    y -= SIDE
    for dung in range(4):
        for col in range(WIDTH):
            x = dung*DUNGW + col*TILE
            level.drawTile(sideSurfs, dung, col, HEIGHT-1, x, y)


### PER-LEVEL LOOP ###
while True:

    ############################################################################
    ###                   STUFF THAT RESETS EACH LEVEL                       ###
    ############################################################################

    validBox = None
    moveDirection = None
    boxDirection = None
    ### DRAWING LEVELS ###
    curLvl = levels[levelNum]  # stores reference to current level
    nexLvl = levels[levelNum + 1]  # stores reference to next level
    curLay = newSurf(SCREENSIZE)   # current level's layer
    nexLay = newSurf((SCREENLENGTH, SCREENLENGTH + SIDE))

    curTileSheet = curLvl.tileSheet
    nexTileSheet = nexLvl.tileSheet



    ### ANIMATION STUFF ###
    # NEXT LEVEL
    nexLayY = 0  # resets y values
    curLayY = 0
    sideY = (levelNum + 2) * SIDE

    animCur = None


    ### PREDRAWS BOTH THE CURRENT LEVEL AND THE NEXT LEVEL ###
    curDungs.fill((0, 255, 0))
    nexDungs.fill((0, 255, 0))
    curLay.fill((0, 255, 0))
    nexLay.fill((0, 255, 0))
    for dung in range(4):
        curLvl.drawDung(curDungs, dung, dung * DUNGW, 0)
        curLay.blit(curDungs, (dungX[dung], dungY[dung]), dungRects[dung])

        nexLvl.drawDung(nexDungs, dung, dung * DUNGW, 0)
        nexLay.blit(nexDungs, (dungX[dung], dungY[dung]), dungRects[dung])

        x = dungX[dung]
        y = dungY[dung] + DUNGH + SIDE
        blitSide(nexLay, dung, x, y)

        # DRAWS SHADOWS
        drawNextShadow(nexLay, dung, dungX[dung], dungY[dung], 0)


    # MISC
    # stores player's current position for when reset key is pressed
    startCol = playCol
    startRow = playRow
    startDung = playDung



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
                    # resets camera
                    camXLock = 0
                    camYLock = 0

                    # resets layout and redraws dungeons
                    curLay.fill((0, 255, 0))
                    curDungs.fill((0, 255, 0))

                    curLvl.layout = copy.deepcopy(curLvl.origLayout)
                    curLvl.tileVars = copy.deepcopy(curLvl.origTileVars)
                    for dung in range(4):
                        curLvl.drawDung(curDungs, dung, dung * DUNGW, 0)
                        position = (dungX[dung], dungY[dung])
                        curLay.blit(curDungs, position, dungRects[dung])

                    # resets player
                    playCol = startCol
                    playRow = startRow
                    playDung = startDung

                    # resets all boxes
                    for box in curLvl.boxes:
                        box.col = box.origCol
                        box.row = box.origRow
                        box.dungs = copy.copy(box.origDungs)



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

                if liftedKey in moveQueue:
                    moveQueue.remove(liftedKey)

            elif event.type == pygame.QUIT:
                running = False



        #############
        ### INPUT ###
        #############

        ### MOVEMENT ###
        # if an input was made and no animation is currently playing
        if moveQueue and animQueue == []:

            # start movement animation if you land on a non-wall/non-void tile
            moveDirection = moveQueue[0]

            queryX = playCol
            queryY = playRow
            if moveQueue[0] == LEFT:
                queryX -= 1

            elif moveQueue[0] == RIGHT:
                queryX += 1

            elif moveQueue[0] == UP:
                queryY -= 1

            elif moveQueue[0] == DOWN:
                queryY += 1

            tile = curLvl.tileAt(moveDirection, queryX, queryY)
            moveBoxes = []
            validBox = checkBox(moveDirection, moveDirection, playCol, playRow)

            if validBox and moveBoxes != []:
                boxDirection = moveDirection

            if tile not in (WALL, VOID) and (validBox or moveBoxes == []):
                playDung = moveDirection
                playAnim = playMovement[moveDirection]
                ghostAnim = ghostMovement[moveDirection]

                # a quick fix for the animation not showing the first frame
                playAnim.frame = -1
                ghostAnim.frame = -1

                animQueue.append(playAnim)

            else:
                moveDirection = None

        if moveQueue:
            camDir = moveQueue[0]
            if camDir == LEFT or camDir == RIGHT:
                camXLock = CAMMAXFRAME
            elif camDir == UP or camDir == DOWN:
                camYLock = CAMMAXFRAME



        ##################
        ### ANIMATIONS ###
        ##################

        ### ALL QUEUED ANIMATIONS ###
        # increments these animations one at a time
        if animQueue:
            animCur = animQueue[0]

            # LAST FRAME STUFF
            if animCur.frame == animCur.lastFrame:
                animCur.resetAnim()

                # SPECIFIC TO PLAYER MOVEMENT
                if animCur is playAnim:
                    playCol = queryX       # update the player's position
                    playRow = queryY

                    tile = curLvl.tileAt(playDung, playCol, playRow)
                    if tile == SWIRL:
                        animQueue.append(animRotate)

                    elif tile == GOAL:
                        animQueue.append(animPlayDrop)
                        animQueue.append(animCurLvlUp)

                    playAnim = playIdle  # reset the sprite to idle
                    ghostAnim = ghostIdle


                    # BOX STUFF
                    for box in moveBoxes:
                        if moveDirection == LEFT:
                            box.col -= 1
                        elif moveDirection == RIGHT:
                            box.col += 1
                        elif moveDirection == UP:
                            box.row -= 1
                        elif moveDirection == DOWN:
                            box.row += 1

                        box.xOff = 0
                        box.yOff = 0

                    moveBoxes = []

                    moveDirection = None
                    boxDirection = None



                # SPECIFIC TO DUNGEON ROTATION
                elif animCur is animRotate:
                    # UPDATE PLAYER DUNG
                    playDung = (playDung + 1) % 4

                    # UPDATE LAYOUT
                    curLvl.layout.insert(0, curLvl.layout[3])
                    del curLvl.layout[4]

                    # UPDATE BOXES
                    for box in curLvl.boxes:
                        box.dungs.insert(0, box.dungs[3])
                        del box.dungs[4]

                    curLvl.tileVars.insert(0, curLvl.tileVars[3])
                    del curLvl.tileVars[4]

                    # RESET DUNGEON POSITIONS
                    dungX = copy.copy(origDungX)
                    dungY = copy.copy(origDungY)

                    # REDRAW THE DUNGEONS IN THEIR RESET POSITIONS
                    curDungs.fill((0, 255, 0))
                    curLay.fill((0, 255, 0))
                    for dung in range(4):
                        curLvl.drawDung(curDungs, dung, dung * DUNGW, 0)
                        position = (dungX[dung], dungY[dung])
                        curLay.blit(curDungs, position, dungRects[dung])





                # SPECIFIC TO PLAYER DROP DURING NEXT LEVEL TRANSITION
                elif animCur is animPlayDrop:
                    # skips a frame of animation
                    animQueue.remove(animCur)
                    continue

                # SPECIFIC TO NEXT LEVEL TRANSITION
                elif animCur is animCurLvlUp:
                    levelNum += 1
                    nextLevel = True

                    # exits game loop and goes to the next level
                    animQueue.remove(animCur)
                    break

                animQueue.remove(animCur) # deletes animation from queue



            # ALL OTHER FRAMES
            else:
                # INCREMENT FRAME AND VALUES
                animCur.nextFrame()


                # SPECIFIC TO PLAYER MOVEMENT (mostly just box stuff)
                if animCur is playAnim:
                    for box in moveBoxes:

                        if moveDirection == LEFT:
                            box.xOff = -animBoxSlide.value

                        elif moveDirection == RIGHT:
                            box.xOff = animBoxSlide.value

                        elif moveDirection == UP:
                            box.yOff = -animBoxSlide.value

                        elif moveDirection == DOWN:
                            box.yOff = animBoxSlide.value


                # SPECIFIC TO DUNGEON ROTATION
                if animCur is animRotate:

                    curLay.fill((0, 255, 0))

                    # CALCULATES WHERE ON THE CIRCLE TO DRAW THE LEVEL
                    for dung in range(4):
                        angle = (dung + 2) % 4 * 90
                        angle += animCur.value
                        angle = math.radians(angle)

                        x = ROTATEMIDX + math.cos(angle) * ROTATERADIUS
                        y = ROTATEMIDY + math.sin(angle) * ROTATERADIUS

                        dungX[dung] = x
                        dungY[dung] = y

                        curLay.blit(curDungs, (x, y), dungRects[dung])



                # SPECIFIC TO NEXT LEVEL TRANSITION
                elif animCur is animCurLvlUp:
                    # moves everything up
                    curLayY = round(animCurLvlUp.value)
                    nexLayY = round(animNexLvlUp.value)

                    nexLay.fill((0, 0, 0))

                    for dung in range(4):
                        # redraws dungeons
                        nexLay.blit(nexDungs, (dungX[dung], dungY[dung]), dungRects[dung])

                        # redraws the side layer
                        x = dungX[dung]
                        y = dungY[dung] + DUNGH + SIDE
                        blitSide(nexLay, dung, x, y)

                        # redraws the shadows, with an offset based on the frame
                        shadowOff = - NEXTSHADOWINTERVAL * animCur.frame
                        drawNextShadow(nexLay, dung, dungX[dung], dungY[dung], shadowOff)

                    camXLock = 0  # resets camera
                    camYLock = 0

                    # DRAW BOXES
                    for box in nexLvl.boxes:
                        for dung in range(4):
                            if box.dungs[dung] != None:
                                x = dungX[dung] + box.col * TILE
                                y = dungY[dung] + box.row * TILE + nexLayY
                                nexTileSheet.drawTile(preDisplay, (x, y), BOX, box.variant)

                                if nexLvl.tileAt(dung, box.col, box.row + 1) in covers:
                                    nexLvl.drawTile(preDisplay, dung, box.col, box.row + 1)


        else:   # resets if there are no animations playing
            animCur = None







        ##########################
        ### DRAWING EVERYTHING ###
        ##########################

        ### SIDE OF NEXT DUNGEONS & NEXT LEVEL ###
        preDisplay.blit(nexLay, (0, nexLayY + SIDE))

        if animCur is animCurLvlUp:
            for box in nexLvl.boxes:
                for dung in range(4):
                    if box.dungs[dung] != None:
                        x = dungX[dung] + box.col * TILE
                        y = dungY[dung] + box.row * TILE + SIDE + nexLayY

                        nexTileSheet.drawTile(preDisplay, (x, y), BOX, box.variant)

                        if nexLvl.tileAt(dung, box.col, box.row + 1) in covers:
                            nexLvl.drawTile(preDisplay, dung, box.col, box.row + 1, x, y + TILE)

        ### DUNGEONS ###
        preDisplay.blit(curLay, (0, curLayY))

        ### BOXES ABOVE PLAYER ###
        for row in range(playRow + 1):
            for box in curLvl.boxes:
                if box.row == row:
                    for dung in range(4):
                        if box.dungs[dung] != None:
                            x = dungX[dung] + box.col * TILE + box.xOff
                            y = dungY[dung] + box.row * TILE + box.yOff + curLayY

                            curTileSheet.drawTile(preDisplay, (x, y), BOX, box.variant)

                            if curLvl.tileAt(dung, box.col, box.row + 1) in covers:
                                curLvl.drawTile(preDisplay, dung, box.col, box.row + 1)
                            elif box in moveBoxes:
                                drawCov(boxDirection, dung, box.col, box.row)
                            else:
                                drawCov(None, dung, box.col, box.row)

        ### PLAYER ###
        for dung in range(4):
            playX = dungX[dung] + (playCol - 1) * TILE
            playY = dungY[dung] + (playRow - 1) * TILE

            ### CHANGE THE PLAYER'S POSITION BASED ON THE CURRENT ANIMATION ###
            if animCur is animPlayDrop:
                playY += animPlayDrop.value

            elif animCur is animCurLvlUp:
                playY += nexLayY + SIDE



            ### DRAW THE PLAYER (and the ghosts) ###
            if playDung == dung:
                playAnim.blitFrame(preDisplay, (playX, playY))
            else:
                ghostAnim.blitFrame(preDisplay, (playX, playY))


            ### DRAWS BLOCKS THAT SHOULD OVERLAP THE PLAYER (and ghosts)###
            if animCur is animPlayDrop:

                # draws block directly below player.  no exceptions
                if nexLvl.tileAt(dung, playCol, playRow + 1):
                    curLvl.drawTile(preDisplay, dung, playCol, playRow + 1)

                # flat tiles will cover the wall below it so redraw that wall
                if curLvl.tileAt(dung, playCol, playRow + 2) in covers:
                    curLvl.drawTile(preDisplay, dung, playCol, playRow + 2)


            elif animCur is animCurLvlUp:
                x = dungX[dung] + playCol * TILE

                # draws wall beneath player on next level
                if nexLvl.tileAt(dung, playCol, playRow + 1) in covers:
                    y = playY + TILE + TILE

                    nexLvl.drawTile(preDisplay, dung, playCol, playRow + 1, x, y)

                    # draw a single-block shadow onto the wall
                    shadowAlpha = - NEXTSHADOWINTERVAL * animCur.frame + SHADOWINTERVAL
                    shadow.set_alpha(shadowAlpha)
                    preDisplay.blit(shadow, (x, y), tileShadow)


                # draws the column of blocks that overlap the player
                # during first half, only draw blocks below the player
                if animCur.frame < animCur.lastFrame / 2:

                    # a wall will start higher up from the other blocks
                    if curLvl.tileAt(dung, playCol, playRow + 1) in covers:
                        y = dungY[dung] + playRow * TILE + TILE
                    else:
                        y = dungY[dung] + playRow * TILE + TILE + SIDE

                # during second half, top ghost is covered by bottom dungeon
                else:
                    # so draw the entire column
                    y = dungY[dung]

                section = (x, y, TILE, DUNGH)
                preDisplay.blit(curLay, (x, y + curLayY), section)



            else:   # normal movement
                drawCov(moveDirection, dung, playCol, playRow)



        ### BOXES BELOW PLAYER ###
        for row in range(playRow + 1, HEIGHT):
            for box in curLvl.boxes:
                if box.row == row:
                    for dung in range(4):
                        if box.dungs[dung] != None:
                            x = dungX[dung] + box.col * TILE + box.xOff
                            y = dungY[dung] + box.row * TILE + box.yOff + curLayY

                            curTileSheet.drawTile(preDisplay, (x, y), BOX, box.variant)

                            if animCur == animCurLvlUp:
                                if curLvl.tileAt(dung, box.col, box.row + 1) in covers:
                                    curLvl.drawTile(preDisplay, dung, box.col, box.row + 1)
                            elif box in moveBoxes:
                                drawCov(boxDirection, dung, box.col, box.row)
                            else:
                                drawCov(None, dung, box.col, box.row)



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
        # there's nothing here lol


        ### DEBUGGING ###
        #print(animNextLevel.frame, dungLayer.get_alpha())
        fps = TAHOMA.render(str(round(clock.get_fps())), False, (255, 255, 255))
        postDisplay.blit(fps, (10, 10))

        debug1 = TAHOMA.render(str(levelNum * 20), False, (255, 255, 255))
        debug2 = TAHOMA.render(str(moveDirection), False, (255, 255, 255))
        debug3 = TAHOMA.render(str(boxDirection), False, (255, 255, 255))
        debug4 = TAHOMA.render(repr(moveBoxes), False, (255, 255, 255))

        postDisplay.blit(debug1, (10, 20))
        postDisplay.blit(debug2, (10, 30))
        postDisplay.blit(debug3, (10, 40))
        postDisplay.blit(debug4, (10, 50))
        if debugPressed:
            clockTick = 5   # slow down game when the debug button is pressed
        else:
            clockTick = 60

        #postDisplay.blit(nexLay, (0, -200))


        ### FINAL OUTPUT ###
        pygame.display.flip()        # display the screen

        preDisplay.fill((0, 0, 0))   # clear the screen
        postDisplay.fill((0, 0, 0))

        clock.tick(clockTick)        # keeps the FPS at a consistent 60



        # exits loops when window is closed
        if not running:
            break

    if not running:
        break



pygame.quit()
