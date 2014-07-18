""" Matrix math """

from numpy import linalg

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
    try:
        matrixAnswer = linalg.solve(coefficientMatrix,solutionVector)
    except linalg.LinAlgError as e:
        print e
        return None
    else:
        return [[round(linalg.det([i]),3)] for i in matrixAnswer]
