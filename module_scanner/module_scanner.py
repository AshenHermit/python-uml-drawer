import importlib
import importlib.util
from importlib.machinery import SourceFileLoader
import inspect
import typing
from pathlib import Path

from diagrams.parser import DiagramRenderer

CWD = Path(__file__).parent.resolve()

class PackageScanner():
    def __init__(self, package_path:Path) -> None:
        self.__package_path:Path = Path(package_path.resolve())
        self.__init_module = self.import_package()
    
    @property
    def package_path(self): return self.__package_path
    @property
    def init_module(self): return self.__init_module
    
    def import_package(self):
        package_path = self.package_path
        if package_path.exists():
            package_name = package_path.with_suffix("").name
            if package_path.is_file():
                location = package_path.as_posix()
            elif package_path.is_dir():
                location = (package_path/"__init__.py").as_posix()
            
            loader = SourceFileLoader(package_name, location)
            spec = importlib.util.spec_from_loader(package_name, loader)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        return None 

    @property
    def members(self):
        members = inspect.getmembers(self.init_module)
        def is_child_member(member):
            if inspect.ismodule(member):
                member_file = getattr(member, "__file__", "")
            else:
                member_module = inspect.getmodule(member)
                member_file = getattr(member_module, "__file__", "")
            return Path(member_file).is_relative_to(self.package_path)
        members = list(filter(lambda x: is_child_member(x[1]), members))
        return members


if __name__ == "__main__":
    members = []
    members += PackageScanner(CWD/"../module_scanner/").members
    members += PackageScanner(CWD/"../diagrams/").members
    members = list(map(lambda x: x[1], members))

    renderer = DiagramRenderer(CWD/"../test_diagram.drawio")
    renderer.render_members(members)