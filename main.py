import asyncio
import json
import networkx as nx
import matplotlib.pyplot as plt
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


@dataclass
class CodeEdge:
    source: str
    target: str
    type: str  # "calls", "imports", "defines", "uses", "inherits", "implements"
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
                        column=0
                    )
                    nodes[import_id] = import_node
                    edges.append(CodeEdge(file_id, import_id, "imports"))
            
            # Extract classes and interfaces
            class_pattern = re.compile(
                r'(?:public\s+)?(?:abstract\s+)?(?:final\s+)?(?:class|interface|enum)\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?'
            )
            
            # Track current class for methods
            current_class = None
            current_class_id = None
            brace_count = 0
            in_class = False
            
            for i, line in enumerate(lines):
                # Count braces to track scope
                brace_count += line.count('{') - line.count('}')
                
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
                        metadata={'package': package_name}
                    )
                    nodes[class_id] = class_node
                    edges.append(CodeEdge(file_id, class_id, "defines"))
                    
                    current_class = class_name
                    current_class_id = class_id
                    in_class = True
                    
                    # Handle inheritance
                    if class_match.group(2):  # extends
                        parent_class = class_match.group(2)
                        edges.append(CodeEdge(class_id, f"external::{parent_class}", "inherits"))
                    
                    if class_match.group(3):  # implements
                        interfaces = [intf.strip() for intf in class_match.group(3).split(',')]
                        for intf in interfaces:
                            edges.append(CodeEdge(class_id, f"external::{intf}", "implements"))
                
                # Check for method declarations (simplified)
                if in_class and current_class_id:
                    method_pattern = re.compile(
                        r'(?:public\s+|private\s+|protected\s+)?(?:static\s+)?(?:final\s+)?(?:synchronized\s+)?(?:[\w<>\[\]]+\s+)?(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{'
                    )
                    method_match = method_pattern.search(line)
                    if method_match and not any(keyword in line for keyword in ['if', 'for', 'while', 'switch', 'catch']):
                        method_name = method_match.group(1)
                        if method_name not in ['if', 'for', 'while', 'switch', 'new']:  # Filter out keywords
                            method_id = f"{current_class_id}::{method_name}:{i+1}"
                            method_node = CodeNode(
                                id=method_id,
                                name=method_name,
                                type=NodeType.METHOD,
                                file_path=str(file_path),
                                line=i+1,
                                column=0
                            )
                            nodes[method_id] = method_node
                            edges.append(CodeEdge(current_class_id, method_id, "contains"))
                
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
            
            # Visit AST nodes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_id = f"{file_id}::{node.name}:{node.lineno}"
                    class_node = CodeNode(
                        id=class_id,
                        name=node.name,
                        type=NodeType.CLASS,
                        file_path=str(file_path),
                        line=node.lineno,
                        column=node.col_offset
                    )
                    nodes[class_id] = class_node
                    edges.append(CodeEdge(file_id, class_id, "defines"))
                    
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
                                column=item.col_offset
                            )
                            nodes[method_id] = method_node
                            edges.append(CodeEdge(class_id, method_id, "contains"))
                            
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
                        column=node.col_offset
                    )
                    nodes[func_id] = func_node
                    edges.append(CodeEdge(file_id, func_id, "defines"))
                    
                elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                    import_id = f"{file_id}::import:{node.lineno}"
                    module_name = node.module if isinstance(node, ast.ImportFrom) else node.names[0].name
                    import_node = CodeNode(
                        id=import_id,
                        name=module_name or "import",
                        type=NodeType.IMPORT,
                        file_path=str(file_path),
                        line=node.lineno,
                        column=node.col_offset
                    )
                    nodes[import_id] = import_node
                    edges.append(CodeEdge(file_id, import_id, "imports"))
                    
        except Exception as e:
            print(f"Error parsing Python file {file_path}: {e}")
            
        return nodes, edges


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
        
        # Construct the graph
        self._construct_graph()
        
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
                line=node.line
            )
            
        # Add edges (skip external references for now)
        for edge in self.edges:
            if edge.source in self.nodes and edge.target in self.nodes:
                self.graph.add_edge(
                    edge.source,
                    edge.target,
                    type=edge.type
                )
                
    def visualize(self, output_file: str = "code_graph.png", layout: str = "spring"):
        """Visualize the code graph"""
        if len(self.nodes) == 0:
            print("No nodes to visualize!")
            return
            
        plt.figure(figsize=(24, 20))
        
        # Color nodes by type
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
        
        node_colors = [color_map.get(self.graph.nodes[node].get('type', ''), '#CCCCCC') 
                      for node in self.graph.nodes()]
        
        # Choose layout
        if layout == "spring":
            pos = nx.spring_layout(self.graph, k=5, iterations=50, seed=42)
        elif layout == "circular":
            pos = nx.circular_layout(self.graph)
        elif layout == "kamada":
            pos = nx.kamada_kawai_layout(self.graph)
        else:
            # Hierarchical layout
            try:
                import pygraphviz
                pos = nx.nx_agraph.graphviz_layout(self.graph, prog='dot')
            except:
                print("For hierarchical layout, install pygraphviz. Using spring layout instead.")
                pos = nx.spring_layout(self.graph, k=5, iterations=50, seed=42)
                
        # Draw nodes
        nx.draw_networkx_nodes(
            self.graph, pos,
            node_color=node_colors,
            node_size=800,
            alpha=0.8
        )
        
        # Draw edges
        nx.draw_networkx_edges(
            self.graph, pos,
            edge_color='gray',
            arrows=True,
            alpha=0.5,
            arrowsize=15,
            arrowstyle='->'
        )
        
        # Draw labels
        labels = {}
        for node, data in self.graph.nodes(data=True):
            label = data.get('label', node)
            # Truncate long labels
            if len(label) > 20:
                label = label[:17] + '...'
            labels[node] = label
            
        nx.draw_networkx_labels(
            self.graph, pos,
            labels,
            font_size=6,
            font_weight='bold'
        )
        
        # Add legend
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', label=node_type,
                   markerfacecolor=color, markersize=10)
            for node_type, color in color_map.items()
        ]
        plt.legend(handles=legend_elements, loc='upper right', fontsize=10)
        
        plt.title(f"Code Graph: {self.root_path.name} ({self.language})", fontsize=18, fontweight='bold')
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Graph saved to {output_file}")
        
    def export_to_json(self, output_file: str = "code_graph.json"):
        """Export graph to JSON format"""
        data = {
            "language": self.language,
            "root_path": str(self.root_path),
            "nodes": [
                {
                    "id": node_id,
                    "name": node.name,
                    "type": node.type.value,
                    "file": node.file_path,
                    "line": node.line,
                    "column": node.column,
                    "metadata": node.metadata
                }
                for node_id, node in self.nodes.items()
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "type": edge.type,
                    "metadata": edge.metadata
                }
                for edge in self.edges
            ]
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
            
        print(f"Graph exported to {output_file}")
            
    def get_statistics(self) -> Dict:
        """Get graph statistics"""
        stats = {
            "language": self.language,
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "nodes_by_type": {},
            "avg_degree": 0,
            "connected_components": nx.number_weakly_connected_components(self.graph)
        }
        
        # Count nodes by type
        for node in self.nodes.values():
            node_type = node.type.value
            stats["nodes_by_type"][node_type] = stats["nodes_by_type"].get(node_type, 0) + 1
            
        # Calculate average degree
        if len(self.graph.nodes()) > 0:
            stats["avg_degree"] = sum(dict(self.graph.degree()).values()) / len(self.graph.nodes())
            
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
    parser.add_argument('--layout', choices=['spring', 'circular', 'kamada', 'hierarchical'], default='spring', help='Graph layout algorithm')
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
    
    print("\nGenerating visualization...")
    builder.visualize(args.output, layout=args.layout)
    
    print(f"Exporting to {args.json}...")
    builder.export_to_json(args.json)
    
    # Print statistics
    stats = builder.get_statistics()
    print("\nGraph Statistics:")
    print(f"Language: {stats['language']}")
    print(f"Total nodes: {stats['total_nodes']}")
    print(f"Total edges: {stats['total_edges']}")
    print(f"Average degree: {stats['avg_degree']:.2f}")
    print(f"Connected components: {stats['connected_components']}")
    print("\nNodes by type:")
    for node_type, count in stats['nodes_by_type'].items():
        print(f"  {node_type}: {count}")
    
    print(f"\nDone! Check {args.output} and {args.json}")