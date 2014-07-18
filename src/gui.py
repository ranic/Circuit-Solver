from Tkinter import *
import tkSimpleDialog
import tkFileDialog
from circuit import *
import pickle

#  Constants
CELL_SIZE = 20
OFFSCREEN = (-50, -50)
R_VOLTAGE = 20

#########################################################################
## Taking human/time input (mousePressed, motion, keyPressed, timerFired)
#########################################################################

### MOUSE PRESSED FUNCTIONS ###

def mousePressed(event):
    # accounts for clicking again to de-select something
    canvas.data.isClicked = not canvas.data.isClicked
    if canvas.data.drawWire: # starts drawing a wire
        mousePressedWire(event)
    else:
        mousePressedVoltage(event)
        mousePressedResistor(event)
        mousePressedNode(event)

# Adds the initial coordiantes of the click to the list of wires,
# which will be drawn each time
def mousePressedWire(event):
    if inBounds(event.x,event.y):
        x,y = snapToGrid(event.x,event.y)
        if canvas.data.isClicked:
            canvas.data.currentWire = Wire((x,y), (x,y))
        else:
            # If wire drawn on same point, delete it
            if canvas.data.currentWire.src != canvas.data.currentWire.dest:
                canvas.data.circuit.addElement(canvas.data.currentWire)
            canvas.data.currentWire = None

# Mouse pressed actions if user selects a Voltage Source
def mousePressedVoltage(event):
    # if the user selects a voltage source
    if canvas.data.isClicked and isVoltageSource(event.x,event.y):
        canvas.data.draggingVoltage = True
        canvas.data.clickedVoltage = (event.x,event.y) # start dragging it
    # When dropping the object, it's added to the grid
    elif not canvas.data.isClicked and canvas.data.draggingVoltage:
        if inBounds(event.x,event.y):
            x,y = snapToGrid(event.x,event.y)
            addVoltageToGrid(x,y)

# Initializes voltage and adds it to the grid
# Also creates a connection object between the two nodes and stores
# the voltage source as that connection
def addVoltageToGrid(x,y):
    canvas.data.clickedVoltage = (x,y)
    canvas.data.draggingVoltage = False
    vPrompt = ("Voltage Entry","Enter voltage in Volts")
    voltValue = 0
    # waits till a user selects a non-zero voltage value
    while voltValue == 0:
        voltValue = tkSimpleDialog.askfloat(vPrompt[0],vPrompt[1])
        # If the user cancels, remove the voltage source
        if voltValue == None:
            canvas.data.clickedVoltage = (-50,-50)
            break
    # Otherwise, create the connection object for the voltage
    if voltValue != None:
        a = VoltageSource((x,y + 40),(x,y-40), voltValue)
        canvas.data.circuit.addElement(a)
    # adds ground to the bottom of the first voltage source
    if len(canvas.data.circuit.voltageSources()) == 1 and voltValue != None:
        canvas.data.circuit.addGround((x,y + 40))

# Mouse pressed actions if user selects a Resistor
def mousePressedResistor(event):
    #  When picking up ther resistor...
    if canvas.data.isClicked and isResistor(event.x,event.y):
        canvas.data.draggingResistor = True
        canvas.data.clickedResistor = (event.x,event.y) # start dragging
    #  When dropping the resistor, it's added to the grid
    elif not canvas.data.isClicked and canvas.data.draggingResistor:
        if inBounds(event.x,event.y):
            (x,y) = snapToGrid(event.x,event.y)
            addResistorToGrid(x,y)

# Adds the resistor to the circuit, initializing it with a user-entered resistance. Same idea as the voltage source
def addResistorToGrid(x,y):
    canvas.data.clickedResistor = x,y
    canvas.data.draggingResistor = False
    rPrompt = ("Resistance Entry","Enter resistance in Ohms")
    resistance = 0
    while resistance <= 0:
        resistance = tkSimpleDialog.askfloat(rPrompt[0],rPrompt[1])
        # If the user cancels the resistance selection, the resistor disappears
        # and is not added to the circuit
        if resistance == None:
            canvas.data.clickedResistor = -50,-50
            break
    if resistance != None:
        b = Resistor((x-40,y),(x + 40,y), resistance)
        canvas.data.circuit.addElement(b)

# When the user clicks on a node after solving the circuit,
# it is allowed to be displayed
def mousePressedNode(event):
    if not canvas.data.circuit.solved:
        pass
    else:
        if type(isNode(event.x,event.y)) == tuple:
            nodeLocation,nodeVoltage = isNode(event.x,event.y)
            canvas.data.displayedNode = (nodeLocation,nodeVoltage)

### MOTION FUNCTIONS  ###

