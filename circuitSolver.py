# Term Project: Circuit Solver
# Author: Vijay Jayaram, vijayj, Section H
# Mentor: Dylan Swen

from Tkinter import *
import tkSimpleDialog
import tkFileDialog
import pickle
from numpy import *

# Constants
CELL_SIZE = 20
OFFSCREEN = (-50, -50)

# TODO: Saving and loading state

####################################################
## Classes for circuit elements
####################################################

#Only one circuit instance is created, holds all the nodes
class Circuit(object):
    def __init__(self):
        self.nodes = dict()
        self.ground = None

    def addElement(self, element):
        """ Create and add an element to the circuit """
        src, dest = element.src, element.dest
        if src not in self.nodes:
            self.nodes[src] = Node(src)
        if dest not in self.nodes:
            self.nodes[dest] = Node(dest)
        self.nodes[src].addElement(element)
        self.nodes[dest].addElement(element.inverse())

    def addGround(self,location):
        self.ground = location

    def __str__(self):
        elementStr = "\n".join(["\n".join(map(str,v.elements)) \
                                    for (k,v) in self.nodes.iteritems()])
        return "%s\n Ground: %s" % (elementStr, self.ground)

    ####################################################
    ## Function that solves the circuit
    ####################################################

    def solve(self):
        canvas.data.circuit.unsolvable = False
        canvas.data.displayAnswer = False

        # A circuit with no voltage sources is unsolvable
        if len(canvas.data.voltageSources) == 0:
            canvas.data.circuit.unsolvable = True
            return

        # Map each node location to a variable in the system of equations (column in the matrix)
        self.nodeToCol = dict((k, i) for i, (k,_) in enumerate(self.nodes.iteritems()))
        self.dim = len(self.nodes)

        try:
            solution = solveMatrix(self.createEquations())
        except linalg.LinAlgError as e:
            print e
            canvas.data.circuit.unsolvable = True
            return

        for loc, node in self.nodes.iteritems():
            node.voltage = solution[self.nodeToCol[loc]][0]

        canvas.data.displayAnswer = True

    #Creates each node equation using a KCL (if needed)
    #Goes through each node, starting with ground
    #Stores all these equations in the matrix 'voltages'
    def createEquations(self):
        voltages = []

        # Ground equation forces ground node to be 0 volts
        groundEquation = [0]*(self.dim + 1)
        groundEquation[self.nodeToCol[self.ground]] = 1
        voltages.append(groundEquation)

        canKCL = False

        for loc, node in self.nodes.iteritems():
            # First, create all voltage source equations
            for element in node.elements:
                src = self.nodeToCol[element.src]
                dest = self.nodeToCol[element.dest]

                # Equation is n1 - n2 = voltageValue for voltage sources
                if isinstance(element, VoltageSource):
                    equation = [0]*(self.dim + 1)
                    equation[src] = 1
                    equation[dest] = -1
                    equation[self.dim] = -element.voltage
                    voltages.append(equation)

            # Next, use KCL to produce equations for nodes connecting resistors
            if any([isinstance(e, Resistor) for e in node.elements]):
                equation = [0]*(self.dim + 1)
                self.recursivelyFindCurrent(loc, set(), equation)
                voltages.append(equation)
        return voltages

    def recursivelyFindCurrent(self, location, visited, equation):
        """ Find current using either Ohm's law or recursively with KCL """
        for element in self.nodes[location].elements:
            #if the connection was already visited, don't do anything
            #otherwise, this would recurse infinitely
            if element not in visited:
                visited.add(element)

                #Base case: two nodes are connected by a resistor
                if isinstance(element, Resistor):
                    srcIndex = self.nodeToCol[element.src]
                    destIndex = self.nodeToCol[element.dest]

                    # Equation is src - dest (normalized by R)
                    equation[srcIndex] += 1.0/element.resistance
                    equation[destIndex] += -1.0/element.resistance

                #Recursive case: nodes connected by a non-resistive element
                #Go through using KCLs and add them up to get the current
                else:
                    self.recursivelyFindCurrent(element.dest, visited, equation)

