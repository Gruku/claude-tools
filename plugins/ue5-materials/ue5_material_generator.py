#!/usr/bin/env python3
"""
UE5 Material Node Generator
Converts simple YAML definitions to UE5 Material Editor clipboard format.

Usage:
    python ue5_material_generator.py input.yaml > output.txt
    python ue5_material_generator.py input.yaml -o output.txt

Then copy the contents of output.txt and paste into UE5 Material Editor (Ctrl+V).

Node types can be:
- Built-in: Constant, Time, Custom, MakeFloat4/3/2, NamedRerouteDeclaration/Usage, Comment
- Registry: Any node defined in node_registry.yaml (Add, Multiply, Lerp, etc.)
- Generic: Any node with full specification in YAML
"""

import yaml
import uuid
import argparse
import sys
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path


# =============================================================================
# FIXED GUIDS FOR ENGINE FUNCTIONS
# =============================================================================

MAKEFLOAT4_GUIDS = {
    'X': '529C1D96441E07EB03A9E59B8A7F67B6',
    'Y': 'B5BD7D1B494F6928732CCDA1C63D8E15',
    'Z': '050F17B8471570B47A802CB7CAA5A201',
    'A': '4302C68A4D3ABCFB34DE619C2867A488',
    'Result': '0DD6F9954C067C3E5DDBBBA0D6910DD2',
}

MAKEFLOAT3_GUIDS = {
    'X': '2A09FD7E4BD8CE8029E7A3B58DE3B71C',
    'Y': '5A62C58746F8D5D62C4C7D90E8F10A34',
    'Z': '8B15E09648C2A1F43E5B9C12D7A63F58',
    'Result': 'CE48D3B54A9F72E16D80B5A49C2E8D71',
}

MAKEFLOAT2_GUIDS = {
    'X': 'F1A3C72B4E6D89052B4A8C9DE3F71B26',
    'Y': '3D5E8A1C4B7F62943C6D9E0FA2B84C57',
    'Result': '7E2B9D4A5C8F31764A5B6C7D8E9F0A12',
}


def generate_guid() -> str:
    """Generate a valid UE5 GUID (32 uppercase hex characters)."""
    return uuid.uuid4().hex.upper()


def load_node_registry() -> Dict[str, Any]:
    """Load node definitions from the registry YAML file next to this script."""
    path = Path(__file__).parent / 'node_registry.yaml'
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


# Global registry
NODE_REGISTRY = load_node_registry()


# =============================================================================
# PIN CLASS
# =============================================================================

@dataclass
class Pin:
    """Represents a material graph pin."""
    pin_id: str
    pin_name: str
    direction: str = "EGPD_Input"
    category: str = ""
    subcategory: str = ""
    linked_to: List[Tuple[str, str]] = field(default_factory=list)

    def to_string(self) -> str:
        linked_str = ""
        if self.linked_to:
            links = ",".join([f"{node} {pin}" for node, pin in self.linked_to])
            linked_str = f",LinkedTo=({links},)"

        return (
            f"CustomProperties Pin ("
            f"PinId={self.pin_id},"
            f"PinName=\"{self.pin_name}\","
            f"PinFriendlyName=NSLOCTEXT(\"MaterialGraphNode\", \"Space\", \" \"),"
            f"PinType.PinCategory=\"{self.category}\","
            f"PinType.PinSubCategory=\"{self.subcategory}\","
            f"PinType.PinSubCategoryObject=None,"
            f"PinType.PinSubCategoryMemberReference=(),"
            f"PinType.PinValueType=(),"
            f"PinType.ContainerType=None,"
            f"PinType.bIsReference=False,"
            f"PinType.bIsConst=False,"
            f"PinType.bIsWeakPointer=False,"
            f"PinType.bIsUObjectWrapper=False,"
            f"PinType.bSerializeAsSinglePrecisionFloat=False,"
            f"Direction=\"{self.direction}\"{linked_str},"
            f"PersistentGuid=00000000000000000000000000000000,"
            f"bHidden=False,"
            f"bNotConnectable=False,"
            f"bDefaultValueIsReadOnly=False,"
            f"bDefaultValueIsIgnored=False,"
            f"bAdvancedView=False,"
            f"bOrphanedPin=False"
            f")"
        )


# =============================================================================
# BASE NODE CLASS
# =============================================================================

@dataclass
class MaterialNode:
    """Base class for material nodes."""
    name: str
    node_name: str
    expression_name: str
    expression_class: str
    pos_x: int = 0
    pos_y: int = 0
    material_path: str = "/Script/UnrealEd.PreviewMaterial'/Engine/Transient.M_Preview'"
    node_guid: str = field(default_factory=generate_guid)
    expression_guid: str = field(default_factory=generate_guid)
    desc: str = ""
    pins: List[Pin] = field(default_factory=list)
    input_expressions: Dict[str, str] = field(default_factory=dict)

    # For output pin lookup
    output_pin_id: str = ""
    input_pin_ids: Dict[str, str] = field(default_factory=dict)

    def get_expression_path(self) -> str:
        return f"/Script/Engine.{self.expression_class}'{self.node_name}.{self.expression_name}'"

    def get_inner_properties(self) -> str:
        """Override in subclasses for type-specific properties."""
        return ""

    def get_outer_node_class(self) -> str:
        return "/Script/UnrealEd.MaterialGraphNode"

    def to_string(self) -> str:
        inner_props = self.get_inner_properties()
        desc_props = ""
        outer_comment = ""

        if self.desc:
            desc_props = f"\n      Desc=\"{self.desc}\"\n      bCommentBubbleVisible=True"
            outer_comment = f"\n   bCommentBubbleVisible=True\n   NodeComment=\"{self.desc}\""

        pins_str = "\n   ".join([p.to_string() for p in self.pins])

        return f"""Begin Object Class={self.get_outer_node_class()} Name=\"{self.node_name}\" ExportPath=\"{self.get_outer_node_class()}'{self.node_name}'\"
   Begin Object Class=/Script/Engine.{self.expression_class} Name=\"{self.expression_name}\" ExportPath=\"/Script/Engine.{self.expression_class}'{self.node_name}.{self.expression_name}'\"
   End Object
   Begin Object Name=\"{self.expression_name}\" ExportPath=\"/Script/Engine.{self.expression_class}'{self.node_name}.{self.expression_name}'\"{inner_props}{desc_props}
      MaterialExpressionEditorX={self.pos_x}
      MaterialExpressionEditorY={self.pos_y}
      MaterialExpressionGuid={self.expression_guid}
      Material=\"{self.material_path}\"
   End Object
   MaterialExpression=\"/Script/Engine.{self.expression_class}'{self.expression_name}'\"
   NodePosX={self.pos_x}
   NodePosY={self.pos_y}{outer_comment}
   NodeGuid={self.node_guid}
   {pins_str}
End Object"""