def motion(event):
    if inBounds(event.x,event.y):
        if canvas.data.drawWire:
            motionWire(event)
        elif canvas.data.draggingVoltage:
            motionVoltage(event)
        elif canvas.data.draggingResistor:
            motionResistor(event)
        elif canvas.data.draggingGround:
            motionGround(event)

def motionWire(event):
    # Draw wire as user drags mouse
    if canvas.data.currentWire is not None and canvas.data.isClicked:
        canvas.data.currentWire.dest = snapToGrid(event.x,event.y)

# Draws voltage as the cursor moves
def motionVoltage(event):
    drawVoltageSource(event.x,event.y)
    canvas.data.clickedVoltage = (event.x,event.y)

# Same for resistor
def motionResistor(event):
    drawResistor(event.x,event.y)
    canvas.data.clickedResistor = (event.x,event.y)

def drawMotionElements():
    cx,cy = canvas.data.clickedVoltage
    rx,ry = canvas.data.clickedResistor
    drawVoltageSource(cx,cy)
    drawResistor(rx,ry)

def keyPressed(event):
    key = event.keysym.lower()

    # Solves circuit
    if key == "c":
        canvas.data.circuit.solve()
        canvas.data.drawWire = False
    # Reset
    if key == "r":
        init()
    # Print's what's on the circuit
    if key == "p":
        print canvas.data.circuit
    # shows element pane
    if key =="e":
        canvas.data.showElementPane = not canvas.data.showElementPane
    # allows user to draw wire
    if key == "w":
        canvas.data.drawWire = not canvas.data.drawWire
    #  save to file
    if key == "s":
        filename = tkFileDialog.asksaveasfilename()
        with open(filename, 'w') as f:
            pickle.dump(canvas.data.circuit, f)
    if key == "l":
        filename = tkFileDialog.askopenfilename()
        with open(filename, 'r') as f:
             circuit = pickle.load(f)
        init()
        canvas.data.circuit = circuit

    redrawAll()

def timerFired():
    redrawAll()
    drawMotionElements()
    delay = 10 # milliseconds
    canvas.after(delay,timerFired)

#################################################################
## Visual elements (drawGrid, drawElements, etc.)
#################################################################

# Draws the instruction pane on the bottom right corner
def drawInstructions():
    instructCoords = [(400,425),(502,510)]
    canvas.create_rectangle(instructCoords,fill="white")
    canvas.create_text(450,435,text="INSTRUCTIONS")
    canvas.create_text(405,450,text="'e' for element pane",anchor=W,
    font= "helvetica 10")
    canvas.create_text(405,495,text="'w' to draw wire",anchor=W,
    font= "helvetica 10")
    canvas.create_text(405,480,text="'c' to solve circuit",anchor=W,
    font= "helvetica 10")
    canvas.create_text(405,465,text="'r' to reset",anchor=W,
    font= "helvetica 10")

# Draws element pane and node voltage (if circuit is solved)
def drawElementPane():
    paneCoords = [(400,0),(510,510)]
    canvas.create_rectangle(paneCoords,fill = "grey")
    canvas.create_text(450,20,text="Elements",font = "helvetica 19")
    drawVoltageSource(450,100)
    drawResistor(450,180)
    if canvas.data.circuit.solved:
        font = "helvetica 9"
        text = "Solved!\nClick a node\nto display \nnode voltage."
        canvas.create_text(450,300,text=text)


def getCenter(element):
    """ Returns tuple of an element's center coordinates """
    src = element.src
    dest = element.dest

    return ((src[0] + dest[0])/2,(src[1] + dest[1])/2)

# Displays node location and voltage if user clicks a node
def displayNodeVoltage():
    if canvas.data.circuit.solved and canvas.data.displayedNode[1] != -50:
        if not canvas.data.circuit.unsolvable:
            (nodeLocation,nodeVoltage) = canvas.data.displayedNode
            text = "Node at %s has voltage %.2f V" % (nodeLocation,nodeVoltage)
            font = "helvetica 14"
            canvas.create_text(200,450,text=text,font=font,fill ="red")


def displayWireMode():
    if canvas.data.drawWire:
        text = "Wire mode: Click to start a wire, press 'w' to exit"
        font = "helvetica 14"
        canvas.create_text(200,400,text=text,font=font,fill ="red")

# Function that draws a resistor
def drawResistor(cx,cy):
    # c represents the 'center' of the resistor, where it's length is 80 pixels
    eLeft,eRight = cx-2*CELL_SIZE,cx + 2*CELL_SIZE # left and right endpoints
    halfCell = CELL_SIZE/2
    canvas.create_line(eLeft,cy,eRight,cy,fill="yellow")
    canvas.create_rectangle(eLeft + CELL_SIZE,cy + halfCell/2,
    eRight-CELL_SIZE,cy-halfCell/2,fill="red")

