export type NodeType = 'file' | 'class' | 'interface' | 'method' | 'function' | 'variable' | 'import' | 'module' | 'package';

export interface GraphNode {
  id: string;
  name: string;
  type: NodeType;
  file: string;
  line: number;
  column: number;
  metadata?: Record<string, unknown>;
  children?: GraphNode[];
  parent_id?: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  metadata?: Record<string, unknown>;
}

export interface GraphData {
  language: string;
  root_path: string;
  hierarchical: GraphNode[];
  nodes: GraphNode[];
  edges: GraphEdge[];
  external_dependencies?: Array<{
    source: string;
    target: string;
    type: string;
  }>;
}

export interface D3Node extends GraphNode {
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
  radius: number;
  level: number;
}

export interface D3Link {
  source: string | D3Node;
  target: string | D3Node;
  type: string;
}

export interface GraphStats {
  totalNodes: number;
  totalEdges: number;
  nodesByType: Record<NodeType, number>;
  edgesByType: Record<string, number>;
  crossFileConnections: number;
}