class Element:

    def __init__(self, src, dest):
        """ src and dest are tuples representing the element's grid location """
        self.src = src
        self.dest = dest
        # Populated when circuit is solved
        self.current = None

    def resetCurrent(self, value=None):
        self.current = value

    def __str__(self):
        return "src: %s, dest: %s" % (self.src, self.dest)

    def inverse(self):
        raise NotImplementedError

class VoltageSource(Element):

    def __init__(self, src, dest, voltage):
        Element.__init__(self, src, dest)
        self.voltage = voltage

    # TODO: Don't return a separate element for this...
    def inverse(self):
        return VoltageSource(self.dest, self.src, -self.voltage)

    def __str__(self):
        s = Element.__str__(self)
        return "Voltage Source: %s, voltage: %0.3f" % (s, self.voltage)

class Resistor(Element):

    def __init__(self, src, dest, resistance):
        Element.__init__(self, src, dest)
        self.resistance = resistance

    # TODO: Don't return a separate element for this...
    def inverse(self):
        return Resistor(self.dest, self.src, self.resistance)

    def __str__(self):
        s = Element.__str__(self)
        return "Resistor: %s, resistance: %0.3f" % (s, self.resistance)

class Node(object):
    def __init__(self,location,voltage=0,current=0):
        self.elements = []
        self.location = location
        self.voltage = voltage
        self.current = current

    def addElement(self, element):
        assert(self.location == element.src)
        self.elements.append(element)

#################################################################
## General helper functions
#################################################################

#Checks if the item is in bounds of the grid
def inBounds(x,y):
    return (x>0 and y>0) and (x<400 and y<500)

#Checks if a voltage source is selected
def isVoltageSource(x,y):
    return ((430 <= x <= 470) and (60 <= y <= 140))

#Checks if the user selects a resistor from the element pane
def isResistor(x,y):
    return ((420 <= x <= 480) and (170 <= y <= 190))

#After the circuit is solved, checks which node the user selects
#and stores that node's location and voltage into a display variable
def isNode(x,y):
    nodes = canvas.data.circuit.nodes
    for node in canvas.data.circuit.nodes:
        #allows for leeway in where the user clicks
        if node[0] in range(x-CELL_SIZE,x + CELL_SIZE):
            if node[1] in range(y-CELL_SIZE,y + CELL_SIZE):
                canvas.data.displayedNode = (node,nodes[node].voltage)
                return canvas.data.displayedNode
    return False

#Uses the "closest bus stop" solution to snap the pieces to the nodes
def snapToGrid(x,y):
    a = CELL_SIZE/2
    snappedX = ((x + a)/CELL_SIZE)*CELL_SIZE
    snappedY = ((y + a)/CELL_SIZE)*CELL_SIZE
    return snappedX,snappedY

#########################################################################
## Taking human/time input (mousePressed, motion, keyPressed, timerFired)
#########################################################################

### MOUSE PRESSED FUNCTIONS ###

def mousePressed(event):
    #accounts for clicking again to de-select something
    canvas.data.isClicked = not canvas.data.isClicked
    if canvas.data.drawWire: #starts drawing a wire
        mousePressedWire(event)
    else:
        mousePressedVoltage(event)
        mousePressedResistor(event)
        mousePressedNode(event)

#Adds the initial coordiantes of the click to the list of wires,
#which will be drawn each time
def mousePressedWire(event):
    if inBounds(event.x,event.y):
        x,y = snapToGrid(event.x,event.y)
        if canvas.data.isClicked:
            canvas.data.wires.append([(x,y),(x,y)])
        else:
            lastWire = canvas.data.wires[-1]
            #treats wire as a voltage source and adds it as an object
            if lastWire[0]!=lastWire[1]:
                element = VoltageSource(lastWire[0],lastWire[1], 0)
                canvas.data.circuit.addElement(element)

