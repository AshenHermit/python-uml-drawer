from os import stat
import typing
from pathlib import Path

import requests
import re
import json

CWD = Path(__file__).parent.resolve()

# https://raw.githubusercontent.com/jgraph/mxgraph/ff141aab158417bd866e2dfebd06c61d40773cd2/javascript/src/js/util/mxConstants.js

def insert_str(source:str, sub:str, pos:int):
    return source[:pos] + sub + source[pos:]

class DictConfig():
    def __init__(self, config_dict:dict=None) -> None:
        if config_dict is not None and type(config_dict) is not dict: 
            raise ValueError("type of config_dict argument must be a dict")
        self.__config_dict = config_dict or {}
    
    def __getattr__(self, name:str):
        if name in self.__config_dict:
            return self.__config_dict[name]
        else:
            return None

    @staticmethod
    def from_json(text):
        try:
            data = json.loads(text)
            config = DictConfig(data)
        except:
            config = DictConfig()
        return config


class CodeGenerator():
    def __init__(self, filepath:Path, part_name:str="") -> None:
        self.filepath = filepath
        self.part_name = part_name

    def generate(self):
        # forming marks
        upper_part_name = self.part_name.upper()
        part_mark = "#${}_GENERATED_PART_{}$"
        part_config_mark = part_mark.format(upper_part_name, "CONFIG")
        part_start_mark = part_mark.format(upper_part_name, "START")
        part_end_mark = part_mark.format(upper_part_name, "END")

        text:str = self.filepath.read_text()
        
        #part start
        part_start_pos = text.find(part_start_mark)
        if part_start_pos == -1: return
        indent = text[max(0, text.rfind("\n", None, part_start_pos)+1):part_start_pos]
        
        #config
        part_config_pos = text.find(part_config_mark)
        if part_config_pos != -1:
            config = text[part_config_pos+len(part_config_mark):text.find("\n", part_config_pos)].strip()
            config = DictConfig.from_json(config)
        else:
            config = DictConfig()


        after_start_mark = part_start_pos+len(part_start_mark)
        tail_text = text[after_start_mark:]
        text = text[:after_start_mark]+"\n"+indent
        gen_text_insert_pos = len(text)
        text += tail_text

        # part end
        part_end_pos = text.find(part_end_mark)
        if part_end_pos == -1:
            text = text[:after_start_mark]+"\n"+indent+part_end_mark+text[after_start_mark:]
            part_end_pos = text.find(part_end_mark)

        text = text[:gen_text_insert_pos] + text[part_end_pos:]
        text = insert_str(text, "\n"+indent, gen_text_insert_pos)

        generated_text = self.get_generated_part(config)
        generated_text = generated_text.replace("\n", "\n"+indent)
        text = insert_str(text, generated_text, gen_text_insert_pos)
        self.filepath.write_text(text)
        
    
    def get_generated_part(self, config:DictConfig)->str:
        return "#keke"

class WebFileReader():
    def __init__(self, url) -> None:
        self._url = url
    @property
    def text(self):
        if getattr(self, "_text", None) is None:
            try:
                self._text = requests.get(self._url).text
            except:
                self._text = ""
        return self._text

class Variable():
    def __init__(self, doc:str, name:str, value:typing.Any) -> None:
        self.doc = doc
        self.name = name
        self.value = value
    
    @staticmethod
    def from_js_match(mdoc:str, mname:str, mvalue:str):
        doc = re.sub(r"^[\t \*\/]+", "", mdoc, flags=re.MULTILINE)
        name = mname
        quotes_pat = re.compile(r"((^\'|\'$)|(^\"|\"$)|(^\`|\`$))")
        if quotes_pat.search(mvalue) is not None:
            value = quotes_pat.sub("", mvalue)
        else:
            try:
                value = float(mvalue)
            except:
                value = str(mvalue)
        var = Variable(doc, name, value)
        return var

class PropertiesGatherer():
    def __init__(self, text) -> None:
        self.text = text
    
    def gather(self)->typing.List[Variable]:
        variables:list[Variable] = []

        text = self.text
        text = text[text.find("{")+1:]

        pat = re.compile(
            r"(\/\*\*[\S\s]*?(?=\*\/)\*\/)[\S\s]*?(?=\S)([\S\s]*?(?=:))\s*:\s*([^,\n]+)", 
            flags=re.MULTILINE)

        for match in pat.finditer(text):
            var = Variable.from_js_match(
                match.group(1), match.group(2), match.group(3)
            )
            variables.append(var)
        return variables

class StyleClassGenerator(CodeGenerator):
    def __init__(self, filepath: Path) -> None:
        super().__init__(filepath, part_name="style")
        self.constants_js = WebFileReader("https://raw.githubusercontent.com/jgraph/mxgraph/ff141aab158417bd866e2dfebd06c61d40773cd2/javascript/src/js/util/mxConstants.js")

    def get_generated_part(self, config:DictConfig) -> str:
        prop_gatherer = PropertiesGatherer(self.constants_js.text)
        variables:list[Variable] = prop_gatherer.gather()
        variables = list(filter(lambda v: v.name.startswith("STYLE_"), variables))

        part = ""
        for var in variables:
            if var.value in config.execlude: continue
            var.doc = var.doc.replace("\n", "\n    ").strip()
            part += f"@property\n"
            part += f"def {var.value}(self):\n"
            part += f"    \"\"\"\n    {var.doc}\n    \"\"\"\n"
            part += f"    return self[\"{var.value}\"]\n"
            part += f"@{var.value}.setter\n"
            part += f"def {var.value}(self, value): self[\"{var.value}\"] = value\n"
            part += f"\n"

        return part

def main():
    gen = StyleClassGenerator(CWD/"../diagrams/style.py")
    gen.generate()

if __name__ == '__main__':
    main()