# =============================================================================
# REGISTRY-BASED NODE (for Add, Multiply, Lerp, etc.)
# =============================================================================

class RegistryNode(MaterialNode):
    """Node created from registry definition."""

    def __init__(self, name: str, node_type: str, node_index: int,
                 registry_def: Dict[str, Any], yaml_props: Dict[str, Any] = None, **kwargs):
        expr_class = registry_def['expression_class']
        expr_name = f"{expr_class}_{name}"

        # Determine graph node class
        graph_class = registry_def.get('graph_node_class', '/Script/UnrealEd.MaterialGraphNode')

        super().__init__(
            name=name,
            node_name=f"MaterialGraphNode_{node_index}",
            expression_name=expr_name,
            expression_class=expr_class,
            **kwargs
        )

        self.registry_def = registry_def
        self.yaml_props = yaml_props or {}
        self._graph_class = graph_class

        # Build properties from registry defaults + yaml overrides
        self.properties = dict(registry_def.get('properties', {}))

        # Apply property mappings
        mappings = registry_def.get('property_mappings', {})
        for yaml_key, ue_key in mappings.items():
            if yaml_key in self.yaml_props:
                self.properties[ue_key] = self.yaml_props[yaml_key]

        # Direct property overrides
        if 'properties' in self.yaml_props:
            self.properties.update(self.yaml_props['properties'])

        # Create input pins
        self.input_pin_ids = {}
        for input_def in registry_def.get('inputs', []):
            input_name = input_def['name']
            pin_name = input_def.get('pin_name', input_name)
            pin_id = generate_guid()
            self.input_pin_ids[input_name] = pin_id
            self.pins.append(Pin(
                pin_id=pin_id,
                pin_name=pin_name,
                direction="EGPD_Input",
                category=input_def.get('category', ''),
                subcategory=input_def.get('subcategory', '')
            ))

        # Create output pins
        outputs = registry_def.get('outputs', [{'name': 'Output'}])
        for i, output_def in enumerate(outputs):
            output_name = output_def['name']
            pin_id = generate_guid()
            if i == 0:
                self.output_pin_id = pin_id
            self.pins.append(Pin(
                pin_id=pin_id,
                pin_name=output_name,
                direction="EGPD_Output",
                subcategory=output_def.get('subcategory', '')
            ))

    def get_outer_node_class(self) -> str:
        return self._graph_class

    def get_inner_properties(self) -> str:
        props_lines = []

        # Add input expressions
        inputs_def = self.registry_def.get('inputs', [])
        for input_def in inputs_def:
            input_name = input_def['name']
            if input_name in self.input_expressions:
                props_lines.append(f"{input_name}=(Expression=\"{self.input_expressions[input_name]}\")")

        # Add other properties
        for key, value in self.properties.items():
            if isinstance(value, bool):
                props_lines.append(f"{key}={'True' if value else 'False'}")
            elif isinstance(value, str):
                # Check if it's already a UE format like "(R=1.0,G=1.0,...)"
                if value.startswith('(') or value.startswith('/'):
                    props_lines.append(f"{key}={value}")
                else:
                    props_lines.append(f"{key}=\"{value}\"")
            else:
                props_lines.append(f"{key}={value}")

        if props_lines:
            return "\n      " + "\n      ".join(props_lines)
        return ""


# =============================================================================
# GENERIC NODE (full flexibility)
# =============================================================================

