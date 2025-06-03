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


class HierarchicalLayout:
    """Calculate hierarchical layout positions for nodes"""
    
    def __init__(self, nodes: Dict[str, CodeNode], edges: List[CodeEdge]):
        self.nodes = nodes
        self.edges = edges
        self.positions = {}
        self.node_sizes = {}
        
    def calculate_positions(self) -> Dict[str, Tuple[float, float]]:
        """Calculate positions for all nodes in a hierarchical layout"""
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
            subtree_width, subtree_height = self._calculate_subtree_size(root_id, children)
            self._position_subtree(root_id, children, current_x + subtree_width / 2, 0)
            current_x += subtree_width + 100
            max_y = max(max_y, subtree_height)
            
        return self.positions
    
    def _calculate_subtree_size(self, node_id: str, children: Dict[str, List[str]]) -> Tuple[float, float]:
        """Calculate the size needed for a subtree"""
        node = self.nodes[node_id]
        
        if node_id not in children or not children[node_id]:
            # Leaf node
            self.node_sizes[node_id] = (150, 100)
            return (150, 100)
        
        # Calculate size based on children
        child_sizes = []
        total_width = 0
        max_height = 0
        
        for child_id in children[node_id]:
            child_width, child_height = self._calculate_subtree_size(child_id, children)
            child_sizes.append((child_width, child_height))
            total_width += child_width
            max_height = max(max_height, child_height)
        
        # Add spacing between children
        total_width += 50 * (len(children[node_id]) - 1)
        
        # Node's own size depends on its type and children
        if node.type == NodeType.FILE:
            node_width = max(total_width + 100, 300)
            node_height = max_height + 200
        elif node.type == NodeType.CLASS:
            node_width = max(total_width + 80, 250)
            node_height = max_height + 150
        else:
            node_width = max(total_width, 150)
            node_height = max_height + 100
            
        self.node_sizes[node_id] = (node_width, node_height)
        return (node_width, node_height)
    
    def _position_subtree(self, node_id: str, children: Dict[str, List[str]], x: float, y: float):
        """Position a node and all its children"""
        self.positions[node_id] = (x, y)
        
        if node_id not in children or not children[node_id]:
            return
        
        # Position children
        node_width, node_height = self.node_sizes[node_id]
        child_y = y + 150  # Vertical spacing
        
        # Calculate starting x position for children
        total_children_width = sum(self.node_sizes[child_id][0] for child_id in children[node_id])
        total_children_width += 50 * (len(children[node_id]) - 1)  # spacing
        
        current_x = x - total_children_width / 2
        
        for child_id in children[node_id]:
            child_width, _ = self.node_sizes[child_id]
            child_x = current_x + child_width / 2
            self._position_subtree(child_id, children, child_x, child_y)
            current_x += child_width + 50


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
                
    def visualize_hierarchical(self, output_file: str = "code_graph.png"):
        """Create a hierarchical visualization with nested containers"""
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
        
        # Calculate hierarchical layout
        layout = HierarchicalLayout(self.nodes, self.edges)
        positions = layout.calculate_positions()
        
        # Find bounds
        if positions:
            x_coords = [pos[0] for pos in positions.values()]
            y_coords = [pos[1] for pos in positions.values()]
            min_x, max_x = min(x_coords) - 200, max(x_coords) + 200
            min_y, max_y = min(y_coords) - 200, max(y_coords) + 200
        else:
            min_x, max_x, min_y, max_y = -100, 100, -100, 100
        
        # Draw containers for files and classes
        containers_drawn = set()
        
        # Group nodes by parent
        children_by_parent = defaultdict(list)
        for node_id, node in self.nodes.items():
            if node.parent_id:
                children_by_parent[node.parent_id].append(node_id)
        
        # Draw containers (files and classes)
        for node_id, node in self.nodes.items():
            if node.type in [NodeType.FILE, NodeType.CLASS] and node_id in children_by_parent:
                if node_id not in positions:
                    continue
                    
                x, y = positions[node_id]
                children = children_by_parent[node_id]
                
                if children:
                    # Calculate bounding box for container
                    child_positions = [positions[child_id] for child_id in children if child_id in positions]
                    if child_positions:
                        child_xs = [pos[0] for pos in child_positions]
                        child_ys = [pos[1] for pos in child_positions]
                        
                        padding = 80 if node.type == NodeType.FILE else 60
                        rect_x = min(child_xs) - padding
                        rect_y = min(child_ys) - padding
                        rect_width = max(child_xs) - min(child_xs) + 2 * padding
                        rect_height = max(child_ys) - min(child_ys) + 2 * padding
                        
                        # Draw rounded rectangle container
                        if node.type == NodeType.FILE:
                            rect = patches.FancyBboxPatch(
                                (rect_x, rect_y), rect_width, rect_height,
                                boxstyle="round,pad=10",
                                facecolor=color_map[node.type.value] + '20',  # Transparent
                                edgecolor=color_map[node.type.value],
                                linewidth=2,
                                linestyle='--'
                            )
                        else:  # CLASS
                            rect = patches.FancyBboxPatch(
                                (rect_x, rect_y), rect_width, rect_height,
                                boxstyle="round,pad=5",
                                facecolor=color_map[node.type.value] + '30',  # Slightly more opaque
                                edgecolor=color_map[node.type.value],
                                linewidth=1.5
                            )
                        ax.add_patch(rect)
                        
                        # Add container label
                        label_y = rect_y + rect_height - 20
                        ax.text(x, label_y, node.name, 
                               ha='center', va='top',
                               fontsize=12 if node.type == NodeType.FILE else 10,
                               fontweight='bold',
                               bbox=dict(boxstyle="round,pad=0.3", 
                                       facecolor=color_map[node.type.value], 
                                       alpha=0.8))
        
        # Draw edges (non-containment relationships)
        for edge in self.edges:
            if edge.type != "contains" and edge.source in positions and edge.target in positions:
                x1, y1 = positions[edge.source]
                x2, y2 = positions[edge.target]
                
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
                
                ax.plot([x1, x2], [y1, y2], 
                       linestyle=style, color=color, linewidth=width, alpha=0.6)
                
                # Add arrowhead
                ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                           arrowprops=dict(arrowstyle='->', color=color, alpha=0.6))
        
        # Draw nodes
        for node_id, node in self.nodes.items():
            if node_id not in positions:
                continue
                
            x, y = positions[node_id]
            
            # Skip container nodes as we've already drawn them
            if node.type in [NodeType.FILE, NodeType.CLASS] and node_id in children_by_parent:
                continue
            
            # Draw node
            if node.type == NodeType.METHOD:
                marker = 'o'
                size = 300
            elif node.type == NodeType.FUNCTION:
                marker = 's'
                size = 300
            elif node.type == NodeType.IMPORT:
                marker = '^'
                size = 250
            else:
                marker = 'o'
                size = 200
                
            ax.scatter(x, y, s=size, c=color_map.get(node.type.value, '#CCCCCC'),
                      marker=marker, alpha=0.8, edgecolors='black', linewidth=1)
            
            # Add label
            ax.text(x, y-30, node.name[:20] + ('...' if len(node.name) > 20 else ''),
                   ha='center', va='top', fontsize=8)
        
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
        ax.set_title(f"Code Graph: {self.root_path.name} ({self.language})", 
                    fontsize=20, fontweight='bold', pad=20)
        ax.axis('off')
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"Hierarchical graph saved to {output_file}")
        
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
        
    def export_html_viewer(self, html_file: str = "code_graph.html", json_file: str = "code_graph.json"):
        """Export an interactive HTML viewer"""
        html_content = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Interactive Code Graph Viewer</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #f0f0f0;
        }
        
        #container {
            width: 100vw;
            height: 100vh;
            position: relative;
            overflow: hidden;
        }
        
        #controls {
            position: absolute;
            top: 10px;
            left: 10px;
            background: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            z-index: 1000;
        }
        
        #info {
            position: absolute;
            top: 10px;
            right: 10px;
            background: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            max-width: 300px;
            z-index: 1000;
        }
        
        .node {
            cursor: pointer;
        }
        
        .node-label {
            font-size: 12px;
            pointer-events: none;
        }
        
        .link {
            fill: none;
            stroke-opacity: 0.6;
        }
        
        .link-contains {
            stroke: #999;
            stroke-width: 1;
        }
        
        .link-inherits {
            stroke: red;
            stroke-width: 2;
            stroke-dasharray: 5,5;
        }
        
        .link-implements {
            stroke: blue;
            stroke-width: 2;
            stroke-dasharray: 2,2;
        }
        
        .link-calls {
            stroke: green;
            stroke-width: 1.5;
        }
        
        .container {
            fill-opacity: 0.1;
            stroke-width: 2;
            stroke-dasharray: 5,5;
        }
        
        .container-file {
            fill: #FF6B6B;
            stroke: #FF6B6B;
        }
        
        .container-class {
            fill: #4ECDC4;
            stroke: #4ECDC4;
            stroke-dasharray: none;
        }
        
        button {
            margin: 2px;
            padding: 5px 10px;
            border: none;
            border-radius: 3px;
            background: #007bff;
            color: white;
            cursor: pointer;
        }
        
        button:hover {
            background: #0056b3;
        }
        
        #search {
            width: 200px;
            padding: 5px;
            margin-bottom: 10px;
            border: 1px solid #ddd;
            border-radius: 3px;
        }
    </style>
