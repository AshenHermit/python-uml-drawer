from os import stat
from types import ModuleType, MappingProxyType
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
            return DiagramElement
        if el.tag == "root":
            return DObject
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
        children = list(filter(
            lambda e:
                type(e)==DObject and e.parent==self.id, 
            neighbours))
        return children

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
        return self.find("mxGeometry")
        
    @property
    def x(self)->float: return float(self.geometry_el.get("x", "0"))
    @x.setter
    def x(self, value:float)->float: self.geometry_el.set("x", str(value))
    
    @property
    def y(self)->float: return float(self.geometry_el.get("y", "0"))
    @y.setter
    def y(self, value:float)->float: self.geometry_el.set("y", str(value))

    @property
    def width(self)->float: return float(self.geometry_el.get("width", "1"))
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

    def __init__(self, *children, attrib=..., nsmap=..., **_extra) -> None:
        super().__init__(*children, attrib=attrib, nsmap=nsmap, **_extra)
        self.ref_class:typing.Type[object] = None
        self.ref_class_name:str = ""

    def get_all_separator_lines(self):
        child_objects:list[DObject] = self.get_child_objects()
        separator_lines = [obj for obj in child_objects if obj.style.shape == "line"]
        return separator_lines
    
    def get_separator_line(self, index=0):
        """creates separator line if not exist"""
        # create previous separators if index is > count of separators in general
        for i in range(max(0, index - len(self.get_all_separator_lines()))):
            self.get_separator_line(i)
        separator_lines = self.get_all_separator_lines()
        separator_line = None
        prev_els = self.get_children_in_section(index)

        if len(separator_lines)==index:
            line_xml = templates.class_separator_line_xml(f"{self.id}_separator_line_{index}", self.id)
            line_el = etree.fromstring(line_xml, xml_diagram_parser)
            line_el.height = self.SEPARATOR_LINE_HEIGHT
            if len(prev_els)>0:
                prev_els[-1].addnext(line_el)
            else:
                self.addnext(line_el)
            separator_line = line_el
        else:
            separator_line = separator_lines[min(len(separator_lines), index)]
        
        if len(prev_els)>0:
            prev_el = prev_els[-1]
            separator_line.y = prev_el.y + prev_el.height
        return separator_line

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
        def get_members_names(cls):
            return list(map(lambda x: x[0], inspect.getmembers(cls)))
        inherited_members = get_members_names(inspect.getmro(cls)[1])
        def is_original(member_name_value):
            return member_name_value[0] not in inherited_members
        def name_filter(member_name_value):
            return not member_name_value[0].startswith("__")
        def filter_members(member_name_value):
            return is_original(member_name_value) and name_filter(member_name_value)
            #
        fields = inspect.getmembers(cls, predicate=lambda x: not inspect.isroutine(x))
        methods = inspect.getmembers(cls,predicate=lambda x: inspect.isroutine(x))
        fields, methods = tuple([list(filter(filter_members, arr)) for arr in [fields, methods]])
        return fields, methods
    
    def fill_section(self, section=0, row_generator:typing.Callable[[],DObject]=None):
        sec_children:list[DObject] = self.get_children_in_section(section)
        if section==0:
            after_element = self
        else:
            separator_line:DObject = self.get_separator_line(section-1)
            after_element = separator_line
        
        for i, row_el in enumerate(row_generator()):
            existing_els = [c for c in sec_children if c.value==row_el.value]

            if len(existing_els)>0:
                el:DObject = existing_els[0]
                el.value = row_el.value
            else:
                if len(sec_children)>0 and after_element:
                    after_element = sec_children[-1]
                row_el.y = after_element.y + after_element.height
                if after_element == self: 
                    row_el.y = after_element.y+self.CLASS_HEADER_HEIGHT
                if len(sec_children)>0: after_element = sec_children[-1]
                row_el.parent = self.id
                after_element.addnext(row_el)
        
    def render_class(self, cls:typing.Type[object]):
        """ Fills class swimlane with fields of actual python class, separating line and methods.  
        
            If swimlane already has some rows, they will just be renamed. At the end of rendering height of swimlane updates to `self.compute_height()`
        """
        self.ref_class = cls
        self.ref_class_name = cls.__name__
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
                    id = f"{self.id}_{str(type(member[1]).__name__)}_{member[0]}"
                    xml = templates.class_row_xml(id, self.id)
                    el:DObject = etree.fromstring(xml, xml_diagram_parser)
                    el.value = member_to_string(member)
                    el.height = self.ROW_HEIGHT
                    yield el
                
            return generator
        
        self.fill_section(0, row_generator=members_rows_generator_maker(fields))
        self.fill_section(1, row_generator=members_rows_generator_maker(methods))

        self.height = self.compute_height()
        self.arrange_children()

    def compute_height(self):
        """ Returns sum of children heights + self.CLASS_HEADER_HEIGHT. """
        height = super().compute_height()
        height += self.CLASS_HEADER_HEIGHT
        return height

    def arrange_children(self):
        separator_lines = self.get_all_separator_lines()
        section_els = []
        for sec in range(len(separator_lines)+1):
            # arrange separator line
            if sec>0:
                if len(section_els)>0:
                    separator_lines[sec-1].y = section_els[-1].y + section_els[-1].height
                elif sec==1:
                    separator_lines[sec-1].y = self.CLASS_HEADER_HEIGHT
                else:
                    separator_lines[sec-1].y = separator_lines[sec-2].y + separator_lines[sec-2].height

            # arrange members
            section_els = self.get_children_in_section(sec)
            for i,el in enumerate(section_els):
                if i==0 and sec==0:
                    el.y = self.CLASS_HEADER_HEIGHT
                elif i==0:
                    separator_line = separator_lines[sec-1]
                    el.y = separator_line.y + separator_line.height
                else:
                    prev_el = section_els[i-1]
                    el.y = prev_el.y + prev_el.height

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
        classes = list(classes)
        files = list(set(map(lambda c: get_class_file(c), classes)))
        classes_by_file = {file : [] for file in files}
        for cls in classes:
            classes_by_file[get_class_file(cls)].append(cls)

        x_index_of_cls = {c: files.index(get_class_file(c)) for c in classes}
        classes_objects = self.classes_objects
        for file in classes_by_file.keys():
            next_y = 0
            next_x = files.index(file)*280
            # pack infile members
            infile_members = None
            for member in list(classes_by_file[file]):
                if type(member).__name__ != "type":
                    if infile_members is None:
                        infile_members = type(Path(file).with_suffix("").name+"_module", (object,), {})
                    setattr(infile_members, member.__name__, member)
                    classes_by_file[file].remove(member)
            if infile_members is not None:
                classes_by_file[file].append(infile_members)

            for cls in classes_by_file[file]:
                cls_objects = self.find_class_objects(cls)
                cls_obj_ref = None
                if len(cls_objects)>0:
                    for cls_obj in cls_objects:
                        cls_obj.render_class(cls)
                        cls_obj_ref = cls_obj
                else:
                    cls_obj_xml = templates.class_xml(
                        f"{cls.__name__.lower()}_class_node", 
                        self.main_container.id,
                        cls.__name__,
                        next_x,
                        next_y, )
                    cls_obj = etree.fromstring(cls_obj_xml, xml_diagram_parser)
                    self.root_el.append(cls_obj)
                    cls_obj.render_class(cls)
                    cls_obj_ref = cls_obj
                
                if cls_obj_ref is not None:
                    next_y = cls_obj_ref.y+cls_obj_ref.height+20.0
                    next_x = cls_obj_ref.x

class DiagramRenderer:
    def __init__(self, diagram_filepath:Path) -> None:
        self.diagram_filepath = diagram_filepath

    def render_members(self, members):
        encoding = 'utf-8'
        if not self.diagram_filepath.exists():
            self.diagram_filepath.write_text(templates.empty_diagram(), encoding=encoding)
        root:etree.ElementBase = objectify.parse(str(self.diagram_filepath), xml_diagram_parser).getroot()
        objects = root.findall("diagram/mxGraphModel/root/")
        diagram:DiagramElement = root.find("diagram")
        diagram.render_classes(members)
        self.diagram_filepath.write_text(etree.tostring(root, pretty_print=True).decode(encoding), encoding=encoding)

def main():
    renderer = DiagramRenderer(CWD/"../python_uml_drawer.drawio")
    renderer.render_members([DObject, DClassNode, DiagramElement])

if __name__ == '__main__':
    main()