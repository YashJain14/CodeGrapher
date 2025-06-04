import asyncio
import json
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import subprocess
import os
from pathlib import Path
import sys
import threading
import queue
import time
from collections import defaultdict
import re
import math


class NodeType(Enum):
    FILE = "file"
    CLASS = "class"
    METHOD = "method"
    FUNCTION = "function"
    VARIABLE = "variable"
    IMPORT = "import"
    MODULE = "module"
    PACKAGE = "package"
    INTERFACE = "interface"


@dataclass
class CodeNode:
    id: str
    name: str
    type: NodeType
    file_path: str
    line: int
    column: int
    metadata: Dict = field(default_factory=dict)
    parent_id: Optional[str] = None  # Added parent tracking


@dataclass
class CodeEdge:
    source: str
    target: str
    type: str  # "calls", "imports", "defines", "uses", "inherits", "implements", "contains"
    metadata: Dict = field(default_factory=dict)


class LanguageDetector:
    """Detect the primary programming language in a repository"""
    
    LANGUAGE_EXTENSIONS = {
        'python': ['.py'],
        'java': ['.java'],
        'javascript': ['.js', '.jsx'],
        'typescript': ['.ts', '.tsx'],
        'cpp': ['.cpp', '.cc', '.cxx', '.hpp', '.h'],
        'c': ['.c', '.h'],
        'csharp': ['.cs'],
        'go': ['.go'],
        'rust': ['.rs'],
        'ruby': ['.rb'],
        'php': ['.php'],
        'swift': ['.swift'],
        'kotlin': ['.kt', '.kts']
    }
    
    @staticmethod
    def detect_language(root_path: Path) -> str:
        """Detect the primary language based on file count"""
        file_counts = defaultdict(int)
        
        # Count files by extension
        for lang, extensions in LanguageDetector.LANGUAGE_EXTENSIONS.items():
            for ext in extensions:
                count = len(list(root_path.rglob(f"*{ext}")))
                file_counts[lang] += count
        
        if not file_counts:
            return 'python'  # default
            
        # Return language with most files
        primary_lang = max(file_counts.items(), key=lambda x: x[1])[0]
        print(f"Detected primary language: {primary_lang} ({file_counts[primary_lang]} files)")
        
        # Print all detected languages
        for lang, count in sorted(file_counts.items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                print(f"  {lang}: {count} files")
                
        return primary_lang


class JavaParser:
    """Parser for Java source files"""
    
    @staticmethod
    def parse_file(file_path: Path, file_id: str) -> Tuple[Dict[str, CodeNode], List[CodeEdge]]:
        """Parse a Java file and extract nodes and edges"""
        nodes = {}
        edges = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Extract package
            package_match = re.search(r'package\s+([\w.]+)\s*;', content)
            package_name = package_match.group(1) if package_match else 'default'
            
            # Extract imports
            import_pattern = re.compile(r'import\s+(?:static\s+)?([\w.]+(?:\.\*)?)\s*;')
            imported_classes = {}  # Simple name -> full name
            
            for i, line in enumerate(lines):
                import_match = import_pattern.search(line)
                if import_match:
                    import_name = import_match.group(1)
                    import_id = f"{file_id}::import:{i+1}"
                    import_node = CodeNode(
                        id=import_id,
                        name=import_name,
                        type=NodeType.IMPORT,
                        file_path=str(file_path),
                        line=i+1,
                        column=0,
                        parent_id=file_id
                    )
                    nodes[import_id] = import_node
                    edges.append(CodeEdge(file_id, import_id, "contains"))
                    
                    # Track imported class names
                    if not import_name.endswith('*'):
                        simple_name = import_name.split('.')[-1]
                        imported_classes[simple_name] = import_name
            
            # Extract classes and interfaces
            class_pattern = re.compile(
                r'(?:public\s+)?(?:abstract\s+)?(?:final\s+)?(?:class|interface|enum)\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?'
            )
            
            # Pattern for method calls
            method_call_pattern = re.compile(r'(\w+)\.(\w+)\s*\(')
            # Pattern for object creation
            new_pattern = re.compile(r'new\s+(\w+)\s*\(')
            # Pattern for static method calls
            static_call_pattern = re.compile(r'([A-Z]\w+)\.(\w+)\s*\(')
            
            # Track current class for methods
            current_class = None
            current_class_id = None
            current_method = None
            current_method_id = None
            brace_count = 0
            in_class = False
            in_method = False
            method_brace_count = 0
            
            for i, line in enumerate(lines):
                # Count braces to track scope
                brace_count += line.count('{') - line.count('}')
                
                if in_method:
                    method_brace_count += line.count('{') - line.count('}')
                    
                    # Analyze method body for calls
                    if current_method_id:
                        # Check for object creation
                        for match in new_pattern.finditer(line):
                            class_name = match.group(1)
                            edges.append(CodeEdge(
                                current_method_id,
                                f"unresolved::{class_name}",
                                "instantiates",
                                {'call_type': 'constructor'}
                            ))
                        
                        # Check for method calls
                        for match in method_call_pattern.finditer(line):
                            obj_name = match.group(1)
                            method_name = match.group(2)
                            
                            # Skip common keywords
                            if obj_name not in ['if', 'for', 'while', 'switch', 'catch', 'return']:
                                edges.append(CodeEdge(
                                    current_method_id,
                                    f"unresolved::{method_name}",
                                    "calls",
                                    {'call_type': 'method', 'object': obj_name}
                                ))
                        
                        # Check for static method calls
                        for match in static_call_pattern.finditer(line):
                            class_name = match.group(1)
                            method_name = match.group(2)
                            edges.append(CodeEdge(
                                current_method_id,
                                f"unresolved::{method_name}",
                                "calls",
                                {'call_type': 'static', 'class': class_name}
                            ))
                    
                    # Check if we're leaving the method
                    if method_brace_count == 0:
                        in_method = False
                        current_method = None
                        current_method_id = None
                
                # Check for class/interface declaration
                class_match = class_pattern.search(line)
                if class_match:
                    class_name = class_match.group(1)
                    class_type = NodeType.INTERFACE if 'interface' in line else NodeType.CLASS
                    class_id = f"{file_id}::{class_name}:{i+1}"
                    
                    class_node = CodeNode(
                        id=class_id,
                        name=class_name,
                        type=class_type,
                        file_path=str(file_path),
                        line=i+1,
                        column=0,
                        metadata={'package': package_name, 'exportable': True},
                        parent_id=file_id
                    )
                    nodes[class_id] = class_node
                    edges.append(CodeEdge(file_id, class_id, "contains"))
                    
                    current_class = class_name
                    current_class_id = class_id
                    in_class = True
                    
                    # Handle inheritance
                    if class_match.group(2):  # extends
                        parent_class = class_match.group(2)
                        edges.append(CodeEdge(class_id, f"unresolved::{parent_class}", "inherits"))
                    
                    if class_match.group(3):  # implements
                        interfaces = [intf.strip() for intf in class_match.group(3).split(',')]
                        for intf in interfaces:
                            edges.append(CodeEdge(class_id, f"unresolved::{intf}", "implements"))
                
                # Check for method declarations
                if in_class and current_class_id and not in_method:
                    method_pattern = re.compile(
                        r'(?:public\s+|private\s+|protected\s+)?(?:static\s+)?(?:final\s+)?(?:synchronized\s+)?(?:[\w<>\[\]]+\s+)?(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{'
                    )
                    method_match = method_pattern.search(line)
                    if method_match and not any(keyword in line for keyword in ['if', 'for', 'while', 'switch', 'catch']):
                        method_name = method_match.group(1)
                        if method_name not in ['if', 'for', 'while', 'switch', 'new']:
                            method_id = f"{current_class_id}::{method_name}:{i+1}"
                            method_node = CodeNode(
                                id=method_id,
                                name=method_name,
                                type=NodeType.METHOD,
                                file_path=str(file_path),
                                line=i+1,
                                column=0,
                                parent_id=current_class_id
                            )
                            nodes[method_id] = method_node
                            edges.append(CodeEdge(current_class_id, method_id, "contains"))
                            
                            current_method = method_name
                            current_method_id = method_id
                            in_method = True
                            method_brace_count = line.count('{') - line.count('}')
                
                # Reset class tracking when leaving class scope
                if in_class and brace_count == 0:
                    in_class = False
                    current_class = None
                    current_class_id = None
                    
        except Exception as e:
            print(f"Error parsing Java file {file_path}: {e}")
            
        return nodes, edges


class PythonParser:
    """Parser for Python source files using AST"""
    
    @staticmethod
    def parse_file(file_path: Path, file_id: str) -> Tuple[Dict[str, CodeNode], List[CodeEdge]]:
        """Parse a Python file and extract nodes and edges"""
        import ast
        
        nodes = {}
        edges = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content, filename=str(file_path))
            
            # Track imports for resolving calls
            imports = {}  # name -> module mapping
            from_imports = {}  # name -> (module, original_name) mapping
            
            # First pass: collect all definitions and imports
            class_methods = {}  # Track which methods belong to which class
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        import_name = alias.asname if alias.asname else alias.name
                        imports[import_name] = alias.name
                        
                elif isinstance(node, ast.ImportFrom) and node.module:
                    for alias in node.names:
                        import_name = alias.asname if alias.asname else alias.name
                        from_imports[import_name] = (node.module, alias.name)
            
            # Create a visitor to analyze function calls
            class CallVisitor(ast.NodeVisitor):
                def __init__(self, current_scope_id, current_file_id):
                    self.current_scope_id = current_scope_id
                    self.current_file_id = current_file_id
                    self.calls = []
                
                def visit_Call(self, node):
                    call_info = self._extract_call_info(node)
                    if call_info:
                        self.calls.append(call_info)
                    self.generic_visit(node)
                
                def _extract_call_info(self, node):
                    if isinstance(node.func, ast.Name):
                        # Direct function call
                        return ('function', node.func.id, None)
                    elif isinstance(node.func, ast.Attribute):
                        # Method call (e.g., obj.method())
                        if isinstance(node.func.value, ast.Name):
                            return ('method', node.func.attr, node.func.value.id)
                        else:
                            return ('method', node.func.attr, None)
                    return None
            
            # Second pass: create nodes and analyze calls
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_id = f"{file_id}::{node.name}:{node.lineno}"
                    class_node = CodeNode(
                        id=class_id,
                        name=node.name,
                        type=NodeType.CLASS,
                        file_path=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        parent_id=file_id,
                        metadata={'exportable': True}  # Mark as exportable
                    )
                    nodes[class_id] = class_node
                    edges.append(CodeEdge(file_id, class_id, "contains"))
                    
                    # Process methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_id = f"{class_id}::{item.name}:{item.lineno}"
                            method_node = CodeNode(
                                id=method_id,
                                name=item.name,
                                type=NodeType.METHOD,
                                file_path=str(file_path),
                                line=item.lineno,
                                column=item.col_offset,
                                parent_id=class_id
                            )
                            nodes[method_id] = method_node
                            edges.append(CodeEdge(class_id, method_id, "contains"))
                            class_methods[f"{node.name}.{item.name}"] = method_id
                            
                            # Analyze method body for calls
                            visitor = CallVisitor(method_id, file_id)
                            visitor.visit(item)
                            for call_type, call_name, obj_name in visitor.calls:
                                # Store call info for later resolution
                                edges.append(CodeEdge(
                                    method_id, 
                                    f"unresolved::{call_name}", 
                                    "calls",
                                    {'call_type': call_type, 'object': obj_name}
                                ))
                            
                elif isinstance(node, ast.FunctionDef) and not any(
                    isinstance(parent, ast.ClassDef) for parent in ast.walk(tree)
                    if any(child is node for child in ast.walk(parent))
                ):
                    func_id = f"{file_id}::{node.name}:{node.lineno}"
                    func_node = CodeNode(
                        id=func_id,
                        name=node.name,
                        type=NodeType.FUNCTION,
                        file_path=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        parent_id=file_id,
                        metadata={'exportable': True}  # Mark as exportable
                    )
                    nodes[func_id] = func_node
                    edges.append(CodeEdge(file_id, func_id, "contains"))
                    
                    # Analyze function body for calls
                    visitor = CallVisitor(func_id, file_id)
                    visitor.visit(node)
                    for call_type, call_name, obj_name in visitor.calls:
                        edges.append(CodeEdge(
                            func_id, 
                            f"unresolved::{call_name}", 
                            "calls",
                            {'call_type': call_type, 'object': obj_name}
                        ))
                    
                elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                    import_id = f"{file_id}::import:{node.lineno}"
                    module_name = node.module if isinstance(node, ast.ImportFrom) else node.names[0].name
                    import_node = CodeNode(
                        id=import_id,
                        name=module_name or "import",
                        type=NodeType.IMPORT,
                        file_path=str(file_path),
                        line=node.lineno,
                        column=node.col_offset,
                        parent_id=file_id,
                        metadata={'imported_names': [alias.name for alias in node.names] if hasattr(node, 'names') else []}
                    )
                    nodes[import_id] = import_node
                    edges.append(CodeEdge(file_id, import_id, "contains"))
                    
        except Exception as e:
            print(f"Error parsing Python file {file_path}: {e}")
            
        return nodes, edges


