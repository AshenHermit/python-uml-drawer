

def class_separator_line_xml(id:str, parent:str):
    return f"""
<mxCell id="{id}" value="" style="line;strokeWidth=1;fillColor=none;align=left;verticalAlign=middle;spacingTop=-1;spacingLeft=3;spacingRight=3;rotatable=0;labelPosition=right;points=[];portConstraint=eastwest;" parent="{parent}" vertex="1">
    <mxGeometry y="46" width="200" height="8" as="geometry"/>
</mxCell>"""

def class_row_xml(id:str, parent:str):
    return f"""
<mxCell id="{id}" value="text" style="text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;spacingLeft=4;spacingRight=4;overflow=hidden;rotatable=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;" parent="{parent}" vertex="1">
    <mxGeometry y="54" width="200" height="20" as="geometry"/>
</mxCell>"""

def class_xml(id:str, parent:str, value:str="ClassNode", x:float=0, y:float=0, width:float=200, height:float=100, start_size:float=30.0):
    return f"""
<mxCell id="{id}" value="{value}" style="swimlane;fontStyle=1;align=center;verticalAlign=middle;childLayout=stackLayout;horizontal=1;startSize={start_size};horizontalStack=0;resizeParent=1;resizeLast=0;collapsible=1;marginBottom=0;rounded=0;shadow=0;strokeWidth=1;fontFamily=Courier New;fillColor=none;" parent="{parent}" vertex="1">
    <mxGeometry x="{x}" y="{y}" width="{width}" height="{height}" as="geometry">
    </mxGeometry>
</mxCell>"""