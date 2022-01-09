from os import stat
from types import ModuleType
import typing
from lxml import objectify, etree
from pathlib import Path
import inspect
import diagrams.templates as templates

from diagrams.style import Style

CWD = Path(__file__).parent.resolve()

class XMLDiagramLookup(etree.PythonElementClassLookup):
    def lookup(self, doc, el:etree.ElementBase):
        if el.tag == "mxCell":
            style = el.get("style", "")
            style = Style.from_string(style)
            if style.shape == "swimlane":
                return DClassNode
            else:
                return DObject
        if el.tag == "diagram":
            return
        return None

xml_diagram_parser:etree.XMLParser = objectify.makeparser()
xml_diagram_parser.set_element_class_lookup(XMLDiagramLookup())

class CustomElementBase(etree.ElementBase):
    def __repr__(self) -> str:
        return super().__repr__().replace("Element", self.__class__.__name__)

class DObject(CustomElementBase):
    def __str__(self) -> str:
        return super().__str__()
    
    def get_child_objects(self):
        parent:CustomElementBase = self.getparent()
        neighbours = parent.getchildren()
        neighbours = list(filter(
            lambda e: 
                type(e)==DObject and e.parent==self.id, 
            neighbours))
        return neighbours

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

    @property
    def geometry_el(self)->etree.ElementBase:
        return self.find("mxGeometry") or None
        
    @property
    def x(self)->float: return float(self.geometry_el.get("x", "0"))
    @x.setter
    def x(self, value:float)->float: self.geometry_el.set("x", str(value))
    
    @property
    def y(self)->float: return float(self.geometry_el.get("y"), "0")
    @y.setter
    def y(self, value:float)->float: self.geometry_el.set("y", str(value))

    @property
    def width(self)->float: return float(self.geometry_el.get("width"), "1")
    @width.setter
    def width(self, value:float)->float: self.geometry_el.set("width", str(value))

    @property
    def height(self)->float: return float(self.geometry_el.get("height", "1"))
    @height.setter
    def height(self, value:float)->float: self.geometry_el.set("height", str(value))

    def compute_height(self):
        """ Returns sum of children heights. """
        children:typing.List[DObject] = self.get_child_objects()
        height = 0
        for child in children:
            if child.geometry_el is not None:
                height += child.height
        return height

class DClassNode(DObject):
    SEPARATOR_LINE_HEIGHT = 8.0
    ROW_HEIGHT = 20.0
    CLASS_HEADER_HEIGHT = 30.0

    def get_separator_line(self, index=0):
        def get_all_separator_lines():
            child_objects:list[DObject] = self.get_child_objects()
            separator_lines = [obj for obj in child_objects if obj.style.shape == "line"]
            return separator_lines
        separator_lines = get_all_separator_lines()
        if len(separator_lines)==0:
            line_xml = templates.class_separator_line_xml(self.id+"_separator_line", self.id)
            line_el = etree.fromstring(line_xml, xml_diagram_parser)
            line_el.height = self.SEPARATOR_LINE_HEIGHT
            return self.addnext(line_el)
        else:
            return separator_lines[min(len(separator_lines), index)]

    def get_children_in_section(self, section=0) -> typing.List[DObject]:
        child_objects:list[DObject] = self.get_child_objects()
        children_in_sec = []
        current_section = 0
        for child in child_objects:
            if child.style.shape == "line":
                current_section+=1
            elif current_section==section:
                children_in_sec.append(child)
        return children_in_sec
        
    def get_class_fields_and_methods(self, cls:typing.Type[object]):
        def is_original(member):
            # TODO: this
            def get_members_names(cls):
                return list(map(lambda x: x[0], inspect.getmembers(cls)))
            inherited_members = get_members_names(inspect.getmro(cls)[1])
            member_name = member[0]
            original = not member_name in inherited_members
            return original
            
            # 
        fields = inspect.getmembers(cls, predicate=lambda x: not inspect.isroutine(x) and is_original(x))
        methods = inspect.getmembers(cls,predicate=lambda x: inspect.isroutine(x) and is_original(x))
        def name_filter(name:str):
            return not name.startswith("__")
        def filter_members(members:list):
            return list(filter(lambda x: name_filter(x[0]), members))
        fields = filter_members(fields)
        methods = filter_members(methods)
        return fields, methods
    
    def fill_section(self, section=0, row_generator:typing.Callable[[],DObject]=None):
        sec_children:list[DObject] = self.get_children_in_section(section)
        if section==0:
            after_element = self
        else:
            separator_line:DObject = self.get_separator_line(section-1)
            after_element = separator_line
        
        for i, row_el in enumerate(row_generator()):
            if i<len(sec_children):
                child:DObject = sec_children[i]
                child.value = row_el.value
                child.height = row_el.height
                after_element = child
            else:
                row_el.id = f"{self.id}_{section}_{i}"
                row_el.parent = self.id
                after_element.addnext(row_el)
                after_element = row_el
        
    def render_class(self, cls:typing.Type[object]):
        """ Fills class swimlane with fields of actual python class, separating line and methods.  
        
            If swimlane already has some rows, they will just be renamed. At the end of rendering height of swimlane updates to `self.compute_height()`
        """
        fields, methods = self.get_class_fields_and_methods(cls)

        def members_rows_generator_maker(members):
            def member_to_string(member):
                if inspect.isroutine(member[1]):
                    sig = inspect.signature(member[1])
                    s = f"{member[0]}("
                    s+=", ".join([p.name for p in sig.parameters.values() if p.name!="self"])
                    s+=")"
                    return s
                else:
                    return member[0]

            def generator():
                for member in members:
                    xml = templates.class_row_xml("id", self.id)
                    el:DObject = etree.fromstring(xml, xml_diagram_parser)
                    el.value = member_to_string(member)
                    el.height = self.ROW_HEIGHT
                    yield el
                
            return generator
        
        self.fill_section(0, row_generator=members_rows_generator_maker(fields))
        self.fill_section(1, row_generator=members_rows_generator_maker(methods))

        self.height = self.compute_height()

    def compute_height(self):
        """ Returns sum of children heights + self.CLASS_HEADER_HEIGHT. """
        height = super().compute_height()
        height += self.CLASS_HEADER_HEIGHT
        return height

    @staticmethod
    def predict_height_with_class(self, cls):
        fields, methods = self.get_class_fields_and_methods(cls)
        height = 0
        height += self.CLASS_HEADER_HEIGHT
        height += self.SEPARATOR_LINE_HEIGHT
        for i in range(len(fields)+len(methods)):
            height += self.ROW_HEIGHT
        return height

