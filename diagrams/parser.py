from os import stat
import typing
from lxml import objectify, etree
from pathlib import Path
import inspect

from diagrams.style import Style

CWD = Path(__file__).parent.resolve()

class XMLDiagramLookup(etree.PythonElementClassLookup):
    def lookup(self, doc, el:etree.ElementBase):
        lookupmap = { 'custom' : DObject }
        if el.tag == "mxCell":
            style = el.get("style", "")
            style = Style.from_string(style)
            if False and style.shape == "swimlane":
                return None
            else:
                return DObject
        return None

xml_diagram_parser:etree.XMLParser = objectify.makeparser()
xml_diagram_parser.set_element_class_lookup(XMLDiagramLookup())

class DObject(etree.ElementBase):
    def _init(self):
        pass

    def __str__(self) -> str:
        return super().__str__()
    
    def get_child_objects(self):
        parent:etree.ElementBase = self.getparent()
        neighbours = parent.getchildren()
        neighbours = list(filter(lambda e: e.parent==self.id, neighbours))
        return neighbours

    def __repr__(self) -> str:
        return super().__repr__().replace("Element", self.__class__.__name__)

    @property
    def style(self)->Style:
        return Style.from_string(self.get("style", ""))
    @style.setter
    def style(self, style:Style): self.set("style", str(style))

    @property
    def value(self)->str: return self.get("value", "")
    @value.setter
    def value(self, value:str):self.set("value", value)

    @property
    def id(self)->str: return str(self.get("id", "1"))
    @id.setter
    def id(self, id:str):self.set("id", str(id))

    @property
    def parent(self)->str: return str(self.get("parent", "1"))
    @parent.setter
    def parent(self, parent:str):self.set("parent", str(parent))

    @property
    def vertex(self)->int: return int(self.get("vertex", "1"))
    @vertex.setter
    def vertex(self, vertex:int):self.set("vertex", str(vertex))

class DClassNode(DObject):
    def render_class(cls:typing.Type[object]):
        # cls.__dict__
        pass

def main():
    root = objectify.parse(str(CWD/"../python_uml_drawer.drawio"), xml_diagram_parser).getroot()
    pass
if __name__ == '__main__':
    main()