# Function that draws a voltage source
def drawVoltageSource(cx, cy):
    r = R_VOLTAGE
    canvas.create_line(cx,cy + 2*r,cx,cy-2*r,fill="yellow")
    canvas.create_oval(cx-r,cy-r,cx + r,cy + r,fill = "white")
    canvas.create_text(cx,cy,text=" + \n -",font = "helevetica 14")

# Function to create ground
def drawGround(x,top):
    canvas.create_line(x,top,x,top + 10,fill="brown")
    canvas.create_line(x-10,top + 15,x + 10,top + 15,fill="brown",width=2)
    canvas.create_line(x-5,top + 20,x + 5,top + 20,fill="brown",width=2)
    canvas.create_line(x-2,top + 25,x + 2,top + 25,fill="brown")

# Generates grid , element pane, instructions, and node voltage
def background():
    if canvas.data.showElementPane:
        drawElementPane()
    drawInstructions()
    displayNodeVoltage()
    displayWireMode()

# Draws each voltage source, resistor, ground, and 'unsolvable'
# if it applies
def drawCircuit():
    for voltageSource in canvas.data.circuit.voltageSources():
        drawVoltageSource(*getCenter(voltageSource))
    for wire in canvas.data.circuit.wires():
        x1, y1 = wire.src
        x2, y2 = wire.dest
        canvas.create_line(x1,y1,x2,y2,fill="yellow")

    if canvas.data.currentWire is not None:
        x1, y1 = canvas.data.currentWire.src
        x2, y2 = canvas.data.currentWire.dest
        canvas.create_line(x1,y1,x2,y2,fill="yellow")

    for resistor in canvas.data.circuit.resistors():
        drawResistor(*getCenter(resistor))
    if (canvas.data.circuit.ground):
        ground = canvas.data.circuit.ground
        drawGround(ground[0], ground[1])
    if canvas.data.circuit.unsolvable:
        font = "helvetica 20"
        canvas.create_text(250,450,text="UNSOLVABLE",font=font,fill = "red")

# Draws the background and circuit
def redrawAll():
    canvas.delete(ALL)
    background()
    drawCircuit()

#################################################################
## General helper functions
#################################################################

# Checks if the item is in bounds of the grid
def inBounds(x,y):
    return (x>0 and y>0) and (x<400 and y<500)

# Checks if a voltage source is selected
def isVoltageSource(x,y):
    return ((430 <= x <= 470) and (60 <= y <= 140))

# Checks if the user selects a resistor from the element pane
def isResistor(x,y):
    return ((420 <= x <= 480) and (170 <= y <= 190))

# After the circuit is solved, checks which node the user selects
# and stores that node's location and voltage into a display variable
def isNode(x,y):
    nodes = canvas.data.circuit.nodes
    for node in canvas.data.circuit.nodes:
        # allows for leeway in where the user clicks
        if node[0] in range(x-CELL_SIZE,x + CELL_SIZE):
            if node[1] in range(y-CELL_SIZE,y + CELL_SIZE):
                canvas.data.displayedNode = (node,nodes[node].voltage)
                return canvas.data.displayedNode
    return False

# Uses the "closest bus stop" solution to snap the pieces to the nodes
def snapToGrid(x,y):
    a = CELL_SIZE/2
    snappedX = ((x + a)/CELL_SIZE)*CELL_SIZE
    snappedY = ((y + a)/CELL_SIZE)*CELL_SIZE
    return snappedX,snappedY

#################################################################
## Initialize canvas.data and run
#################################################################

def init():
    canvas.data.circuit = Circuit()
    visualElementInit()
    background()

def visualElementInit():
    canvas.data.showElementPane = True
    canvas.data.isClicked = False
    canvas.data.drawWire = False
    canvas.data.isClicked = True
    canvas.data.draggingVoltage = False
    canvas.data.clickedVoltage = OFFSCREEN
    canvas.data.draggingResistor = False
    canvas.data.clickedResistor = OFFSCREEN
    canvas.data.draggingGround = False
    canvas.data.drawWire = False
    canvas.data.displayedNode = OFFSCREEN
    canvas.data.currentWire = None

def run():
    #  create the root and the canvas
    global canvas
    root = Tk()
    # creates background for grid
    canvas = Canvas(root, width=500, height=500,bg = "Black")
    canvas.pack()
    root.resizable(False,False) # keeps the grid constant
    root.canvas = canvas.canvas = canvas
    #  Set up canvas data and call init
    class Struct: pass
    canvas.data = Struct()
    init()
    redrawAll()
    #  set up keyPressed
    root.bind("<Button-1>", mousePressed)
    root.bind("<Key>", keyPressed)
    root.bind("<Motion>",motion)
    timerFired()
    root.mainloop()

run()