#Mouse pressed actions if user selects a Voltage Source
def mousePressedVoltage(event):
    #if the user selects a voltage source
    if canvas.data.isClicked and isVoltageSource(event.x,event.y):
        canvas.data.draggingVoltage = True
        canvas.data.clickedVoltage = (event.x,event.y) #start dragging it
    #When dropping the object, it's added to the grid
    elif not canvas.data.isClicked and canvas.data.draggingVoltage:
        if inBounds(event.x,event.y):
            x,y = snapToGrid(event.x,event.y)
            addVoltageToGrid(x,y)

#Initializes voltage and adds it to the grid
#Also creates a connection object between the two nodes and stores
#the voltage source as that connection
def addVoltageToGrid(x,y):
    canvas.data.clickedVoltage = (x,y)
    canvas.data.draggingVoltage = False
    vPrompt = ("Voltage Entry","Enter voltage in Volts")
    voltValue = 0
    #waits till a user selects a non-zero voltage value
    while voltValue == 0:
        voltValue = tkSimpleDialog.askfloat(vPrompt[0],vPrompt[1])
        #If the user cancels, remove the voltage source
        if voltValue == None:
            canvas.data.clickedVoltage = (-50,-50)
            break
    #Otherwise, create the connection object for the voltage
    if voltValue != None:
        canvas.data.voltageSources.add(canvas.data.clickedVoltage)
        a = VoltageSource((x,y + 40),(x,y-40), voltValue)
        canvas.data.circuit.addElement(a)
    #adds ground to the bottom of the first voltage source
    if len(canvas.data.voltageSources) == 1 and voltValue != None:
        canvas.data.grounds = (x,y + 40)
        canvas.data.circuit.addGround((x,y + 40))

#Mouse pressed actions if user selects a Resistor
def mousePressedResistor(event):
    #When picking up ther resistor...
    if canvas.data.isClicked and isResistor(event.x,event.y):
        canvas.data.draggingResistor = True
        canvas.data.clickedResistor = (event.x,event.y) #start dragging
    #When dropping the resistor, it's added to the grid
    elif not canvas.data.isClicked and canvas.data.draggingResistor:
        if inBounds(event.x,event.y):
            (x,y) = snapToGrid(event.x,event.y)
            addResistorToGrid(x,y)

#Adds the resistor to the circuit, initializing it with a user-entered resistance. Same idea as the voltage source
def addResistorToGrid(x,y):
    canvas.data.clickedResistor = x,y
    canvas.data.draggingResistor = False
    rPrompt = ("Resistance Entry","Enter resistance in Ohms")
    resistance = 0
    while resistance <= 0:
        resistance = tkSimpleDialog.askfloat(rPrompt[0],rPrompt[1])
        #If the user cancels the resistance selection, the resistor disappears
        #and is not added to the circuit
        if resistance == None:
            canvas.data.clickedResistor = -50,-50
            break
    if resistance != None:
        canvas.data.resistors.add(canvas.data.clickedResistor)
        b = Resistor((x-40,y),(x + 40,y), resistance)
        canvas.data.circuit.addElement(b)

#When the user clicks on a node after solving the circuit,
#it is allowed to be displayed
def mousePressedNode(event):
    if not canvas.data.displayAnswer:
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
    if len(canvas.data.wires) != 0:
        #draws only the wire that was just added to the list
        lastWire = canvas.data.wires[-1]
        if canvas.data.isClicked:
            lastWire[1] = snapToGrid(event.x,event.y) #draw wire as user drags

#Draws voltage as the cursor moves
def motionVoltage(event):
    drawVoltageSource(event.x,event.y,20)
    canvas.data.clickedVoltage = (event.x,event.y)

#Same for resistor
def motionResistor(event):
    drawResistor(event.x,event.y)
    canvas.data.clickedResistor = (event.x,event.y)

def drawMotionElements():
    cx,cy = canvas.data.clickedVoltage
    rx,ry = canvas.data.clickedResistor
    drawVoltageSource(cx,cy,20)
    drawResistor(rx,ry)

