""" Class definitions of circuit components. Also contains solve function. """

from matrix import solveMatrix

####################################################
## Classes for circuit elements
####################################################

# Only one circuit instance is created, holds all the nodes

# TODO: Handle case of creating multiple elements between the same src and dest
# TODO: Faster lookup/deletion of elements (using dicts)

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

    def removeElement(self, element):
        src, dest = element.src, element.dest
        print src, dest
        assert(src in self.nodes)
        assert(dest in self.nodes)
        print "src: ", self.nodes[src].elements
        print "dest: ", self.nodes[dest].elements
        self.nodes[src].elements.remove(element)
        self.nodes[dest].elements.remove(element.inverse())

    def voltageSources(self):
        return filter(lambda x: isinstance(x, VoltageSource) and x.voltage, self.elements) 

    def resistors(self):
        return filter(lambda x: isinstance(x, Resistor), self.elements) 

    def wires(self):
        return filter(lambda x: isinstance(x, Wire), self.elements) 

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
        print self 
        # Map each node location to a variable in the system of equations (column in the matrix)
        self.nodeToCol = dict((k, i) for i, (k,_) in enumerate(self.nodes.iteritems()))
        self.dim = len(self.nodes)

        solution = solveMatrix(self._createEquations())
        if solution is None:
            self.unsolvable = True
            return

        for loc, node in self.nodes.iteritems():
            node.voltage = solution[self.nodeToCol[loc]][0]

        self.solved = True

    # Creates each node equation using a KCL (if needed)
    # Goes through each node, starting with ground
    def _createEquations(self):
        equations = []

        # Ground equation forces ground node to be 0 volts
        groundEquation = [0]*(self.dim + 1)
        groundEquation[self.nodeToCol[self.ground]] = 1
        equations.append(groundEquation)

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
                    equations.append(equation)

            # Next, use KCL to produce equations for nodes connecting resistors
            if any([isinstance(e, Resistor) for e in node.elements]):
                equation = [0]*(self.dim + 1)
                self._buildKCLEquation(loc, set(), equation)
                equations.append(equation)

        return equations

    def _buildKCLEquation(self, location, visited, equation):
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
                    self._buildKCLEquation(element.dest, visited, equation)

class Element:

    def __init__(self, src, dest):
        """ src and dest are tuples representing the element's grid location """
        self.src = src
        self.dest = dest
        # Populated when circuit is solved
        #self.current = None

    def resetCurrent(self, value=None):
        self.current = value

    def __eq__(self, other):
        return self.src == other.src and self.dest == other.dest

    def __hash__(self):
        return self.src.__hash__() + self.dest.__hash__()

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

    def __eq__(self, other):
        return isinstance(other, VoltageSource) and self.voltage == other.voltage \
                                                and Element.__eq__(self, other)

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

    def __eq__(self, other):
        return isinstance(other, Resistor) and self.resistance == other.resistance \
                                           and Element.__eq__(self, other)

    def __str__(self):
        s = Element.__str__(self)
        return "Resistor: %s, resistance: %0.3f" % (s, self.resistance)

class Wire(VoltageSource):
    def __init__(self, src, dest):
        VoltageSource.__init__(self, src, dest, 0)

    def inverse(self):
        return Wire(self.dest, self.src)

    def __eq__(self, other):
        return isinstance(other, Wire) and VoltageSource.__eq__(self, other)

class Node(object):
    def __init__(self,location,voltage=0,current=0):
        self.elements = set()
        self.location = location
        self.voltage = voltage
        self.current = current

    def addElement(self, element):
        assert(self.location == element.src)
        self.elements.add(element)
