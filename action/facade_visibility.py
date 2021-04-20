from math import sqrt
import numpy as np
from bisect import bisect_left
from operator import itemgetter


class PriorityQueue():
    def __init__(self):
        self.keys = []
        self.queue = []
        self.ids = []
    
    def push(self, key, item):
        i = bisect_left(self.keys, key) # Determine where to insert item.
        self.keys.insert(i, key)        # Insert key of item to keys list.
        self.queue.insert(i, item)      # Insert the item itself in the corresponding place.
        self.ids.insert(i, id(item))
    
    def pop(self):
        self.keys.pop(0)
        self.ids.pop(0)
        return self.queue.pop(0)
    
    def remove(self, item):
        itemIndex = self.ids.index(id(item))
        del self.ids[itemIndex]
        del self.queue[itemIndex]
        del self.keys[itemIndex]
    
    def empty(self):
        return not self.queue
    
    def cleanup(self):
        self.keys.clear()
        self.queue.clear()
        self.ids.clear()


class FacadeVisibility:
    
    def __init__(self, searchRange=(10., 100.)):
        self.app = None
        self.kdTree = None
        self.bldgVerts = None
        self.searchWidthMargin = searchRange[0]
        self.searchHeight = searchRange[1]
        self.searchHeight_2 = searchRange[1]*searchRange[1]
        self.vertIndexToBldgIndex = []
        self.priorityQueue = PriorityQueue()
        self.posEvents = []
        self.negEvents = []
    
    def do(self, manager):
        # check if have a way manager
        if not self.app.managersById["ways"]:
            return
        
        buildings = manager.buildings
        
        # Create an instance of <util.polygon.Polygon> for each <building>,
        # remove straight angles for them and calculate the total number of vertices
        for building in buildings:
            if not building.polygon:
                building.initPolygon(manager)
        
        for building in buildings:
            building.polygon.processStraightAngles(manager)
        
        for building in buildings:
            building.polygon.processStraightAnglesExtra(manager)
        
        # the total number of vertices
        totalNumVerts = sum(building.polygon.numEdges for building in buildings if building.polygon)
        # create mapping between the index of the vertex and index of the building in <buildings>
        self.vertIndexToBldgIndex.extend(
            bldgIndex for bldgIndex, building in enumerate(buildings) if building.polygon for _ in range(building.polygon.numEdges)
        )
        
        # allocate the memory for an empty numpy array
        bldgVerts = np.zeros((totalNumVerts, 2))
        # fill in <self.bldgVerts>
        index = 0
        for building in buildings:
            if building.polygon:
                # store the index of the first vertex of <building> in <self.bldgVerts> 
                building.auxIndex = index
                for vert in building.polygon.verts:
                    bldgVerts[index] = (vert[0], vert[1])
                    index += 1
        self.bldgVerts = bldgVerts
        
        self.createKdTree(buildings, totalNumVerts)
        
        self.calculateFacadeVisibility(manager)
    
    def cleanup(self):
        self.kdTree = None
        self.bldgVerts = None
        self.vertIndexToBldgIndex.clear()

    def calculateFacadeVisibility(self, manager):
        buildings = manager.buildings
        
        posEvents = self.posEvents
        negEvents = self.negEvents
        
        for way in self.app.managersById["ways"].getFacadeVisibilityWays():
            #if not way.polyline:
            #    way.initPolyline()
            
            for segmentCenter, segmentUnitVector, segmentLength in way.segments(manager.data):
                posEvents.clear()
                negEvents.clear()
                
                searchWidth = segmentLength/2. + self.searchWidthMargin
                # Get all building vertices for the buildings whose vertices are returned
                # by the query to the KD tree
                queryBldgIndices = set(
                    self.makeKdQuery(segmentCenter, sqrt(searchWidth*searchWidth + self.searchHeight_2))
                )
                queryBldgVertIndices = tuple(
                    vertIndex for bldgIndex in queryBldgIndices for vertIndex in range(buildings[bldgIndex].auxIndex, buildings[bldgIndex].auxIndex + buildings[bldgIndex].polygon.numEdges)
                )
                # slice <self.bldgVerts> using <queryBldgVertIndices>
                queryBldgVerts = self.bldgVerts[queryBldgVertIndices,:]
                
                # transform <queryBldgVerts> to the system of reference of <way>
                matrix = np.array(( (segmentUnitVector[0], -segmentUnitVector[1]), (segmentUnitVector[1], segmentUnitVector[0]) ))
                
                # shift origin to the segment center
                queryBldgVerts -= segmentCenter
                # rotate <queryBldgVerts>, output back to <queryBldgVerts>
                np.matmul(queryBldgVerts, matrix, out=queryBldgVerts)
                
                #
                # fill <posEvents> and <negEvents>
                #
                
                # index in <queryBldgVerts>
                firstVertIndex = 0
                for bldgIndex in queryBldgIndices:
                    building = buildings[bldgIndex]
                    building.resetTmpVisibility()
                    building.resetCrossedEdges()
                    
                    for edge, edgeVert1, edgeVert2 in building.polygon.edgeInfo(queryBldgVerts, firstVertIndex):
                        # check if there are edges crossed by this way-segment (the vertices have different signs of y-coord)
                        if np.diff( (np.sign(edgeVert1[1]),np.sign(edgeVert2[1])) ):
                            # find x-coord of intersection with way-segment axis (the x-axis in this coordinate system).
                            # divide its value by the half of the segment length to get a relative number.
                            # for absolute values between 0 and 1, the intersection is in the way-segment, else out of it.
                            dx = edgeVert2[0]- edgeVert1[0]
                            dy = edgeVert2[1]- edgeVert1[1]
                            x0 = edgeVert1[0]
                            y0 = edgeVert1[1]
                            intsectX = (x0+abs(y0/dy)*dx ) / (segmentLength/2.) if dy else 0.
                            # store result in building for later analysis
                            building.addCrossedEdge(edge, intsectX)

                    intersections = building.crossedEdges
                    # if there are intersections, fill a dummy line in the interior of the building
                    # between the intersection. The edge index is negative, so that it can be 
                    # excluded in lines marked with "updateAuxVisibilityAdd".
                    if intersections:
                        intersections.sort(key=lambda x:x[1])
                        for i in range(0, len(intersections), 2):
                            x1 = intersections[i][1] * segmentLength/2.
                            x2 = intersections[i+1][1] * segmentLength/2.
                            edge = None  # None to mark it as a dummy edge
                            posEvents.append(
                                (edge, None, x1, np.array((x1,0.)), np.array((x2,0.)))
                            )
                            # Keep track of the related "edge starts" event,
                            # that's why <posEvents[-1]>
                            posEvents.append(
                                (edge, posEvents[-1], x2, np.array((x1,0.)), np.array((x2,0.)))
                            )
                            negEvents.append(
                                (edge, None, x1, np.array((x1,0.)), np.array((x2,0.)))
                            )
                            # Keep track of the related "edge starts" event,
                            # that's why <posEvents[-1]>
                            negEvents.append(
                                (edge, negEvents[-1], x2, np.array((x1,0.)), np.array((x2,0.)))
                            )

                    for edge, edgeVert1, edgeVert2 in building.polygon.edgeInfo(queryBldgVerts, firstVertIndex):
                        if edgeVert1[0] > edgeVert2[0]:
                            # because the algorithm scans with increasing x, the first vertice has to get smaller x
                            edgeVert1, edgeVert2 = edgeVert2, edgeVert1
                        
                        if edgeVert1[1] > 0. or edgeVert2[1] > 0.:
                            posEvents.append(
                                (edge, None, edgeVert1[0], edgeVert1, edgeVert2)
                            )
                            # Keep track of the related "edge starts" event,
                            # that's why <posEvents[-1]>
                            posEvents.append(
                                (edge, posEvents[-1], edgeVert2[0], edgeVert1, edgeVert2)
                            )
                        if edgeVert1[1] < 0. or edgeVert2[1] < 0.:
                            negEvents.append(
                                (edge, None, edgeVert1[0], edgeVert1, edgeVert2)
                            )
                            # Keep track of the related "edge starts" event,
                            # that's why <negEvents[-1]>
                            negEvents.append(
                                (edge, negEvents[-1], edgeVert2[0], edgeVert1, edgeVert2)
                            )
                     
                    firstVertIndex += building.polygon.numEdges
                
                self.processEvents(posEvents, True)
                self.processEvents(negEvents, False)

                # index in <queryBldgVerts>
                firstVertIndex = 0
                for bldgIndex in queryBldgIndices:
                    building = buildings[bldgIndex]

                    # compute visibility ratio and select edges in range
                    for edge, edgeVert1, edgeVert2 in building.polygon.edgeInfo(queryBldgVerts, firstVertIndex):
                        dx = abs(edgeVert2[0] - edgeVert1[0])
                        dy = abs(edgeVert2[1] - edgeVert1[1])
                        if dx < dy: # abs of angle to way-segment < 45°, done here because crossings are excluded
                            edge.visibilityTmp = 0.
                        elif dx:
                            edge.visibilityTmp /= dx    # normalization of visibility
                        else:
                            edge.visibilityTmp = 0.     # edge perpendicular to way-segment
                    
                    # check for intersections and process them
                    edgeIntersections = building.crossedEdges
                    # if there are intersections, process their edges
                    if edgeIntersections:
                        # for values between 0 and 1, the intersection is in the way-segment
                        wayIntersects =  tuple( isect[0] for isect in edgeIntersections if abs(isect[1]) <= 1. )
                        if wayIntersects:
                            # all intersections with the way-segment itself become full visible
                            for edge, intsectX in edgeIntersections:
                                edge.visibilityTmp = 1. if abs(intsectX) <= 1. else 0.
                        else:
                            # process the nearest axis intersections. If there are on both sides, we assume a street within a
                            # courtyard. Else, the edge gets visible.

                            # largest index on negative (left) side
                            axisLeftEdge, _ = max( (isec for isec in edgeIntersections if isec[1]<0.), key=itemgetter(1), default=(None,None))
                            if axisLeftEdge: # if edgeIntersections[axisLeftIndex] > 2* searchWidth/segmentLength:
                                axisLeftEdge.visibilityTmp = 1.
                            else:
                                # smallest index on positive (right) side
                                axisRightEdge, _ = min( (isec for isec in edgeIntersections if isec[1]>=0.), key=itemgetter(1), default=(None,None))
                                if axisRightEdge: # and edgeIntersections[axisRightIndex] < 2* searchWidth/segmentLength:
                                    axisRightEdge.visibilityTmp = 1.

                    # check for range and angles
                    for edge, edgeVert1, edgeVert2 in building.polygon.edgeInfo(queryBldgVerts, firstVertIndex):
                        # at least one vertice of the edge must be in rectangular search range
                        if not ( (abs(edgeVert1[0]) < searchWidth and abs(edgeVert1[1]) < self.searchHeight) or\
                                (abs(edgeVert2[0]) < searchWidth and abs(edgeVert2[1]) < self.searchHeight) ):
                            edge.visibilityTmp = 0.
                        edge.updateVisibility()

                    firstVertIndex += building.polygon.numEdges

    def processEvents(self, events, positiveY):
        """
        Process <self.posEvents> or <self.negEvents>
        """
        queue = self.priorityQueue
        activeEvent = None
        activeX = 0.
        
        # sort events by increasing start x and then by increasing abs(end y)
        events.sort(
            key = (lambda x: (x[2], x[4][1])) if positiveY else (lambda x: (x[2], -x[4][1]))
        )

        queue.cleanup()
        
        #self.drawEvents(events)
        
        for event in events:
            _, relatedEdgeStartsEvent, eventX, edgeVert1, edgeVert2 = event
            if positiveY:
                startY = edgeVert1[1]
                endY = edgeVert2[1]
            else:
                startY = -edgeVert1[1]
                endY = -edgeVert2[1]
            if not activeEvent:
                activeEvent = event
                activeX = eventX
            elif not relatedEdgeStartsEvent: # an "edge starts" event here
                activeStartX = activeEvent[3][0]
                activeEndX = activeEvent[4][0]
                if positiveY:
                    activeStartY = activeEvent[3][1]
                    activeEndY = activeEvent[4][1]
                else:
                    activeStartY = -activeEvent[3][1]
                    activeEndY = -activeEvent[4][1]
                # if both edges start at the same x-coord, the new edge is in front,
                # when its endpoint is nearer to the way-segment.
                isInFront = False
                if eventX == activeStartX:
                    isInFront = endY < activeEndY 
                # potentially, if the new edge starts in front of the active edge's 
                # maximum y-coord, it could be in front of the active edge.
                elif startY < max(activeStartY,activeEndY):
                    # if the new edge starts in behind the active edge's 
                    # minimum y-coord, the decision has to be based on the true y-coord 
                    # of the active edge at this x-coord.
                    if startY > min(activeStartY,activeEndY):
                        dx = activeEndX - activeStartX
                        # dy = activeEndY - activeStartY
                        isInFront = startY < activeStartY + (eventX-activeStartX) * (activeEndY - activeStartY) / dx\
                            if dx else False
                    # else, the new edge is in front for sure
                    else:
                        isInFront = True

                if isInFront: # the new edges hides the active edge
                    # edge = activeEvent[0]
                    if activeEvent[0]: # exclude dummy edges of crossings updateAuxVisibilityAdd
                        activeEvent[0].visibilityTmp += eventX - activeX
                    queue.push(activeEndY, activeEvent)
                    activeEvent = event
                    activeX = eventX # the new edges is behind the active edge
                else: 
                    queue.push(endY, event)
            else:
                if activeEvent is relatedEdgeStartsEvent: # the active edge ends
                    # edge = activeEvent[0]
                    if activeEvent[0]:   # exclude dummy edges of crossings updateAuxVisibilityAdd
                        activeEvent[0].visibilityTmp += eventX - activeX
                    if not queue.empty(): # there is an hidden edge that already started                   
                        activeEvent = queue.pop()
                        activeX = eventX
                    else:
                        activeEvent = None
                        activeX = 0.
                else: # there must be an edge in the queue, that ended before
                    queue.remove(relatedEdgeStartsEvent)