class GenericNode(MaterialNode):
    """Fully customizable node specified entirely in YAML."""

    def __init__(self, name: str, node_index: int, yaml_def: Dict[str, Any], **kwargs):
        expr_class = yaml_def['expression_class']
        expr_name = yaml_def.get('expression_name', f"{expr_class}_{name}")
        graph_class = yaml_def.get('graph_node_class', '/Script/UnrealEd.MaterialGraphNode')

        super().__init__(
            name=name,
            node_name=yaml_def.get('node_name', f"MaterialGraphNode_{node_index}"),
            expression_name=expr_name,
            expression_class=expr_class,
            **kwargs
        )

        self.yaml_def = yaml_def
        self._graph_class = graph_class
        self.properties = yaml_def.get('properties', {})

        # Create input pins
        self.input_pin_ids = {}
        for input_def in yaml_def.get('inputs', []):
            if isinstance(input_def, str):
                input_name = input_def
                input_def = {'name': input_name}
            else:
                input_name = input_def['name']

            pin_name = input_def.get('pin_name', input_name)
            pin_id = generate_guid()
            self.input_pin_ids[input_name] = pin_id
            self.pins.append(Pin(
                pin_id=pin_id,
                pin_name=pin_name,
                direction="EGPD_Input",
                category=input_def.get('category', ''),
                subcategory=input_def.get('subcategory', '')
            ))

        # Create output pins
        outputs = yaml_def.get('outputs', [{'name': 'Output'}])
        for i, output_def in enumerate(outputs):
            if isinstance(output_def, str):
                output_name = output_def
                output_def = {'name': output_name}
            else:
                output_name = output_def['name']

            pin_id = generate_guid()
            if i == 0:
                self.output_pin_id = pin_id
            self.pins.append(Pin(
                pin_id=pin_id,
                pin_name=output_name,
                direction="EGPD_Output",
                subcategory=output_def.get('subcategory', '')
            ))

    def get_outer_node_class(self) -> str:
        return self._graph_class

    def get_inner_properties(self) -> str:
        props_lines = []

        # Add input expressions
        for input_name, expr in self.input_expressions.items():
            props_lines.append(f"{input_name}=(Expression=\"{expr}\")")

        # Add other properties
        for key, value in self.properties.items():
            if isinstance(value, bool):
                props_lines.append(f"{key}={'True' if value else 'False'}")
            elif isinstance(value, str):
                if value.startswith('(') or value.startswith('/'):
                    props_lines.append(f"{key}={value}")
                else:
                    props_lines.append(f"{key}=\"{value}\"")
            else:
                props_lines.append(f"{key}={value}")

        if props_lines:
            return "\n      " + "\n      ".join(props_lines)
        return ""


# =============================================================================
# BUILT-IN NODE TYPES (special handling required)
# =============================================================================

class ConstantNode(MaterialNode):
    """Scalar constant node."""

    def __init__(self, name: str, value: float, node_index: int, **kwargs):
        expr_name = f"MaterialExpressionConstant_{name}"
        super().__init__(
            name=name,
            node_name=f"MaterialGraphNode_{node_index}",
            expression_name=expr_name,
            expression_class="MaterialExpressionConstant",
            **kwargs
        )
        self.value = value
        self.output_pin_id = generate_guid()
        self.pins.append(Pin(
            pin_id=self.output_pin_id,
            pin_name="Output",
            direction="EGPD_Output"
        ))

    def get_inner_properties(self) -> str:
        return f"\n      R={self.value}"


class Constant3VectorNode(MaterialNode):
    """RGB/Vector3 constant node."""

    def __init__(self, name: str, r: float, g: float, b: float, node_index: int, **kwargs):
        expr_name = f"MaterialExpressionConstant3Vector_{name}"
        super().__init__(
            name=name,
            node_name=f"MaterialGraphNode_{node_index}",
            expression_name=expr_name,
            expression_class="MaterialExpressionConstant3Vector",
            **kwargs
        )
        self.r, self.g, self.b = r, g, b
        self.output_pin_id = generate_guid()
        self.pins.append(Pin(
            pin_id=self.output_pin_id,
            pin_name="Output",
            direction="EGPD_Output"
        ))

    def get_inner_properties(self) -> str:
        return f"\n      Constant=(R={self.r},G={self.g},B={self.b},A=0.000000)"


class Constant4VectorNode(MaterialNode):
    """RGBA/Vector4 constant node."""

    def __init__(self, name: str, r: float, g: float, b: float, a: float, node_index: int, **kwargs):
        expr_name = f"MaterialExpressionConstant4Vector_{name}"
        super().__init__(
            name=name,
            node_name=f"MaterialGraphNode_{node_index}",
            expression_name=expr_name,
            expression_class="MaterialExpressionConstant4Vector",
            **kwargs
        )
        self.r, self.g, self.b, self.a = r, g, b, a
        self.output_pin_id = generate_guid()
        self.pins.append(Pin(
            pin_id=self.output_pin_id,
            pin_name="Output",
            direction="EGPD_Output"
        ))

    def get_inner_properties(self) -> str:
        return f"\n      Constant=(R={self.r},G={self.g},B={self.b},A={self.a})"


class TimeNode(MaterialNode):
    """Time node."""

    def __init__(self, name: str, node_index: int, ignore_pause: bool = False, **kwargs):
        expr_name = f"MaterialExpressionTime_{name}"
        super().__init__(
            name=name,
            node_name=f"MaterialGraphNode_{node_index}",
            expression_name=expr_name,
            expression_class="MaterialExpressionTime",
            **kwargs
        )
        self.ignore_pause = ignore_pause
        self.output_pin_id = generate_guid()
        self.pins.append(Pin(
            pin_id=self.output_pin_id,
            pin_name="Output",
            direction="EGPD_Output"
        ))

    def get_inner_properties(self) -> str:
        if self.ignore_pause:
            return "\n      bIgnorePause=True"
        return ""


class NamedRerouteDeclarationNode(MaterialNode):
    """Named reroute declaration (setter)."""

    def __init__(self, name: str, var_name: str, node_index: int,
                 color: Tuple[float, float, float] = (0.0, 0.0, 0.0), **kwargs):
        expr_name = f"MaterialExpressionNamedRerouteDeclaration_{name}"
        super().__init__(
            name=name,
            node_name=f"MaterialGraphNode_{node_index}",
            expression_name=expr_name,
            expression_class="MaterialExpressionNamedRerouteDeclaration",
            **kwargs
        )
        self.var_name = var_name
        self.variable_guid = generate_guid()
        self.color = color
        self.input_expression: Optional[str] = None

        self.input_pin_ids = {'Input': generate_guid()}
        self.output_pin_id = generate_guid()

        self.pins.append(Pin(
            pin_id=self.input_pin_ids['Input'],
            pin_name="Input",
            direction="EGPD_Input",
            category="required"
        ))
        self.pins.append(Pin(
            pin_id=self.output_pin_id,
            pin_name="Output",
            direction="EGPD_Output"
        ))

    def get_inner_properties(self) -> str:
        input_expr = ""
        if self.input_expression:
            input_expr = f"\n      Input=(Expression=\"{self.input_expression}\")"
        return f"""{input_expr}
      Name=\"{self.var_name}\"
      NodeColor=(R={self.color[0]},G={self.color[1]},B={self.color[2]},A=1.000000)
      VariableGuid={self.variable_guid}"""