class CirclePackingLayout:
    """Calculate circle packing layout positions for nodes"""
    
    def __init__(self, nodes: Dict[str, CodeNode], edges: List[CodeEdge]):
        self.nodes = nodes
        self.edges = edges
        self.positions = {}
        self.radii = {}
        
    def calculate_positions(self) -> Tuple[Dict[str, Tuple[float, float]], Dict[str, float]]:
        """Calculate positions and radii for circle packing layout"""
        # Build parent-child relationships
        children = defaultdict(list)
        roots = []
        
        for node_id, node in self.nodes.items():
            if node.parent_id and node.parent_id in self.nodes:
                children[node.parent_id].append(node_id)
            else:
                roots.append(node_id)
        
        # Calculate positions for each root and its descendants
        current_x = 0
        max_y = 0
        
        for root_id in sorted(roots):
            radius = self._calculate_node_radius(root_id, children)
            self._position_circle(root_id, children, current_x + radius, radius)
            current_x += radius * 2 + 50  # Add spacing between root circles
            max_y = max(max_y, radius * 2)
            
        return self.positions, self.radii
    
    def _calculate_node_radius(self, node_id: str, children: Dict[str, List[str]]) -> float:
        """Calculate the radius needed for a node and its children"""
        node = self.nodes[node_id]
        
        if node_id not in children or not children[node_id]:
            # Leaf node - radius based on type
            if node.type == NodeType.FILE:
                radius = 40
            elif node.type == NodeType.CLASS:
                radius = 25
            elif node.type in [NodeType.METHOD, NodeType.FUNCTION]:
                radius = 15
            else:
                radius = 10
            self.radii[node_id] = radius
            return radius
        
        # Calculate child radii first
        child_radii = []
        for child_id in children[node_id]:
            child_radius = self._calculate_node_radius(child_id, children)
            child_radii.append(child_radius)
        
        # Pack children in a circle and determine required radius
        if len(child_radii) == 1:
            # Single child
            required_radius = child_radii[0] + 30
        else:
            # Multiple children - pack them in a circle
            # Estimate the radius needed to pack all children
            total_child_area = sum(math.pi * r * r for r in child_radii)
            estimated_radius = math.sqrt(total_child_area / math.pi) + max(child_radii) + 20
            
            # Add minimum padding based on node type
            if node.type == NodeType.FILE:
                required_radius = max(estimated_radius, 80)
            elif node.type == NodeType.CLASS:
                required_radius = max(estimated_radius, 50)
            else:
                required_radius = max(estimated_radius, 30)
        
        self.radii[node_id] = required_radius
        return required_radius
    
    def _position_circle(self, node_id: str, children: Dict[str, List[str]], x: float, y: float):
        """Position a node and its children using circle packing"""
        self.positions[node_id] = (x, y)
        
        if node_id not in children or not children[node_id]:
            return
        
        child_list = children[node_id]
        node_radius = self.radii[node_id]
        
        if len(child_list) == 1:
            # Single child - center it
            child_id = child_list[0]
            self._position_circle(child_id, children, x, y)
        else:
            # Multiple children - arrange in a circle
            angle_step = 2 * math.pi / len(child_list)
            
            # Calculate the distance from center for child circles
            max_child_radius = max(self.radii[child_id] for child_id in child_list)
            distance_from_center = node_radius - max_child_radius - 10  # 10px padding
            distance_from_center = max(distance_from_center, max_child_radius + 20)
            
            for i, child_id in enumerate(child_list):
                angle = i * angle_step
                child_x = x + distance_from_center * math.cos(angle)
                child_y = y + distance_from_center * math.sin(angle)
                self._position_circle(child_id, children, child_x, child_y)


