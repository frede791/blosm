from .container import Container
from .level_groups import LevelGroups


class Div(Container):
    
    def __init__(self, parent, footprint, styleBlock):
        super().__init__(parent, footprint, styleBlock)
        self.levelGroups = LevelGroups(self)
        self.minHeight = footprint.minHeight
        self.minLevel = footprint.minLevel