class NamedRerouteUsageNode(MaterialNode):
    """Named reroute usage (getter).

    Can reference either a declaration node created in the same graph
    (pass `declaration=<NamedRerouteDeclarationNode>`) or an external
    declaration that already exists in the target material
    (pass `declaration_name=<str>` and `declaration_guid=<str>`).
    """

    def __init__(self, name: str, node_index: int,
                 declaration: 'NamedRerouteDeclarationNode' = None,
                 declaration_name: str = None, declaration_guid: str = None,
                 **kwargs):
        expr_name = f"MaterialExpressionNamedRerouteUsage_{name}"
        super().__init__(
            name=name,
            node_name=f"MaterialGraphNode_{node_index}",
            expression_name=expr_name,
            expression_class="MaterialExpressionNamedRerouteUsage",
            **kwargs
        )
        self.declaration = declaration
        # Support external declarations (not created in this graph)
        self._decl_name = declaration_name or (declaration.expression_name if declaration else None)
        self._decl_guid = declaration_guid or (declaration.variable_guid if declaration else None)
        self.output_pin_id = generate_guid()
        self.pins.append(Pin(
            pin_id=self.output_pin_id,
            pin_name="Output",
            direction="EGPD_Output"
        ))

    def get_inner_properties(self) -> str:
        decl_path = f"/Script/Engine.MaterialExpressionNamedRerouteDeclaration'{self._decl_name}'"
        return f"""
      Declaration=\"{decl_path}\"
      DeclarationGuid={self._decl_guid}"""


class MakeFloatNode(MaterialNode):
    """MakeFloat2/3/4 function call node."""

    def __init__(self, name: str, node_index: int, num_components: int, **kwargs):
        expr_name = f"MaterialExpressionMaterialFunctionCall_{name}"
        super().__init__(
            name=name,
            node_name=f"MaterialGraphNode_{node_index}",
            expression_name=expr_name,
            expression_class="MaterialExpressionMaterialFunctionCall",
            **kwargs
        )

        self.num_components = num_components
        self.input_expressions: Dict[str, str] = {}

        # Select GUIDs based on component count
        if num_components == 4:
            self.guids = MAKEFLOAT4_GUIDS
            self.func_path = "/Engine/Functions/Engine_MaterialFunctions02/Utility/MakeFloat4.MakeFloat4"
            self.input_names = ['X', 'Y', 'Z', 'A']
        elif num_components == 3:
            self.guids = MAKEFLOAT3_GUIDS
            self.func_path = "/Engine/Functions/Engine_MaterialFunctions02/Utility/MakeFloat3.MakeFloat3"
            self.input_names = ['X', 'Y', 'Z']
        else:  # 2
            self.guids = MAKEFLOAT2_GUIDS
            self.func_path = "/Engine/Functions/Engine_MaterialFunctions02/Utility/MakeFloat2.MakeFloat2"
            self.input_names = ['X', 'Y']

        # Create pins
        self.pin_ids = {}
        for input_name in self.input_names:
            pin_id = generate_guid()
            self.pin_ids[input_name] = pin_id
            self.pins.append(Pin(
                pin_id=pin_id,
                pin_name=f"{input_name} (S)",
                direction="EGPD_Input",
                category="optional"
            ))

        self.pin_ids['Result'] = generate_guid()
        self.output_pin_id = self.pin_ids['Result']
        self.pins.append(Pin(
            pin_id=self.output_pin_id,
            pin_name="Result",
            direction="EGPD_Output"
        ))

    def get_inner_properties(self) -> str:
        func_inputs = []
        for i, input_name in enumerate(self.input_names):
            expr = self.input_expressions.get(input_name, "")
            if expr:
                func_inputs.append(
                    f"FunctionInputs({i})=(ExpressionInputId={self.guids[input_name]},"
                    f"Input=(Expression=\"{expr}\",InputName=\"{input_name}\"))"
                )
            else:
                func_inputs.append(
                    f"FunctionInputs({i})=(ExpressionInputId={self.guids[input_name]},"
                    f"Input=(InputName=\"{input_name}\"))"
                )

        func_inputs_str = "\n      ".join(func_inputs)

        return f"""
      MaterialFunction=\"/Script/Engine.MaterialFunction'{self.func_path}'\"
      {func_inputs_str}
      FunctionOutputs(0)=(ExpressionOutputId={self.guids['Result']},Output=(OutputName=\"Result\"))
      Outputs(0)=(OutputName=\"Result\")"""


