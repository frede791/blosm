from .div import Div
from defs.facade_classification import FacadeClass


class Facade(Div):
    """
    Represents a building facade.
    It's typically composed of one or more faces (in the most cases rectangular ones)
    """
    
    def __init__(self, parent, indices, vector, volumeGenerator):
        super().__init__(parent, parent, None)
        
        self.indices = indices
        
        self.buildingPart = "facade"
        
        # Is facade visible or hidden by other facades that belong to other buildings or building parts?
        self.visible = True
        
        self.vector = vector
        vector.facade = self
        
        self.outer = True
        
        # is facade processed in the action <FacadeBoolean>?
        self.processed = False
        
        # set facade class
        self.front = False
        self.side = False
        self.back = False
        self.shared = False
        facadeClass = vector.edge.cl
        if facadeClass:
            if facadeClass == FacadeClass.front:
                self.front = True
            elif facadeClass == FacadeClass.side:
                self.side = True
            elif facadeClass == FacadeClass.shared:
                self.shared = True
            elif facadeClass == FacadeClass.back:
                self.back = True
        
        # <volumeGenerator> knows which geometry the facade items have and how to map UV-coordinates
        volumeGenerator.initFacadeItem(self)