def keyPressed(event):
    key = event.keysym.lower()

    #Solves circuit
    if key == "c":
        canvas.data.circuit.solve()
        canvas.data.drawWire = False
    #Reset
    if key == "r":
        init()
    #Print's what's on the circuit
    if key == "p":
        print canvas.data.circuit
    #shows element pane
    if key =="e":
        canvas.data.showElementPane = not canvas.data.showElementPane
    #allows user to draw wire
    if key == "w":
        canvas.data.drawWire = not canvas.data.drawWire
    # save to file
    if key == "s":
        filename = tkFileDialog.asksaveasfilename()
        with open(filename, 'w') as f:
            pickle.dump(canvas.data, f)
    if key == "l":
        filename = tkFileDialog.askopenfilename()
        #with open(filename, 'r') as f:
        #    canvas.data = pickle.load(f)
    redrawAll()

def timerFired():
    redrawAll()
    drawMotionElements()
    delay = 10 #milliseconds
    canvas.after(delay,timerFired)

#################################################################
## Visual elements (drawGrid, drawElements, etc.)
#################################################################

#Draws the instruction pane on the bottom right corner
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

#Draws element pane and node voltage (if circuit is solved)
def drawElementPane():
    paneCoords = [(400,0),(510,510)]
    canvas.create_rectangle(paneCoords,fill = "grey")
    canvas.create_text(450,20,text="Elements",font = "helvetica 19")
    drawVoltageSource(450,100,20)
    drawResistor(450,180)
    if canvas.data.displayAnswer:
        font = "helvetica 9"
        text = "Solved!\nClick a node\nto display \nnode voltage."
        canvas.create_text(450,300,text=text)

#Displays node location and voltage if user clicks a node
def displayNodeVoltage():
    if canvas.data.displayAnswer and canvas.data.displayedNode[1] != -50:
        if not canvas.data.circuit.unsolvable:
            (nodeLocation,nodeVoltage) = canvas.data.displayedNode
            text = "Node at %s has voltage %.2f V" % (nodeLocation,nodeVoltage)
            font = "helvetica 14"
            canvas.create_text(200,450,text=text,font=font,fill ="red")

#Function that draws a resistor
def drawResistor(cx,cy):
    #c represents the 'center' of the resistor, where it's length is 80 pixels
    eLeft,eRight = cx-2*CELL_SIZE,cx + 2*CELL_SIZE #left and right endpoints
    halfCell = CELL_SIZE/2
    canvas.create_line(eLeft,cy,eRight,cy,fill="yellow")
    canvas.create_rectangle(eLeft + CELL_SIZE,cy + halfCell/2,
    eRight-CELL_SIZE,cy-halfCell/2,fill="red")

#Function that draws a voltage source
def drawVoltageSource(cx,cy,r):
    canvas.create_line(cx,cy + 2*r,cx,cy-2*r,fill="yellow")
    canvas.create_oval(cx-r,cy-r,cx + r,cy + r,fill = "white")
    canvas.create_text(cx,cy,text=" + \n -",font = "helevetica 14")

#Function to create ground
def drawGround(x,top):
    canvas.create_line(x,top,x,top + 10,fill="brown")
    canvas.create_line(x-10,top + 15,x + 10,top + 15,fill="brown",width=2)
    canvas.create_line(x-5,top + 20,x + 5,top + 20,fill="brown",width=2)
    canvas.create_line(x-2,top + 25,x + 2,top + 25,fill="brown")

#Generates grid , element pane, instructions, and node voltage
def background():
    if canvas.data.showElementPane:
        drawElementPane()
    drawInstructions()
    displayNodeVoltage()