class CustomNode(MaterialNode):
    """Custom HLSL node."""

    def __init__(self, name: str, code: str, node_index: int,
                 output_type: str = "CMOT_Float4",
                 inputs: List[Tuple[str, str]] = None,
                 additional_outputs: List[Tuple[str, str]] = None,
                 **kwargs):
        expr_name = f"MaterialExpressionCustom_{name}"
        super().__init__(
            name=name,
            node_name=f"MaterialGraphNode_Custom_{node_index}",
            expression_name=expr_name,
            expression_class="MaterialExpressionCustom",
            **kwargs
        )
        self.code = code
        self.output_type = output_type
        self.input_names = inputs or []
        self.additional_outputs = additional_outputs or []
        self.input_expressions: Dict[str, str] = {}

        # Input pins
        self.input_pin_ids: Dict[str, str] = {}
        for input_name, _ in self.input_names:
            pin_id = generate_guid()
            self.input_pin_ids[input_name] = pin_id
            self.pins.append(Pin(
                pin_id=pin_id,
                pin_name=input_name,
                direction="EGPD_Input",
                category="required"
            ))

        # Output pins
        self.output_pin_id = generate_guid()
        self.pins.append(Pin(
            pin_id=self.output_pin_id,
            pin_name="Output",
            direction="EGPD_Output"
        ))

        self.additional_output_pin_ids: Dict[str, str] = {}
        for output_name, _ in self.additional_outputs:
            pin_id = generate_guid()
            self.additional_output_pin_ids[output_name] = pin_id
            self.pins.append(Pin(
                pin_id=pin_id,
                pin_name=output_name,
                direction="EGPD_Output"
            ))

    def get_outer_node_class(self) -> str:
        return "/Script/UnrealEd.MaterialGraphNode_Custom"

    def get_inner_properties(self) -> str:
        # Normalize line endings first, then escape in correct order
        escaped_code = self.code.replace('\r\n', '\n').replace('\r', '\n')
        escaped_code = escaped_code.replace('\\', '\\\\')   # Backslashes first
        escaped_code = escaped_code.replace('"', '\\"')      # Then quotes
        escaped_code = escaped_code.replace('\t', '    ')    # Tabs to spaces
        escaped_code = escaped_code.replace('\n', '\\r\\n')  # Line endings last

        inputs_lines = []
        for i, (input_name, _) in enumerate(self.input_names):
            expr = self.input_expressions.get(input_name, "")
            if expr:
                inputs_lines.append(f"Inputs({i})=(InputName=\"{input_name}\",Input=(Expression=\"{expr}\"))")
            else:
                inputs_lines.append(f"Inputs({i})=(InputName=\"{input_name}\")")

        add_outputs_lines = []
        for i, (output_name, output_type) in enumerate(self.additional_outputs):
            add_outputs_lines.append(f"AdditionalOutputs({i})=(OutputName=\"{output_name}\",OutputType={output_type})")

        outputs_lines = ["Outputs(0)=(OutputName=\"return\")"]
        for i, (output_name, _) in enumerate(self.additional_outputs):
            outputs_lines.append(f"Outputs({i+1})=(OutputName=\"{output_name}\")")

        props = f"""
      Code=\"{escaped_code}\"
      Description=\"{self.name}\"
      OutputType={self.output_type}"""

        if inputs_lines:
            props += "\n      " + "\n      ".join(inputs_lines)
        if add_outputs_lines:
            props += "\n      " + "\n      ".join(add_outputs_lines)

        props += "\n      bShowOutputNameOnPin=True"
        props += "\n      " + "\n      ".join(outputs_lines)

        return props


class CommentNode(MaterialNode):
    """Comment box node."""

    def __init__(self, name: str, text: str, node_index: int,
                 size_x: int = 400, size_y: int = 300,
                 color: Tuple[float, float, float] = (1.0, 1.0, 1.0),
                 contains_nodes: List[str] = None,
                 **kwargs):
        expr_name = f"MaterialExpressionComment_{name}"
        super().__init__(
            name=name,
            node_name=f"MaterialGraphNode_Comment_{node_index}",
            expression_name=expr_name,
            expression_class="MaterialExpressionComment",
            **kwargs
        )
        self.text = text
        self.size_x = size_x
        self.size_y = size_y
        self.color = color
        self.contains_nodes = contains_nodes or []

    def get_outer_node_class(self) -> str:
        return "/Script/UnrealEd.MaterialGraphNode_Comment"

    def get_inner_properties(self) -> str:
        return f"""
      SizeX={self.size_x}
      SizeY={self.size_y}
      Text=\"{self.text}\"
      CommentColor=(R={self.color[0]},G={self.color[1]},B={self.color[2]},A=1.000000)"""

    def to_string(self) -> str:
        return f"""Begin Object Class={self.get_outer_node_class()} Name=\"{self.node_name}\" ExportPath=\"{self.get_outer_node_class()}'{self.node_name}'\"
   Begin Object Class=/Script/Engine.{self.expression_class} Name=\"{self.expression_name}\" ExportPath=\"/Script/Engine.{self.expression_class}'{self.node_name}.{self.expression_name}'\"
   End Object
   Begin Object Name=\"{self.expression_name}\" ExportPath=\"/Script/Engine.{self.expression_class}'{self.node_name}.{self.expression_name}'\"{self.get_inner_properties()}
      MaterialExpressionEditorX={self.pos_x}
      MaterialExpressionEditorY={self.pos_y}
      MaterialExpressionGuid={self.expression_guid}
      Material=\"{self.material_path}\"
   End Object
   MaterialExpression=\"/Script/Engine.{self.expression_class}'{self.expression_name}'\"
   NodePosX={self.pos_x}
   NodePosY={self.pos_y}
   NodeWidth={self.size_x}
   NodeHeight={self.size_y}
   NodeComment=\"{self.text}\"
   CommentColor=(R={self.color[0]},G={self.color[1]},B={self.color[2]},A=1.000000)
   NodeGuid={self.node_guid}
End Object"""


# =============================================================================
# MATERIAL GRAPH BUILDER
# =============================================================================