class DiagramElement(CustomElementBase):
    @property
    def root_el(self)->etree.ElementBase:
        return self.find("mxGraphModel/root")

    @property
    def objects(self)->typing.List[DObject]:
        return self.root_el.findall("mxCell")

    @property
    def main_container(self)->DObject:
        if not hasattr(self, "_main_container"):
            last = None
            for obj in self.objects:
                if obj.geometry_el is None:
                    last = obj
                else:
                    break
            self._main_container = last or self.root_el

        return self._main_container

    @property
    def classes_objects(self)->typing.List[DClassNode]:
        return list(filter(lambda x: type(x)==DClassNode, self.objects))

    def find_class_objects(self, cls:typing.Type[object]):
        finded = [obj for obj in self.classes_objects if obj.value.lower()==cls.__name__.lower()]
        return finded

    def render_classes(self, classes:typing.List[typing.Type[object]]):
        def get_class_file(c): return inspect.getmodule(c).__file__
        classes = list(set(classes))
        files = list(set(map(lambda c: get_class_file(c), classes)))
        classes_by_file = {file : [] for file in files}
        for cls in classes:
            classes_by_file[get_class_file(cls)].append(cls)

        x_index_of_cls = {c: files.index(get_class_file(c)) for c in classes}
        classes_objects = self.classes_objects
        for file in classes_by_file.keys():
            next_y = 0
            next_x = x_index_of_cls*280
            for cls in classes_by_file[file]:
                cls_objects = self.find_class_objects(cls)
                if len(cls_objects)>0:
                    for cls_obj in cls_objects:
                        cls_obj.render_class(cls)
                        next_y = cls_obj.y+cls_obj.height+20.0
                        next_x = cls_obj.x
                else:
                    cls_obj_xml = templates.class_xml(
                        f"{cls.__name__.lower()}_class_node", 
                        self.main_container.id,
                        cls.__name__,
                        next_x,
                        next_y, )
                    cls_obj = etree.fromstring(cls_obj, xml_diagram_parser)
                    self.root_el.append(cls_obj)
                    cls_obj.render_class(cls)

def main():
    encoding = 'utf-8'
    diagram_filepath = CWD/"../python_uml_drawer.drawio"
    root:etree.ElementBase = objectify.parse(str(diagram_filepath), xml_diagram_parser).getroot()
    objects = root.findall("diagram/mxGraphModel/root/")
    diagram:DiagramElement = root.find("diagram")
    diagram.render_classes([DObject, ])
    diagram_filepath.write_text(etree.tostring(root, pretty_print=True).decode(encoding), encoding=encoding)
    

if __name__ == '__main__':
    main()