class FacadeVisibilityBlender(FacadeVisibility):
    
    def createKdTree(self, buildings, totalNumVerts):
        from mathutils.kdtree import KDTree
        kdTree = KDTree(totalNumVerts)
        
        index = 0
        for building in buildings:
            if building.polygon:
                for vert in building.polygon.verts:
                    kdTree.insert(vert, index)
                    index += 1
        kdTree.balance()
        self.kdTree = kdTree
    
    def makeKdQuery(self, searchCenter, searchRadius):
        """
        Returns a generator of building indices in <manager.buldings>.
        The buildings indices aren't unique
        """
        return (
            self.vertIndexToBldgIndex[vertIndex] for _,vertIndex,_ in self.kdTree.find_range(searchCenter, searchRadius)
        )


class FacadeVisibilityOther(FacadeVisibility):
    
    def createKdTree(self, buildings, totalNumVerts):
        from scipy.spatial import KDTree
        
        self.kdTree = KDTree(self.bldgVerts)
    
    def makeKdQuery(self, searchCenter, searchRadius):
        """
        Returns a generator of building indices in <manager.buldings>.
        The buildings indices aren't unique
        """
        return (
            self.vertIndexToBldgIndex[vertIndex] for vertIndex in self.kdTree.query_ball_point(searchCenter, searchRadius)
        )