class MaterialGraphBuilder:
    """Builds a material graph from YAML definition."""

    def __init__(self, yaml_data: Dict[str, Any]):
        if yaml_data is None:
            raise ValueError("YAML data is empty or invalid")
        self.data = yaml_data
        self.nodes: Dict[str, MaterialNode] = {}
        self.node_index = 1
        self.custom_node_index = 1
        self.comment_index = 1

        self.material_path = yaml_data.get('material_path',
            "/Script/UnrealEd.PreviewMaterial'/Engine/Transient.M_Preview'")
        self.position_start = yaml_data.get('position_start', [0, 0])
        self.spacing_x = yaml_data.get('spacing_x', 256)
        self.spacing_y = yaml_data.get('spacing_y', 96)

    def build(self) -> str:
        """Build the complete material graph."""
        self._create_nodes()
        self._wire_connections()
        self._compute_layout()
        self._position_comments()
        return self._generate_output()

    def _create_nodes(self):
        """Create all nodes from YAML definition.

        Nodes are created with placeholder positions. Final positions are
        computed by _compute_layout() after connections are wired, using
        topology-based column assignment.
        """
        nodes_data = self.data.get('nodes', [])
        self._manual_positions: Dict[str, bool] = {}

        for node_def in nodes_data:
            node_type = node_def.get('type', 'Constant')
            name = node_def['name']

            # Track whether user specified explicit positions
            has_manual = 'pos_x' in node_def or 'pos_y' in node_def
            self._manual_positions[name] = has_manual

            pos_x = node_def.get('pos_x', 0)
            pos_y = node_def.get('pos_y', 0)

            common_kwargs = {
                'pos_x': pos_x,
                'pos_y': pos_y,
                'material_path': self.material_path,
                'desc': node_def.get('desc', '')
            }

            node = self._create_node(node_type, name, node_def, common_kwargs)
            self.nodes[name] = node

    def _compute_layout(self):
        """Compute node positions based on connection topology.

        Assigns nodes to columns by graph depth (longest path from roots),
        then vertically centers non-leaf nodes relative to their inputs.
        Nodes with explicit pos_x/pos_y in YAML are left unchanged.
        """
        connections = self.data.get('connections', [])

        # Parse connections to build adjacency lists (exclude Comments)
        incoming: Dict[str, List[str]] = {name: [] for name in self.nodes if not isinstance(self.nodes[name], CommentNode)}
        outgoing: Dict[str, List[str]] = {name: [] for name in self.nodes if not isinstance(self.nodes[name], CommentNode)}

        for conn in connections:
            parts = conn.split('->')
            if len(parts) != 2:
                continue
            source_name = parts[0].strip().split('.')[0]
            target_name = parts[1].strip().split('.')[0]
            if source_name in self.nodes and target_name in self.nodes:
                incoming[target_name].append(source_name)
                outgoing[source_name].append(target_name)

        # Compute depth via longest path from roots (nodes with no inputs)
        depth: Dict[str, int] = {}
        for name in self.nodes:
            if isinstance(self.nodes[name], CommentNode):
                continue
            if not incoming.get(name, []):
                depth[name] = 0

        # Propagate depths iteratively
        changed = True
        max_iter = len(self.nodes) + 1
        iterations = 0
        while changed and iterations < max_iter:
            changed = False
            iterations += 1
            for name in list(depth.keys()):
                for target in outgoing.get(name, []):
                    new_depth = depth[name] + 1
                    if target not in depth or new_depth > depth[target]:
                        depth[target] = new_depth
                        changed = True

        # Handle disconnected nodes (no incoming or outgoing), skip Comments
        for name in self.nodes:
            if isinstance(self.nodes[name], CommentNode):
                continue
            if name not in depth:
                depth[name] = 0

        # Group nodes by depth, preserving YAML insertion order
        columns: Dict[int, List[str]] = {}
        for name in self.nodes:
            if isinstance(self.nodes[name], CommentNode):
                continue
            d = depth[name]
            columns.setdefault(d, []).append(name)

        # First pass: assign column positions
        start_x = self.position_start[0]
        start_y = self.position_start[1]

        for d, names in sorted(columns.items()):
            col_x = start_x + d * self.spacing_x
            for i, name in enumerate(names):
                if not self._manual_positions.get(name, False):
                    node = self.nodes[name]
                    node.pos_x = col_x
                    node.pos_y = start_y + i * self.spacing_y

        # Second pass: vertically center non-leaf nodes relative to their inputs
        for d in sorted(columns.keys()):
            if d == 0:
                continue
            for name in columns[d]:
                if self._manual_positions.get(name, False):
                    continue
                input_names = incoming.get(name, [])
                if input_names:
                    input_ys = [self.nodes[n].pos_y for n in input_names if n in self.nodes]
                    if input_ys:
                        center_y = (min(input_ys) + max(input_ys)) // 2
                        self.nodes[name].pos_y = center_y

        # Third pass: resolve overlaps within each column
        for d, names in sorted(columns.items()):
            auto_names = [n for n in names if not self._manual_positions.get(n, False)]
            if len(auto_names) < 2:
                continue
            # Sort by current Y position
            auto_names.sort(key=lambda n: self.nodes[n].pos_y)
            # Push apart any nodes that are too close
            min_gap = self.spacing_y
            for i in range(1, len(auto_names)):
                prev_y = self.nodes[auto_names[i - 1]].pos_y
                curr_y = self.nodes[auto_names[i]].pos_y
                if curr_y - prev_y < min_gap:
                    self.nodes[auto_names[i]].pos_y = prev_y + min_gap

    def _position_comments(self):
        """Position comment boxes around their contained nodes after layout."""
        PADDING = 80
        TITLE_HEIGHT = 40
        NODE_WIDTH_EST = 250
        NODE_HEIGHT_EST = 150

        for name, node in self.nodes.items():
            if not isinstance(node, CommentNode):
                continue
            if self._manual_positions.get(name, False):
                continue  # User specified explicit position

            if node.contains_nodes:
                # Compute bounding box from contained nodes
                contained = [self.nodes[n] for n in node.contains_nodes if n in self.nodes]
                if not contained:
                    print(f"Warning: Comment '{name}' contains no valid nodes: {node.contains_nodes}")
                    continue
                min_x = min(n.pos_x for n in contained)
                min_y = min(n.pos_y for n in contained)
                max_x = max(n.pos_x for n in contained)
                max_y = max(n.pos_y for n in contained)

                node.pos_x = min_x - PADDING
                node.pos_y = min_y - PADDING - TITLE_HEIGHT
                node.size_x = (max_x - min_x) + NODE_WIDTH_EST + PADDING * 2
                node.size_y = (max_y - min_y) + NODE_HEIGHT_EST + PADDING * 2 + TITLE_HEIGHT
            else:
                self._auto_group_comment(node)

    def _auto_group_comment(self, comment_node):
        """Fallback: group nodes by naming convention based on comment text."""
        PADDING = 80
        TITLE_HEIGHT = 40
        NODE_WIDTH_EST = 250
        NODE_HEIGHT_EST = 150

        text_lower = comment_node.text.lower()
        matched = []

        for n, nd in self.nodes.items():
            if isinstance(nd, CommentNode):
                continue
            if 'input' in text_lower and (n.startswith('In') or isinstance(nd, (ConstantNode, Constant3VectorNode, Constant4VectorNode, MakeFloatNode))):
                matched.append(nd)
            elif 'output' in text_lower and n.startswith('Out'):
                matched.append(nd)
            elif 'custom' in text_lower and isinstance(nd, CustomNode):
                matched.append(nd)

        if not matched:
            print(f"Warning: Comment '{comment_node.name}' could not auto-detect contained nodes. Specify 'contains' in YAML.")
            return

        min_x = min(n.pos_x for n in matched)
        min_y = min(n.pos_y for n in matched)
        max_x = max(n.pos_x for n in matched)
        max_y = max(n.pos_y for n in matched)

        comment_node.pos_x = min_x - PADDING
        comment_node.pos_y = min_y - PADDING - TITLE_HEIGHT
        comment_node.size_x = (max_x - min_x) + NODE_WIDTH_EST + PADDING * 2
        comment_node.size_y = (max_y - min_y) + NODE_HEIGHT_EST + PADDING * 2 + TITLE_HEIGHT

    def _create_node(self, node_type: str, name: str, node_def: Dict,
                     common_kwargs: Dict) -> MaterialNode:
        """Create a single node based on type."""

        # Built-in types with special handling
        if node_type == 'Constant':
            node = ConstantNode(
                name=name,
                value=node_def.get('value', 0.0),
                node_index=self.node_index,
                **common_kwargs
            )
            self.node_index += 1
            return node

        elif node_type == 'Constant3Vector':
            value = node_def.get('value', [0, 0, 0])
            if len(value) < 3:
                print(f"Warning: Constant3Vector '{name}' needs 3 values, got {len(value)}. Padding with zeros.")
                value = list(value) + [0] * (3 - len(value))
            node = Constant3VectorNode(
                name=name,
                r=value[0], g=value[1], b=value[2],
                node_index=self.node_index,
                **common_kwargs
            )
            self.node_index += 1
            return node

        elif node_type == 'Constant4Vector':
            value = node_def.get('value', [0, 0, 0, 0])
            if len(value) < 4:
                print(f"Warning: Constant4Vector '{name}' needs 4 values, got {len(value)}. Padding with zeros.")
                value = list(value) + [0] * (4 - len(value))
            node = Constant4VectorNode(
                name=name,
                r=value[0], g=value[1], b=value[2], a=value[3],
                node_index=self.node_index,
                **common_kwargs
            )
            self.node_index += 1
            return node

        elif node_type == 'Time':
            node = TimeNode(
                name=name,
                node_index=self.node_index,
                ignore_pause=node_def.get('ignore_pause', False),
                **common_kwargs
            )
            self.node_index += 1
            return node

        elif node_type == 'NamedRerouteDeclaration':
            color = node_def.get('color', [0, 0, 0])
            node = NamedRerouteDeclarationNode(
                name=name,
                var_name=node_def.get('var_name', name),
                node_index=self.node_index,
                color=tuple(color),
                **common_kwargs
            )
            self.node_index += 1
            return node

        elif node_type == 'NamedRerouteUsage':
            node = NamedRerouteUsageNode(
                name=name,
                node_index=self.node_index,
                declaration_name=node_def.get('declaration_name'),
                declaration_guid=node_def.get('declaration_guid'),
                **common_kwargs
            )
            self.node_index += 1
            return node

        elif node_type in ('MakeFloat4', 'MakeFloat3', 'MakeFloat2'):
            num = int(node_type[-1])
            node = MakeFloatNode(
                name=name,
                node_index=self.node_index,
                num_components=num,
                **common_kwargs
            )
            self.node_index += 1
            return node

        elif node_type == 'Custom':
            inputs = [(inp['name'], inp.get('type', 'float'))
                     for inp in node_def.get('inputs', [])]
            outputs = [(out['name'], out.get('type', 'CMOT_Float1'))
                      for out in node_def.get('additional_outputs', [])]
            node = CustomNode(
                name=name,
                code=node_def.get('code', 'return 0;'),
                node_index=self.custom_node_index,
                output_type=node_def.get('output_type', 'CMOT_Float4'),
                inputs=inputs,
                additional_outputs=outputs,
                **common_kwargs
            )
            self.custom_node_index += 1
            return node

        elif node_type == 'Comment':
            node = CommentNode(
                name=name,
                text=node_def.get('text', ''),
                node_index=self.comment_index,
                size_x=node_def.get('size_x', 400),
                size_y=node_def.get('size_y', 300),
                color=tuple(node_def.get('color', [1, 1, 1])),
                contains_nodes=node_def.get('contains', []),
                **common_kwargs
            )
            self.comment_index += 1
            return node

        elif node_type == 'Generic':
            # Full flexibility - user specifies everything
            node = GenericNode(
                name=name,
                node_index=self.node_index,
                yaml_def=node_def,
                **common_kwargs
            )
            self.node_index += 1
            return node

        # Check registry for node type
        elif node_type in NODE_REGISTRY:
            registry_def = NODE_REGISTRY[node_type]
            node = RegistryNode(
                name=name,
                node_type=node_type,
                node_index=self.node_index,
                registry_def=registry_def,
                yaml_props=node_def,
                **common_kwargs
            )
            self.node_index += 1
            return node

        else:
            raise ValueError(f"Unknown node type: {node_type}. "
                           f"Available: Constant, Time, Custom, MakeFloat2/3/4, "
                           f"NamedRerouteDeclaration, Comment, Generic, "
                           f"or registry types: {list(NODE_REGISTRY.keys())}")

    def _wire_connections(self):
        """Wire all connections from YAML definition."""
        connections = self.data.get('connections', [])

        for conn in connections:
            parts = conn.split('->')
            if len(parts) != 2:
                raise ValueError(f"Invalid connection format: {conn}")

            source_part = parts[0].strip()
            target_part = parts[1].strip()

            if '.' in source_part:
                source_name, source_output = source_part.split('.', 1)
            else:
                source_name = source_part
                source_output = 'Output'

            if '.' in target_part:
                target_name, target_input = target_part.split('.', 1)
            else:
                target_name = target_part
                target_input = 'Input'

            source_node = self.nodes.get(source_name)
            target_node = self.nodes.get(target_name)

            if not source_node:
                raise ValueError(f"Source node not found: {source_name}")
            if not target_node:
                raise ValueError(f"Target node not found: {target_name}")

            self._connect_nodes(source_node, source_output, target_node, target_input)

    def _connect_nodes(self, source: MaterialNode, source_output: str,
                       target: MaterialNode, target_input: str):
        """Create bidirectional connection between nodes."""
        # Find source output pin
        source_pin = None
        for pin in source.pins:
            if pin.direction == "EGPD_Output":
                if pin.pin_name == source_output or source_output in ('Output', 'Result'):
                    source_pin = pin
                    break

        if not source_pin:
            # Try first output (with warning)
            for pin in source.pins:
                if pin.direction == "EGPD_Output":
                    source_pin = pin
                    print(f"Warning: Output '{source_output}' not found on '{source.name}', using first output '{pin.pin_name}'")
                    break

        if not source_pin:
            raise ValueError(f"Output pin '{source_output}' not found on {source.name}")

        # Find target input pin
        target_pin = None
        for pin in target.pins:
            if pin.direction == "EGPD_Input":
                # Handle various pin name formats
                if (pin.pin_name == target_input or
                    pin.pin_name == f"{target_input} (S)" or
                    target_input == 'Input'):
                    target_pin = pin
                    break

        if not target_pin:
            # Try first input (with warning)
            for pin in target.pins:
                if pin.direction == "EGPD_Input":
                    target_pin = pin
                    print(f"Warning: Input '{target_input}' not found on '{target.name}', using first input '{pin.pin_name}'")
                    break

        if not target_pin:
            raise ValueError(f"Input pin '{target_input}' not found on {target.name}")

        # Add bidirectional LinkedTo
        source_pin.linked_to.append((target.node_name, target_pin.pin_id))
        target_pin.linked_to.append((source.node_name, source_pin.pin_id))

        # Add Expression reference in target node
        source_expr_path = source.get_expression_path()

        if isinstance(target, MakeFloatNode):
            target.input_expressions[target_input] = source_expr_path
        elif isinstance(target, NamedRerouteDeclarationNode):
            target.input_expression = source_expr_path
        elif isinstance(target, CustomNode):
            target.input_expressions[target_input] = source_expr_path
        elif isinstance(target, (RegistryNode, GenericNode)):
            target.input_expressions[target_input] = source_expr_path

    def _generate_output(self) -> str:
        """Generate the final clipboard text."""
        output_parts = []
        for node in self.nodes.values():
            output_parts.append(node.to_string())
        return "\n\n".join(output_parts)


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Convert YAML material definitions to UE5 clipboard format'
    )
    parser.add_argument('input', help='Input YAML file')
    parser.add_argument('-o', '--output', help='Output file (default: stdout)')
    parser.add_argument('--list-types', action='store_true',
                       help='List available node types from registry')

    args = parser.parse_args()

    if args.list_types:
        print("Built-in types:")
        print("  Constant, Constant3Vector, Constant4Vector")
        print("  Time, MakeFloat2, MakeFloat3, MakeFloat4")
        print("  Custom, NamedRerouteDeclaration, Comment, Generic")
        print("\nRegistry types:")
        for name in sorted(NODE_REGISTRY.keys()):
            print(f"  {name}")
        return

    with open(args.input, 'r', encoding='utf-8') as f:
        yaml_data = yaml.safe_load(f)

    builder = MaterialGraphBuilder(yaml_data)
    result = builder.build()

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"Output written to {args.output}", file=sys.stderr)
    else:
        print(result)


if __name__ == '__main__':
    main()
