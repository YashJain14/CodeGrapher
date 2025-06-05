'use client';

import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { GraphData, D3Node, D3Link, NodeType, GraphNode } from '@/types/graph';

interface CodeGraphVisualizationProps {
  data: GraphData | null;
  onNodeSelect: (node: D3Node | null) => void;
  filters: {
    showFiles: boolean;
    showClasses: boolean;
    showMethods: boolean;
    showFunctions: boolean;
    showImports: boolean;
  };
  searchTerm: string;
  showConnections: boolean;
}

const colorMap: Record<NodeType, string> = {
  file: '#FF6B6B',
  class: '#4ECDC4',
  interface: '#00CED1',
  method: '#45B7D1',
  function: '#96CEB4',
  variable: '#FECA57',
  import: '#DDA0DD',
  module: '#98D8C8',
  package: '#FFB6C1'
};

export default function CodeGraphVisualization({ 
  data, 
  onNodeSelect, 
  filters,
  searchTerm,
  showConnections 
}: CodeGraphVisualizationProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [simulation, setSimulation] = useState<d3.Simulation<D3Node, D3Link> | null>(null);
  const [nodes, setNodes] = useState<D3Node[]>([]);
  const [links, setLinks] = useState<D3Link[]>([]);

  useEffect(() => {
    if (!data || !svgRef.current || !containerRef.current) return;

    const container = containerRef.current;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = container.clientWidth;
    const height = container.clientHeight;
    const centerX = width / 2;
    const centerY = height / 2;
    const boundaryRadius = Math.min(width, height) * 0.45;

    svg.attr('width', width).attr('height', height);

    // Process data
    const processedNodes: D3Node[] = [];
    const processedLinks: D3Link[] = [];

    // Helper function to calculate radius
    const calculateNodeRadius = (nodeData: GraphNode): number => {
      switch (nodeData.type) {
        case 'file':
          const childCount = (nodeData.children || []).length;
          return Math.max(45, 30 + childCount * 3);
        case 'class':
        case 'interface':
          const methodCount = (nodeData.children || []).length;
          return Math.max(30, 20 + methodCount * 2.5);
        case 'method':
        case 'function':
          return 12;
        case 'import':
          return 8;
        default:
          return 10;
      }
    };

    // Helper function to process hierarchical data
    const processHierarchy = (nodeData: GraphNode, level = 0) => {
      const node: D3Node = {
        ...nodeData,
        radius: calculateNodeRadius(nodeData),
        level,
        x: centerX + (Math.random() - 0.5) * boundaryRadius,
        y: centerY + (Math.random() - 0.5) * boundaryRadius,
        fx: null,
        fy: null
      };

      processedNodes.push(node);

      if (nodeData.children && nodeData.children.length > 0) {
        nodeData.children.forEach((child: GraphNode) => {
          processHierarchy(child, level + 1);
        });
      }
    };

    // Process hierarchical structure
    data.hierarchical.forEach(root => processHierarchy(root));

    // Process edges
    if (data.edges) {
      const nodeMap = new Map(processedNodes.map(n => [n.id, n]));
      
      data.edges.forEach(edge => {
        if (edge.type !== 'contains' && nodeMap.has(edge.source) && nodeMap.has(edge.target)) {
          processedLinks.push({
            source: edge.source,
            target: edge.target,
            type: edge.type
          });
        }
      });
    }

    setNodes(processedNodes);
    setLinks(processedLinks);

    // Create zoom behavior
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 10])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });

    svg.call(zoom);

    // Main group
    const g = svg.append('g');

    // Add gradient definitions
    const defs = svg.append('defs');
    
    // Create arrow markers
    ['calls', 'inherits', 'implements', 'instantiates'].forEach(type => {
      const color = type === 'calls' ? '#45b7d1' : 
                   type === 'inherits' ? '#ff6b6b' :
                   type === 'implements' ? '#4ecdc4' : '#ffa500';
      
      defs.append('marker')
        .attr('id', `arrowhead-${type}`)
        .attr('viewBox', '-0 -5 10 10')
        .attr('refX', 8)
        .attr('refY', 0)
        .attr('orient', 'auto')
        .attr('markerWidth', 8)
        .attr('markerHeight', 8)
        .append('path')
        .attr('d', 'M 0,-5 L 10,0 L 0,5')
        .attr('fill', color)
        .attr('opacity', 0.7);
    });

    // Create boundary circle
    g.append('circle')
      .attr('cx', centerX)
      .attr('cy', centerY)
      .attr('r', boundaryRadius)
      .attr('fill', 'none')
      .attr('stroke', 'rgba(255,255,255,0.1)')
      .attr('stroke-width', 2)
      .attr('stroke-dasharray', '10,10');

    // Create simulation
    const sim = d3.forceSimulation<D3Node>(processedNodes)
      .force('link', d3.forceLink<D3Node, D3Link>(processedLinks)
        .id(d => d.id)
        .strength(0.05)
        .distance(d => {
          const sourceRadius = (d.source as D3Node).radius || 15;
          const targetRadius = (d.target as D3Node).radius || 15;
          return sourceRadius + targetRadius + 100;
        }))
      .force('charge', d3.forceManyBody().strength(-400))
      .force('center', d3.forceCenter(centerX, centerY).strength(0.01))
      .force('collision', d3.forceCollide<D3Node>()
        .radius(d => d.radius + 30)
        .strength(0.9))
      .force('boundary', () => {
        processedNodes.forEach(node => {
          const dx = node.x! - centerX;
          const dy = node.y! - centerY;
          const distance = Math.sqrt(dx * dx + dy * dy);
          
          if (distance > boundaryRadius - node.radius - 20) {
            const factor = (boundaryRadius - node.radius - 20) / distance;
            node.x = centerX + dx * factor;
            node.y = centerY + dy * factor;
          }
        });
      })
      .alphaDecay(0.05)
      .alphaMin(0.001);

    setSimulation(sim);

    // Create connection lines
    const linkElements = g.selectAll('.link')
      .data(processedLinks)
      .enter()
      .append('line')
      .attr('class', d => `link link-${d.type}`)
      .attr('stroke', d => {
        const colors: Record<string, string> = {
          calls: '#45b7d1',
          inherits: '#ff6b6b',
          implements: '#4ecdc4',
          instantiates: '#ffa500'
        };
        return colors[d.type] || '#999';
      })
      .attr('stroke-width', 2)
      .attr('stroke-opacity', 0.6)
      .attr('marker-end', d => `url(#arrowhead-${d.type})`)
      .style('display', showConnections ? 'block' : 'none');

    // Create circles
    const circleElements = g.selectAll('.node-circle')
      .data(processedNodes)
      .enter()
      .append('circle')
      .attr('class', d => `node-circle node-${d.type}`)
      .attr('r', d => d.radius)
      .attr('fill', d => colorMap[d.type] || '#999')
      .attr('stroke', d => colorMap[d.type] || '#999')
      .attr('stroke-width', d => d.type === 'file' || d.type === 'class' ? 3 : 2)
      .attr('fill-opacity', d => {
        if (d.type === 'file') return 0.1;
        if (d.type === 'class') return 0.3;
        return 0.8;
      })
      .style('cursor', 'pointer')
      .on('click', (_event, d) => {
        onNodeSelect(d);
        highlightNode(d, circleElements as any, linkElements as any, labelElements as any);
      })
      .on('mouseover', function() {
        d3.select(this).style('filter', 'brightness(1.2) drop-shadow(0 0 10px rgba(255,255,255,0.3))');
      })
      .on('mouseout', function() {
        d3.select(this).style('filter', '');
      });

    // Create labels
    const labelElements = g.selectAll('.node-label')
      .data(processedNodes)
      .enter()
      .append('text')
      .attr('class', 'node-label')
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'middle')
      .attr('font-size', d => d.type === 'file' || d.type === 'class' ? '12px' : '10px')
      .attr('font-weight', d => d.type === 'file' || d.type === 'class' ? 'bold' : 'normal')
      .attr('fill', 'white')
      .attr('text-shadow', '0 0 3px rgba(0,0,0,0.8)')
      .style('pointer-events', 'none')
      .text(d => {
        const maxLength = d.type === 'file' ? 25 : d.type === 'class' ? 20 : 15;
        return d.name.length > maxLength ? d.name.substring(0, maxLength - 3) + '...' : d.name;
      });

    // Update positions on tick
    sim.on('tick', () => {
      linkElements
        .attr('x1', d => (d.source as D3Node).x!)
        .attr('y1', d => (d.source as D3Node).y!)
        .attr('x2', d => (d.target as D3Node).x!)
        .attr('y2', d => (d.target as D3Node).y!);

      circleElements
        .attr('cx', d => d.x!)
        .attr('cy', d => d.y!);

      labelElements
        .attr('x', d => d.x!)
        .attr('y', d => d.y!);
    });

    // Auto-stop simulation after settling
    setTimeout(() => {
      sim.alpha(0.001);
      processedNodes.forEach(node => {
        node.fx = node.x;
        node.fy = node.y;
      });
    }, 3000);

    // Apply filters and search
    applyFiltersAndSearch(circleElements, labelElements, filters, searchTerm);

    // Update connections visibility
    linkElements.style('display', showConnections ? 'block' : 'none');

    // Cleanup
    return () => {
      sim.stop();
    };
  }, [data, showConnections]);

  // Apply filters and search when they change
  useEffect(() => {
    if (!svgRef.current) return;
    
    const svg = d3.select(svgRef.current);
    const circleElements = svg.selectAll('.node-circle') as d3.Selection<any, D3Node, any, any>;
    const labelElements = svg.selectAll('.node-label') as d3.Selection<any, D3Node, any, any>;
    const linkElements = svg.selectAll('.link');
    
    applyFiltersAndSearch(circleElements, labelElements, filters, searchTerm);
    linkElements.style('display', showConnections ? 'block' : 'none');
  }, [filters, searchTerm, showConnections]);

  const highlightNode = (targetNode: D3Node, circleElements: d3.Selection<any, D3Node, any, any>, linkElements: d3.Selection<any, D3Link, any, any>, labelElements: d3.Selection<any, D3Node, any, any>) => {
    // Reset all styles
    circleElements.classed('highlighted', false).classed('dimmed', false);
    linkElements.classed('highlighted', false).classed('dimmed', false);
    labelElements.classed('dimmed', false);

    // Find connected nodes
    const connectedNodeIds = new Set([targetNode.id]);
    
    links.forEach(link => {
      const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
      const targetId = typeof link.target === 'string' ? link.target : link.target.id;
      
      if (sourceId === targetNode.id || targetId === targetNode.id) {
        connectedNodeIds.add(sourceId);
        connectedNodeIds.add(targetId);
      }
    });

    // Highlight relevant elements
    circleElements
      .classed('highlighted', (d: D3Node) => d.id === targetNode.id)
      .classed('dimmed', (d: D3Node) => !connectedNodeIds.has(d.id));

    linkElements
      .classed('highlighted', (d: D3Link) => {
        const sourceId = typeof d.source === 'string' ? d.source : d.source.id;
        const targetId = typeof d.target === 'string' ? d.target : d.target.id;
        return sourceId === targetNode.id || targetId === targetNode.id;
      })
      .classed('dimmed', (d: D3Link) => {
        const sourceId = typeof d.source === 'string' ? d.source : d.source.id;
        const targetId = typeof d.target === 'string' ? d.target : d.target.id;
        return sourceId !== targetNode.id && targetId !== targetNode.id;
      });

    labelElements.classed('dimmed', (d: D3Node) => !connectedNodeIds.has(d.id));
  };

  const applyFiltersAndSearch = (circleElements: d3.Selection<any, D3Node, any, any>, labelElements: d3.Selection<any, D3Node, any, any>, filters: typeof filters, searchTerm: string) => {
    circleElements.style('display', (d: D3Node) => {
      // Apply type filters
      const typeVisible = filters[`show${d.type.charAt(0).toUpperCase() + d.type.slice(1)}s` as keyof typeof filters];
      if (!typeVisible) return 'none';
      
      // Apply search filter
      if (searchTerm && !d.name.toLowerCase().includes(searchTerm.toLowerCase())) {
        return 'none';
      }
      
      return 'block';
    });

    labelElements.style('display', (d: D3Node) => {
      const typeVisible = filters[`show${d.type.charAt(0).toUpperCase() + d.type.slice(1)}s` as keyof typeof filters];
      if (!typeVisible) return 'none';
      
      if (searchTerm && !d.name.toLowerCase().includes(searchTerm.toLowerCase())) {
        return 'none';
      }
      
      return 'block';
    });
  };

  const resetZoom = () => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.transition().duration(500).call(
      d3.zoom<SVGSVGElement, unknown>().transform,
      d3.zoomIdentity
    );
  };

  const resetPositions = () => {
    if (!simulation || !containerRef.current) return;
    
    const width = containerRef.current.clientWidth;
    const height = containerRef.current.clientHeight;
    const centerX = width / 2;
    const centerY = height / 2;
    const boundaryRadius = Math.min(width, height) * 0.45;

    nodes.forEach((node, index) => {
      const goldenAngle = Math.PI * (3 - Math.sqrt(5));
      const theta = index * goldenAngle;
      const maxRadius = boundaryRadius * 0.9;
      const spiralRadius = Math.sqrt(index / nodes.length) * maxRadius;
      
      node.x = centerX + Math.cos(theta) * spiralRadius;
      node.y = centerY + Math.sin(theta) * spiralRadius;
      node.fx = null;
      node.fy = null;
    });

    simulation.alpha(0.3).restart();
  };

  return (
    <div ref={containerRef} className="w-full h-full relative bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900">
      <svg ref={svgRef} className="w-full h-full">
        <style>{`
          .highlighted {
            stroke: #fff !important;
            stroke-width: 4 !important;
            filter: brightness(1.4) drop-shadow(0 0 15px rgba(255,255,255,0.6)) !important;
          }
          .dimmed {
            opacity: 0.25 !important;
            filter: grayscale(0.3) !important;
          }
          .link {
            transition: all 0.3s ease;
          }
          .link:hover {
            stroke-opacity: 0.9 !important;
            stroke-width: 3 !important;
          }
        `}</style>
      </svg>
      
      {/* Zoom controls */}
      <div className="absolute bottom-4 right-4 flex flex-col space-y-2">
        <button
          onClick={() => {
            if (!svgRef.current) return;
            const svg = d3.select(svgRef.current);
            svg.transition().call(d3.zoom<SVGSVGElement, unknown>().scaleBy, 1.3);
          }}
          className="bg-black bg-opacity-50 hover:bg-opacity-70 text-white p-2 rounded-lg backdrop-blur-sm transition-all"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
        </button>
        
        <button
          onClick={() => {
            if (!svgRef.current) return;
            const svg = d3.select(svgRef.current);
            svg.transition().call(d3.zoom<SVGSVGElement, unknown>().scaleBy, 0.7);
          }}
          className="bg-black bg-opacity-50 hover:bg-opacity-70 text-white p-2 rounded-lg backdrop-blur-sm transition-all"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
          </svg>
        </button>
        
        <button
          onClick={resetZoom}
          className="bg-black bg-opacity-50 hover:bg-opacity-70 text-white p-2 rounded-lg backdrop-blur-sm transition-all"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
          </svg>
        </button>
        
        <button
          onClick={resetPositions}
          className="bg-black bg-opacity-50 hover:bg-opacity-70 text-white p-2 rounded-lg backdrop-blur-sm transition-all"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>
    </div>
  );
}