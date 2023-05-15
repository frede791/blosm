from lib.CompGeom.PolyLine import PolyLine

class WaySection():
    ID = 1  # Must not start with zero to get unambiguous connector indices!
    def __init__(self,net_section,network):
        self.id = WaySection.ID
        WaySection.ID += 1
        self.network = network
        self.originalSection = net_section
        self.category = self.originalSection.category
        self.tags = self.originalSection.tags
        self.polyline = PolyLine(net_section.path)
        self.isLoop = net_section.s == net_section.t
        self._sV = None  # vector of first segment
        self._tV = None  # vector of last segment
        self.trimS = 0.                      # trim factor for start
        self.trimT = len(self.polyline)-1    # trim factor for target
        self._isValid = True

        # Lane specific data. Inserted by method createWaySections() of StreetGenerator.
        self.lanePatterns = None
        self.totalLanes = None
        self.forwardLanes = None
        self.backwardLanes = None
        self.bothLanes = None
        self.isOneWay = None
        self.fwdLaneR = False
        self.fwdLaneL = False
        self.bwdLaneR = False
        self.bwdLaneL = False

        self.laneWidth = None
        self.width = None
        self.forwardWidth = None
        self.backwardWidth = None
        self.offset = 0.

        # Trim values in a cluster
        self.trimStart = 0.
        self.trimEnd = 0.
 
 
        # nrOfLanes = getLanes(self.originalSection.tags)
        # if nrOfLanes:
        #     if self.isOneWay:
        #         self.nrLeftLanes = 0
        #         self.nrRightLanes = nrOfLanes
        #     else:
        #         self.nrLeftLanes = nrOfLanes//2
        #         self.nrRightLanes = nrOfLanes//2
        # else:
        #     self.nrLeftLanes = 1
        #     self.nrRightLanes = 1
        # self.processTurnLanes()

    @property
    def isClipped(self):
        return self._isClipped

    @isClipped.setter
    def isClipped(self,val):
        self._isClipped = val

    @property
    def isValid(self):
        return self._isValid

    @isValid.setter
    def isValid(self,val):
        self._isValid = val

    @property
    def sV(self):
        if self._sV is None:
            self._sV = self.polyline.verts[1] - self.polyline.verts[0]
        return self._sV

    @property
    def tV(self):
        if self._tV is None:
            self._tV = self.polyline.verts[-2] - self.polyline.verts[-1]
        return self._tV

    def fwd(self):
        return [v for v in self.polyline]

    def rev(self):
        return [v for v in self.polyline[::-1]]

    # def processTurnLanes(self):
    #     width = estimateWayWidth(self.originalSection.category,self.originalSection.tags)
    #     tags = self.originalSection.tags
    #     if 'turn:lanes' in tags:
    #         nrOfLanes = getLanes(tags)
    #         if nrOfLanes:
    #             laneDescs = tags['turn:lanes'].split('|')
    #             leftTurns = ['left','slight_left','sharp_left']
    #             rightTurns = ['right','slight_right','sharp_right']
    #             leftTurnLanes = sum(1 for tag in laneDescs if any(x in tag for x in leftTurns) )
    #             rightTurnLanes = sum(1 for tag in laneDescs if any(x in tag for x in rightTurns) )
    #             # ******* turn lanes curently switche off
    #             if True:#leftTurnLanes == rightTurnLanes:
    #                 self.leftWidth = width/2.
    #                 self.rightWidth = width/2.
    #             else:
    #                 if self.network.borderlessOrder(self.polyline[0]) == 2:
    #                     laneWidth = width/nrOfLanes
    #                     halfSymLaneWidth = laneWidth*(nrOfLanes - leftTurnLanes - rightTurnLanes)/2
    #                     self.leftWidth = halfSymLaneWidth + leftTurnLanes * laneWidth
    #                     self.rightWidth = halfSymLaneWidth + rightTurnLanes * laneWidth
    #                     if not self.isOneWay:
    #                         self.nrLeftLanes += leftTurnLanes - rightTurnLanes
    #                         self.nrRightLanes += rightTurnLanes - leftTurnLanes
    #                 else:
    #                     self.leftWidth = width/2.
    #                     self.rightWidth = width/2.
    #         else:
    #             self.leftWidth = width/2.
    #             self.rightWidth = width/2.
    #     else:
    #         self.leftWidth = width/2.
    #         self.rightWidth = width/2.