class MultiLanguageCodeGraphBuilder:
    """Code graph builder with automatic language detection"""
    
    def __init__(self, root_path: str, language: str = None):
        self.root_path = Path(root_path).absolute()
        
        # Use specified language or auto-detect
        if language:
            if language.lower() in LanguageDetector.LANGUAGE_EXTENSIONS:
                self.language = language.lower()
                print(f"Using specified language: {self.language}")
            else:
                print(f"Warning: Unknown language '{language}'. Auto-detecting...")
                self.language = LanguageDetector.detect_language(self.root_path)
        else:
            self.language = LanguageDetector.detect_language(self.root_path)
            
        self.graph = nx.DiGraph()
        self.nodes: Dict[str, CodeNode] = {}
        self.edges: List[CodeEdge] = []
        
        # Set up parser based on detected language
        self.parser = self._get_parser()
        
    def _get_parser(self):
        """Get the appropriate parser for the detected language"""
        if self.language == 'python':
            return PythonParser()
        elif self.language == 'java':
            return JavaParser()
        else:
            print(f"Warning: No parser available for {self.language}, using basic file analysis")
            return None
            
    def _get_file_extensions(self) -> List[str]:
        """Get file extensions for the detected language"""
        return LanguageDetector.LANGUAGE_EXTENSIONS.get(self.language, [])
        
    def build_graph(self):
        """Build the code graph"""
        # Process all files
        extensions = self._get_file_extensions()
        file_count = 0
        
        for ext in extensions:
            for file_path in self.root_path.rglob(f"*{ext}"):
                # Skip hidden directories and common build directories
                if any(part.startswith('.') for part in file_path.parts):
                    continue
                if any(part in ['target', 'build', 'dist', '__pycache__'] for part in file_path.parts):
                    continue
                    
                self._process_file(file_path)
                file_count += 1
                
        print(f"Processed {file_count} {self.language} files")
        
        # Resolve cross-file references
        self._resolve_cross_file_references()
        
        # Construct the graph
        self._construct_graph()
        
    def _resolve_cross_file_references(self):
        """Resolve function calls and class usage across files"""
        print("Resolving cross-file references...")
        
        # Build lookup tables
        function_lookup = {}  # function_name -> node_id
        class_lookup = {}     # class_name -> node_id
        method_lookup = {}    # class_name.method_name -> node_id
        
        for node_id, node in self.nodes.items():
            if node.type == NodeType.FUNCTION:
                function_lookup[node.name] = node_id
            elif node.type == NodeType.CLASS:
                class_lookup[node.name] = node_id
            elif node.type == NodeType.METHOD and node.parent_id:
                parent = self.nodes.get(node.parent_id)
                if parent and parent.type == NodeType.CLASS:
                    method_lookup[f"{parent.name}.{node.name}"] = node_id
        
        # Resolve unresolved edges
        resolved_edges = []
        unresolved_count = 0
        resolved_count = 0
        
        for edge in self.edges:
            if edge.target.startswith("unresolved::"):
                target_name = edge.target.replace("unresolved::", "")
                call_type = edge.metadata.get('call_type', 'function')
                obj_name = edge.metadata.get('object')
                
                resolved_target = None
                
                if call_type == 'function':
                    # Try to resolve as a function
                    if target_name in function_lookup:
                        resolved_target = function_lookup[target_name]
                    elif target_name in class_lookup:
                        # Might be a class instantiation
                        resolved_target = class_lookup[target_name]
                        edge.type = "instantiates"
                        
                elif call_type == 'method' and obj_name:
                    # Try to resolve as a method call
                    # First check if obj_name is a known class
                    if obj_name in class_lookup:
                        method_key = f"{obj_name}.{target_name}"
                        if method_key in method_lookup:
                            resolved_target = method_lookup[method_key]
                
                if resolved_target:
                    resolved_edges.append(CodeEdge(
                        edge.source,
                        resolved_target,
                        edge.type,
                        edge.metadata
                    ))
                    resolved_count += 1
                else:
                    unresolved_count += 1
            else:
                resolved_edges.append(edge)
        
        self.edges = resolved_edges
        
        if resolved_count > 0:
            print(f"Resolved {resolved_count} cross-file references")
        if unresolved_count > 0:
            print(f"Could not resolve {unresolved_count} references (likely external libraries)")
        
    def _process_file(self, file_path: Path):
        """Process a single file"""
        # Add file node
        file_id = str(file_path.relative_to(self.root_path))
        file_node = CodeNode(
            id=file_id,
            name=file_path.name,
            type=NodeType.FILE,
            file_path=str(file_path),
            line=0,
            column=0
        )
        self.nodes[file_id] = file_node
        
        # Parse file based on language
        if self.parser:
            if isinstance(self.parser, JavaParser):
                nodes, edges = JavaParser.parse_file(file_path, file_id)
            elif isinstance(self.parser, PythonParser):
                nodes, edges = PythonParser.parse_file(file_path, file_id)
            
            self.nodes.update(nodes)
            self.edges.extend(edges)
        
    def _construct_graph(self):
        """Construct the NetworkX graph"""
        # Add nodes
        for node_id, node in self.nodes.items():
            self.graph.add_node(
                node_id,
                label=node.name,
                type=node.type.value,
                file=node.file_path,
                line=node.line,
                parent_id=node.parent_id
            )
            
        # Add edges (skip external references)
        for edge in self.edges:
            # Only add edges where both nodes exist in our graph
            if edge.source in self.nodes and edge.target in self.nodes:
                self.graph.add_edge(
                    edge.source,
                    edge.target,
                    type=edge.type
                )
            elif edge.target.startswith("external::"):
                # Optionally track external dependencies
                # You could store these separately if needed
                pass
                
    def visualize_circle_packing(self, output_file: str = "code_graph.png"):
        """Create a circle packing visualization"""
        if len(self.nodes) == 0:
            print("No nodes to visualize!")
            return
            
        fig, ax = plt.subplots(figsize=(30, 24))
        
        # Color scheme
        color_map = {
            NodeType.FILE.value: '#FF6B6B',
            NodeType.CLASS.value: '#4ECDC4',
            NodeType.INTERFACE.value: '#00CED1',
            NodeType.METHOD.value: '#45B7D1',
            NodeType.FUNCTION.value: '#96CEB4',
            NodeType.VARIABLE.value: '#FECA57',
            NodeType.IMPORT.value: '#DDA0DD',
            NodeType.MODULE.value: '#98D8C8',
            NodeType.PACKAGE.value: '#FFB6C1'
        }
        
        # Calculate circle packing layout
        layout = CirclePackingLayout(self.nodes, self.edges)
        positions, radii = layout.calculate_positions()
        
        # Find bounds for the plot
        if positions:
            x_coords = [pos[0] for pos in positions.values()]
            y_coords = [pos[1] for pos in positions.values()]
            all_radii = [radii[node_id] for node_id in positions.keys()]
            
            min_x = min(x_coords) - max(all_radii) - 50
            max_x = max(x_coords) + max(all_radii) + 50
            min_y = min(y_coords) - max(all_radii) - 50
            max_y = max(y_coords) + max(all_radii) + 50
        else:
            min_x, max_x, min_y, max_y = -100, 100, -100, 100
        
        # Draw circles for each node
        for node_id, node in self.nodes.items():
            if node_id not in positions:
                continue
                
            x, y = positions[node_id]
            radius = radii[node_id]
            
            # Determine circle style based on node type
            if node.type == NodeType.FILE:
                # File containers - thick border, low opacity
                circle = patches.Circle(
                    (x, y), radius,
                    facecolor=color_map[node.type.value],
                    alpha=0.2,
                    edgecolor=color_map[node.type.value],
                    linewidth=3,
                    linestyle='--'
                )
            elif node.type == NodeType.CLASS:
                # Class containers - medium border
                circle = patches.Circle(
                    (x, y), radius,
                    facecolor=color_map[node.type.value],
                    alpha=0.3,
                    edgecolor=color_map[node.type.value],
                    linewidth=2
                )
            else:
                # Methods, functions, imports - solid circles
                circle = patches.Circle(
                    (x, y), radius,
                    facecolor=color_map[node.type.value],
                    alpha=0.8,
                    edgecolor='white',
                    linewidth=1
                )
            
            ax.add_patch(circle)
            
            # Add labels
            if node.type in [NodeType.FILE, NodeType.CLASS]:
                # Larger labels for containers
                fontsize = 12 if node.type == NodeType.FILE else 10
                fontweight = 'bold'
                label_y = y + radius - 15  # Position at top of circle
            else:
                # Smaller labels for leaf nodes
                fontsize = 8
                fontweight = 'normal'
                label_y = y
            
            # Truncate long names
            display_name = node.name[:20] + ('...' if len(node.name) > 20 else '')
            
            ax.text(x, label_y, display_name,
                   ha='center', va='center',
                   fontsize=fontsize,
                   fontweight=fontweight,
                   bbox=dict(boxstyle="round,pad=0.3", 
                           facecolor='white', 
                           alpha=0.8,
                           edgecolor='none'))
        
        # Draw non-containment edges
        for edge in self.edges:
            if edge.type != "contains" and edge.source in positions and edge.target in positions:
                x1, y1 = positions[edge.source]
                x2, y2 = positions[edge.target]
                
                # Calculate edge points on circle boundaries
                r1 = radii[edge.source]
                r2 = radii[edge.target]
                
                # Vector from source to target
                dx = x2 - x1
                dy = y2 - y1
                dist = math.sqrt(dx*dx + dy*dy)
                
                if dist > 0:
                    # Normalize vector
                    dx_norm = dx / dist
                    dy_norm = dy / dist
                    
                    # Calculate edge start and end points
                    start_x = x1 + r1 * dx_norm
                    start_y = y1 + r1 * dy_norm
                    end_x = x2 - r2 * dx_norm
                    end_y = y2 - r2 * dy_norm
                    
                    # Choose edge style based on type
                    if edge.type == "inherits":
                        style = 'dashed'
                        color = 'red'
                        width = 2
                    elif edge.type == "implements":
                        style = 'dotted'
                        color = 'blue'
                        width = 2
                    elif edge.type == "calls":
                        style = 'solid'
                        color = 'green'
                        width = 1.5
                    elif edge.type == "instantiates":
                        style = 'solid'
                        color = 'orange'
                        width = 1.5
                    else:
                        style = 'solid'
                        color = 'gray'
                        width = 1
                    
                    ax.plot([start_x, end_x], [start_y, end_y], 
                           linestyle=style, color=color, linewidth=width, alpha=0.7)
                    
                    # Add arrowhead
                    ax.annotate('', xy=(end_x, end_y), xytext=(start_x, start_y),
                               arrowprops=dict(arrowstyle='->', color=color, alpha=0.7))
        
        # Add legend
        from matplotlib.lines import Line2D
        legend_elements = []
        for node_type, color in color_map.items():
            if any(n.type.value == node_type for n in self.nodes.values()):
                legend_elements.append(
                    Line2D([0], [0], marker='o', color='w', label=node_type,
                          markerfacecolor=color, markersize=10)
                )
        
        # Add edge type legend
        legend_elements.extend([
            Line2D([0], [0], color='red', linestyle='dashed', label='inherits'),
            Line2D([0], [0], color='blue', linestyle='dotted', label='implements'),
            Line2D([0], [0], color='green', linestyle='solid', label='calls'),
            Line2D([0], [0], color='orange', linestyle='solid', label='instantiates'),
            Line2D([0], [0], color='gray', linestyle='solid', label='other relationships')
        ])
        
        ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
        
        ax.set_xlim(min_x, max_x)
        ax.set_ylim(min_y, max_y)
        ax.set_title(f"Code Graph: {self.root_path.name} ({self.language}) - Circle Packing Layout", 
                    fontsize=20, fontweight='bold', pad=20)
        ax.set_aspect('equal')
        ax.axis('off')
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"Circle packing graph saved to {output_file}")
        
    def export_to_json(self, output_file: str = "code_graph.json"):
        """Export graph to JSON format with hierarchical structure"""
        # Build hierarchical structure
        def build_hierarchy(node_id: str) -> Dict:
            node = self.nodes[node_id]
            result = {
                "id": node_id,
                "name": node.name,
                "type": node.type.value,
                "file": node.file_path,
                "line": node.line,
                "column": node.column,
                "metadata": node.metadata,
                "children": []
            }
            
            # Find children
            for other_id, other_node in self.nodes.items():
                if other_node.parent_id == node_id:
                    result["children"].append(build_hierarchy(other_id))
            
            return result
        
        # Find root nodes
        roots = []
        for node_id, node in self.nodes.items():
            if not node.parent_id or node.parent_id not in self.nodes:
                roots.append(build_hierarchy(node_id))
        
        # Filter edges to only include those where both nodes exist
        valid_edges = []
        external_dependencies = []
        
        for edge in self.edges:
            if edge.source in self.nodes and edge.target in self.nodes:
                valid_edges.append({
                    "source": edge.source,
                    "target": edge.target,
                    "type": edge.type,
                    "metadata": edge.metadata
                })
            elif edge.target.startswith("external::"):
                # Track external dependencies separately
                external_dependencies.append({
                    "source": edge.source,
                    "target": edge.target.replace("external::", ""),
                    "type": edge.type
                })
        
        # Also export flat structure for compatibility
        data = {
            "language": self.language,
            "root_path": str(self.root_path),
            "hierarchical": roots,
            "nodes": [
                {
                    "id": node_id,
                    "name": node.name,
                    "type": node.type.value,
                    "file": node.file_path,
                    "line": node.line,
                    "column": node.column,
                    "metadata": node.metadata,
                    "parent_id": node.parent_id
                }
                for node_id, node in self.nodes.items()
            ],
            "edges": valid_edges,
            "external_dependencies": external_dependencies
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
            
        print(f"Graph exported to {output_file}")
        if external_dependencies:
            print(f"Found {len(external_dependencies)} external dependencies")
            
    def get_statistics(self) -> Dict:
        """Get graph statistics"""
        stats = {
            "language": self.language,
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "nodes_by_type": {},
            "edges_by_type": {},
            "avg_degree": 0,
            "connected_components": nx.number_weakly_connected_components(self.graph),
            "max_depth": 0,
            "cross_file_connections": 0
        }
        
        # Count nodes by type
        for node in self.nodes.values():
            node_type = node.type.value
            stats["nodes_by_type"][node_type] = stats["nodes_by_type"].get(node_type, 0) + 1
        
        # Count edges by type
        for edge in self.edges:
            edge_type = edge.type
            stats["edges_by_type"][edge_type] = stats["edges_by_type"].get(edge_type, 0) + 1
            
            # Count cross-file connections
            if edge.type in ['calls', 'instantiates', 'inherits', 'implements']:
                source_node = self.nodes.get(edge.source)
                target_node = self.nodes.get(edge.target)
                if source_node and target_node and source_node.file_path != target_node.file_path:
                    stats["cross_file_connections"] += 1
            
        # Calculate average degree
        if len(self.graph.nodes()) > 0:
            stats["avg_degree"] = sum(dict(self.graph.degree()).values()) / len(self.graph.nodes())
            
        # Calculate max depth
        def get_depth(node_id, depth=0):
            node = self.nodes.get(node_id)
            if not node or not node.parent_id:
                return depth
            return get_depth(node.parent_id, depth + 1)
        
        stats["max_depth"] = max((get_depth(node_id) for node_id in self.nodes.keys()), default=0)
            
        return stats


# Example usage
if __name__ == "__main__":
    import argparse
    
    # Set up command line arguments
    parser = argparse.ArgumentParser(description='Build a code graph visualization for your project')
    parser.add_argument('path', nargs='?', default='.', help='Path to the project directory (default: current directory)')
    parser.add_argument('-l', '--language', help='Force specific language (python, java, javascript, etc.)')
    parser.add_argument('-o', '--output', default='code_graph.png', help='Output image filename (default: code_graph.png)')
    parser.add_argument('-j', '--json', default='code_graph.json', help='Output JSON filename (default: code_graph.json)')
    parser.add_argument('--list-languages', action='store_true', help='List supported languages and exit')
    
    args = parser.parse_args()
    
    # List supported languages if requested
    if args.list_languages:
        print("Supported languages:")
        for lang, exts in sorted(LanguageDetector.LANGUAGE_EXTENSIONS.items()):
            print(f"  {lang}: {', '.join(exts)}")
        sys.exit(0)
    
    # Build graph for the project
    print(f"\nBuilding code graph for: {args.path}")
    print("=" * 60)
    
    builder = MultiLanguageCodeGraphBuilder(args.path, language=args.language)
    
    print("\nAnalyzing code structure...")
    builder.build_graph()
    
    print("\nGenerating circle packing visualization...")
    builder.visualize_circle_packing(args.output)
    
    print(f"\nExporting to {args.json}...")
    builder.export_to_json(args.json)
    
    # Print statistics
    stats = builder.get_statistics()
    print("\nGraph Statistics:")
    print(f"Language: {stats['language']}")
    print(f"Total nodes: {stats['total_nodes']}")
    print(f"Total edges: {stats['total_edges']}")
    print(f"Average degree: {stats['avg_degree']:.2f}")
    print(f"Connected components: {stats['connected_components']}")
    print(f"Max depth: {stats['max_depth']}")
    print("\nNodes by type:")
    for node_type, count in stats['nodes_by_type'].items():
        print(f"  {node_type}: {count}")
    
    print(f"\nDone! Generated:")
    print(f"  - Circle packing visualization: {args.output}")
    print(f"  - JSON data: {args.json}")