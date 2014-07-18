""" Definitions of Circuit and Element classes and solve functionality """

from matrix import solveMatrix

# TODO: Saving and loading state

####################################################
## Classes for circuit elements
####################################################

#Only one circuit instance is created, holds all the nodes
class Circuit(object):
    def __init__(self):
        self.nodes = dict()
        self.elements = []
        self.ground = None
        self.unsolvable = False
        self.solved = False

    def addElement(self, element):
        """ Create and add an element to the circuit """
        src, dest = element.src, element.dest
        if src not in self.nodes:
            self.nodes[src] = Node(src)
        if dest not in self.nodes:
            self.nodes[dest] = Node(dest)
        self.nodes[src].addElement(element)
        self.nodes[dest].addElement(element.inverse())
        self.elements.append(element)

    def voltageSources(self):
        return filter(lambda x: isinstance(x, VoltageSource) and x.voltage, self.elements) 

    def resistors(self):
        return filter(lambda x: isinstance(x, Resistor), self.elements) 

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
        self.unsolvable = False
        self.solved = False

        # A circuit with no voltage sources is unsolvable
        if not self.voltageSources():
            self.unsolvable = True
            return

        # Map each node location to a variable in the system of equations (column in the matrix)
        self.nodeToCol = dict((k, i) for i, (k,_) in enumerate(self.nodes.iteritems()))
        self.dim = len(self.nodes)

        solution = solveMatrix(self.createEquations())
        if solution is None:
            self.unsolvable = True
            return

        for loc, node in self.nodes.iteritems():
            node.voltage = solution[self.nodeToCol[loc]][0]

        self.solved = True

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

