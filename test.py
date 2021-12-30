import importlib
import importlib.util
from importlib.machinery import SourceFileLoader
import inspect

from pathlib import Path

def import_package(package_path:Path):
    package_path = Path(package_path)
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

def get_child_members(module, root_path:Path=None):
    members = inspect.getmembers(module)
    def is_child_member(member):
        if root_path is None: return True
        if inspect.ismodule(member):
            member_file = getattr(member, "__file__", "")
        else:
            member_module = inspect.getmodule(module)
            member_file = getattr(member_module, "__file__", "")
        return member_file.find(str(root_path)) != -1
    members = list(map(is_child_member, members))
    return members

package_path = Path("C:/Users/user/Python/python-uml-drawer/diagrams")

module = import_package(package_path)
inspect.getmembers(module)