</head>
<body>
    <div id="container">
        <svg id="graph"></svg>
        <div id="controls">
            <input type="text" id="search" placeholder="Search nodes...">
            <div>
                <button onclick="zoomIn()">Zoom In</button>
                <button onclick="zoomOut()">Zoom Out</button>
                <button onclick="resetZoom()">Reset</button>
            </div>
            <div>
                <label><input type="checkbox" id="showFiles" checked> Files</label>
                <label><input type="checkbox" id="showClasses" checked> Classes</label>
                <label><input type="checkbox" id="showMethods" checked> Methods</label>
                <label><input type="checkbox" id="showImports" checked> Imports</label>
            </div>
        </div>
        <div id="info">
            <h3>Node Info</h3>
            <div id="nodeInfo">Click on a node to see details</div>
        </div>
    </div>
    
    <script>
        // Load and process data
        let graphData = null;
        let simulation = null;
        let svg = null;
        let g = null;
        let zoom = null;
        
        // Color mapping
        const colorMap = {
            'file': '#FF6B6B',
            'class': '#4ECDC4',
            'interface': '#00CED1',
            'method': '#45B7D1',
            'function': '#96CEB4',
            'variable': '#FECA57',
            'import': '#DDA0DD',
            'module': '#98D8C8',
            'package': '#FFB6C1'
        };
        
        // Load JSON data
        fetch('CODE_GRAPH_JSON_FILE')
            .then(response => response.json())
            .then(data => {
                graphData = data;
                initializeGraph();
            })
            .catch(error => console.error('Error loading graph data:', error));
        
        function initializeGraph() {
            const width = window.innerWidth;
            const height = window.innerHeight;
            
            // Create SVG
            svg = d3.select('#graph')
                .attr('width', width)
                .attr('height', height);
            
            // Create zoom behavior
            zoom = d3.zoom()
                .scaleExtent([0.1, 10])
                .on('zoom', (event) => {
                    g.attr('transform', event.transform);
                });
            
            svg.call(zoom);
            
            g = svg.append('g');
            
            // Process hierarchical data into force-directed layout
            const nodes = [];
            const links = [];
            const nodeMap = new Map();
            
            // Flatten hierarchical structure
            function processNode(node, parent = null) {
                const d3Node = {
                    id: node.id,
                    name: node.name,
                    type: node.type,
                    file: node.file,
                    line: node.line,
                    parent: parent,
                    children: []
                };
                
                nodes.push(d3Node);
                nodeMap.set(node.id, d3Node);
                
                if (parent) {
                    links.push({
                        source: parent.id,
                        target: node.id,
                        type: 'contains'
                    });
                }
                
                if (node.children) {
                    node.children.forEach(child => processNode(child, d3Node));
                }
            }
            
            graphData.hierarchical.forEach(root => processNode(root));
            
            // Add non-containment edges
            graphData.edges.forEach(edge => {
                if (edge.type !== 'contains') {
                    links.push(edge);
                }
            });
            
            // Create force simulation
            simulation = d3.forceSimulation(nodes)
                .force('link', d3.forceLink(links).id(d => d.id).distance(100))
                .force('charge', d3.forceManyBody().strength(-300))
                .force('center', d3.forceCenter(width / 2, height / 2))
                .force('collision', d3.forceCollide().radius(50));
            
            // Create containers for files and classes
            const containers = g.selectAll('.container')
                .data(nodes.filter(d => d.type === 'file' || d.type === 'class'))
                .enter()
                .append('rect')
                .attr('class', d => `container container-${d.type}`)
                .attr('rx', 10)
                .attr('ry', 10);
            
            // Create links
            const link = g.selectAll('.link')
                .data(links)
                .enter()
                .append('line')
                .attr('class', d => `link link-${d.type}`);
            
            // Create nodes
            const node = g.selectAll('.node')
                .data(nodes)
                .enter()
                .append('g')
                .attr('class', 'node')
                .call(d3.drag()
                    .on('start', dragstarted)
                    .on('drag', dragged)
                    .on('end', dragended));
            
            // Add circles for nodes
            node.append('circle')
                .attr('r', d => {
                    if (d.type === 'file') return 20;
                    if (d.type === 'class') return 15;
                    if (d.type === 'method' || d.type === 'function') return 10;
                    return 8;
                })
                .attr('fill', d => colorMap[d.type] || '#999')
                .on('click', showNodeInfo);
            
            // Add labels
            node.append('text')
                .attr('class', 'node-label')
                .attr('dx', 12)
                .attr('dy', 4)
                .text(d => d.name.length > 20 ? d.name.substring(0, 17) + '...' : d.name);
            
            // Update positions on tick
            simulation.on('tick', () => {
                // Update containers
                containers.each(function(d) {
                    const children = nodes.filter(n => n.parent && n.parent.id === d.id);
                    if (children.length > 0) {
                        const minX = Math.min(...children.map(c => c.x)) - 30;
                        const minY = Math.min(...children.map(c => c.y)) - 30;
                        const maxX = Math.max(...children.map(c => c.x)) + 30;
                        const maxY = Math.max(...children.map(c => c.y)) + 30;
                        
                        d3.select(this)
                            .attr('x', minX)
                            .attr('y', minY)
                            .attr('width', maxX - minX)
                            .attr('height', maxY - minY);
                    }
                });
                
                // Update links
                link
                    .attr('x1', d => nodeMap.get(d.source.id || d.source).x)
                    .attr('y1', d => nodeMap.get(d.source.id || d.source).y)
                    .attr('x2', d => nodeMap.get(d.target.id || d.target).x)
                    .attr('y2', d => nodeMap.get(d.target.id || d.target).y);
                
                // Update nodes
                node.attr('transform', d => `translate(${d.x},${d.y})`);
            });
        }
        
        // Drag functions
        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }
        
        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }
        
        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }
        
        // Control functions
        function zoomIn() {
            svg.transition().call(zoom.scaleBy, 1.3);
        }
        
        function zoomOut() {
            svg.transition().call(zoom.scaleBy, 0.7);
        }
        
        function resetZoom() {
            svg.transition().call(zoom.transform, d3.zoomIdentity);
        }
        
        function showNodeInfo(event, d) {
            const info = `
                <strong>Name:</strong> ${d.name}<br>
                <strong>Type:</strong> ${d.type}<br>
                <strong>File:</strong> ${d.file}<br>
                <strong>Line:</strong> ${d.line}
            `;
            document.getElementById('nodeInfo').innerHTML = info;
        }
        
        // Search functionality
        document.getElementById('search').addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            
            d3.selectAll('.node').style('opacity', d => {
                if (searchTerm === '') return 1;
                return d.name.toLowerCase().includes(searchTerm) ? 1 : 0.2;
            });
        });
        
        // Filter by type
        ['Files', 'Classes', 'Methods', 'Imports'].forEach(type => {
            document.getElementById(`show${type}`).addEventListener('change', function(e) {
                const typeKey = type.toLowerCase().slice(0, -1); // Remove 's'
                d3.selectAll('.node').style('display', d => {
                    if (!e.target.checked && d.type === typeKey) return 'none';
                    return 'block';
                });
            });
        });
    </script>
</body>
</html>'''
        
        # Replace placeholder with actual JSON file path
        html_content = html_content.replace('CODE_GRAPH_JSON_FILE', json_file)
        
        with open(html_file, 'w') as f:
            f.write(html_content)
            
        print(f"Interactive HTML viewer saved to {html_file}")
            
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
    parser.add_argument('-w', '--web', default='code_graph.html', help='Output HTML filename (default: code_graph.html)')
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
    
    print("\nGenerating hierarchical visualization...")
    builder.visualize_hierarchical(args.output)
    
    print(f"\nExporting to {args.json}...")
    builder.export_to_json(args.json)
    
    print(f"\nGenerating interactive HTML viewer...")
    builder.export_html_viewer(args.web, args.json)
    
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
    print(f"  - Hierarchical visualization: {args.output}")
    print(f"  - JSON data: {args.json}")
    print(f"  - Interactive HTML viewer: {args.web}")
    print("\nOpen the HTML file in a web browser for an interactive experience!")