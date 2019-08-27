from . import Item


class Door(Item):
    
    @classmethod
    def getItem(cls, itemFactory, parent, styleBlock):
        item = itemFactory.getItem(cls)
        item.init()
        item.parent = parent
        item.building = parent.building
        item.styleBlock = styleBlock
        return item