#Draws each voltage source, resistor, ground, and 'unsolvable'
#if it applies
def drawCircuit():
    for voltageSource in canvas.data.voltageSources:
        cx,cy,r = voltageSource[0],voltageSource[1],20
        drawVoltageSource(cx,cy,r)
    for wire in canvas.data.wires:
        canvas.create_line(wire,fill="yellow")
    for resistor in canvas.data.resistors:
        drawResistor(resistor[0],resistor[1])
    if (canvas.data.grounds[0] > 0 and canvas.data.grounds[1] > 0):
        drawGround(canvas.data.grounds[0],canvas.data.grounds[1])
    if canvas.data.circuit.unsolvable:
        font = "helvetica 20"
        canvas.create_text(250,450,text="UNSOLVABLE",font=font,fill = "red")

#Draws the background and circuit
def redrawAll():
    canvas.delete(ALL)
    background()
    drawCircuit()

#################################################################
## Matrix functions to solve a system of linear equations: Ax = b
#################################################################

#Slightly modified from RosettaCode
#Url: http://rosettacode.org/wiki/Reduced_row_echelon_form#Python

#Destructive function that row-reduces a matrix into echelon form
def RREF(M):
    if not M: return
    lead = 0
    rowCount = len(M)
    columnCount = len(M[0])
    for r in range(rowCount):
        if lead >= columnCount:
            return
        i = r
        while M[i][lead] == 0:
            i += 1
            if i == rowCount:
                i = r
                lead += 1
                if columnCount == lead:
                    return
        M[i],M[r] = M[r],M[i]
        lv = M[r][lead]
        M[r] = [ mrx / lv for mrx in M[r]]
        for i in range(rowCount):
            if i != r:
                lv = M[i][lead]
                M[i] = [ iv - lv*rv for rv,iv in zip(M[r],M[i])]
        lead += 1
    return M

def isNonZero(x):
    return abs(x) > 0.0001

def clearZeroRows(M):
    return [row for row in M if any(map(isNonZero, row))]

def clearZeroCols(M):
    transpose = zip(*M)[0]
    noZeros = clearZeroRows(map(list, transpose))
    return map(list, zip(*noZeros))

#Goes through all steps to remove redundant equations and solve Ax = b
def solveMatrix(A):
    RREF(A)

    # Clear out empty equations
    noZeroRows = clearZeroRows(A)

    # Solution is the last column in the matrix
    solutionVector = [[row[-1]] for row in noZeroRows]
    coefficientMatrix = clearZeroCols([[row[:-1]] for row in noZeroRows])

    # Solve and return as python list
    matrixAnswer = linalg.solve(coefficientMatrix,solutionVector)
    return [[round(linalg.det([i]),3)] for i in matrixAnswer]


#################################################################
## Initialize canvas.data and run
#################################################################

def init():
    canvas.data.showElementPane = False
    canvas.data.isClicked = False
    canvas.data.drawWire = False
    visualElementInit()
    objectInit()
    background()

def visualElementInit():
    canvas.data.isClicked = True
    canvas.data.draggingVoltage = False
    canvas.data.clickedVoltage = OFFSCREEN
    canvas.data.draggingResistor = False
    canvas.data.clickedResistor = OFFSCREEN
    canvas.data.draggingGround = False
    canvas.data.drawWire = False
    canvas.data.wires = []
    canvas.data.grounds = OFFSCREEN
    canvas.data.voltageSources = set()
    canvas.data.resistors = set()
    canvas.data.displayAnswer = False
    canvas.data.displayedNode = OFFSCREEN

def objectInit():
    canvas.data.circuit = Circuit()
    canvas.data.circuit.unsolvable = False
    canvas.data.resistorObjects = []
    canvas.data.voltageObjects = []

def run():
    # create the root and the canvas
    global canvas
    root = Tk()
    #creates background for grid
    canvas = Canvas(root, width=500, height=500,bg = "Black")
    canvas.pack()
    root.resizable(False,False) #keeps the grid constant
    root.canvas = canvas.canvas = canvas
    # Set up canvas data and call init
    class Struct: pass
    canvas.data = Struct()
    init()
    redrawAll()
    # set up keyPressed
    root.bind("<Button-1>", mousePressed)
    root.bind("<Key>", keyPressed)
    root.bind("<Motion>",motion)
    timerFired()
    root.mainloop()

run()
