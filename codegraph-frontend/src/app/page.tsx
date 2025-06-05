'use client';

import { useState } from 'react';
import { GraphData, D3Node } from '@/types/graph';
import FileUpload from '@/components/FileUpload';
import CodeGraphVisualization from '@/components/CodeGraphVisualization';
import ControlsPanel from '@/components/ControlsPanel';
import NodeInfoPanel from '@/components/NodeInfoPanel';
import StatsPanel from '@/components/StatsPanel';

export default function Home() {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [selectedNode, setSelectedNode] = useState<D3Node | null>(null);
  const [filters, setFilters] = useState({
    showFiles: true,
    showClasses: true,
    showMethods: true,
    showFunctions: true,
    showImports: true
  });
  const [searchTerm, setSearchTerm] = useState('');
  const [showConnections, setShowConnections] = useState(true);

  const handleFileLoad = (data: GraphData) => {
    setGraphData(data);
    setSelectedNode(null);
  };

  const handleNodeSelect = (node: D3Node | null) => {
    setSelectedNode(node);
  };

  const calculateConnections = (node: D3Node) => {
    if (!graphData) return { incoming: {}, outgoing: {} };

    const incoming: Record<string, number> = {};
    const outgoing: Record<string, number> = {};

    graphData.edges.forEach(edge => {
      if (edge.target === node.id) {
        incoming[edge.type] = (incoming[edge.type] || 0) + 1;
      }
      if (edge.source === node.id) {
        outgoing[edge.type] = (outgoing[edge.type] || 0) + 1;
      }
    });

    return { incoming, outgoing };
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900">
      {/* Header */}
      <header className="relative z-10 p-6 border-b border-white border-opacity-10 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white mb-2">
                CodeGrapher
              </h1>
              <p className="text-gray-300">
                Interactive code structure visualization with physics-based layout
              </p>
            </div>
            <div className="flex items-center space-x-4">
              {graphData && (
                <div className="text-right">
                  <div className="text-white font-semibold">
                    {graphData.language.toUpperCase()} Project
                  </div>
                  <div className="text-gray-300 text-sm">
                    {graphData.nodes.length} nodes • {graphData.edges.length} connections
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="relative h-[calc(100vh-120px)]">
        {!graphData ? (
          /* Welcome Screen */
          <div className="h-full flex items-center justify-center p-6">
            <div className="max-w-2xl mx-auto text-center">
              <div className="mb-8">
                <div className="w-24 h-24 mx-auto mb-6 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                  <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                  </svg>
                </div>
                <h2 className="text-4xl font-bold text-white mb-4">
                  Visualize Your Codebase
                </h2>
                <p className="text-xl text-gray-300 mb-8">
                  Upload a code_graph.json file to explore your project&apos;s structure with 
                  an interactive, physics-based visualization.
                </p>
              </div>

              <div className="max-w-md mx-auto mb-8">
                <FileUpload onFileLoad={handleFileLoad} />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
                <div className="bg-black bg-opacity-30 rounded-xl p-6 backdrop-blur-sm border border-white border-opacity-10">
                  <div className="text-2xl mb-3">🎯</div>
                  <h3 className="text-white font-semibold mb-2">Interactive Exploration</h3>
                  <p className="text-gray-300 text-sm">
                    Click on nodes to see detailed information about classes, methods, and their relationships.
                  </p>
                </div>
                <div className="bg-black bg-opacity-30 rounded-xl p-6 backdrop-blur-sm border border-white border-opacity-10">
                  <div className="text-2xl mb-3">⚡</div>
                  <h3 className="text-white font-semibold mb-2">Physics-Based Layout</h3>
                  <p className="text-gray-300 text-sm">
                    Advanced force simulation creates optimal layouts that reveal natural code organization.
                  </p>
                </div>
                <div className="bg-black bg-opacity-30 rounded-xl p-6 backdrop-blur-sm border border-white border-opacity-10">
                  <div className="text-2xl mb-3">📊</div>
                  <h3 className="text-white font-semibold mb-2">Rich Analytics</h3>
                  <p className="text-gray-300 text-sm">
                    Get insights into code complexity, dependencies, and architectural patterns.
                  </p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          /* Main Application */
          <div className="h-full flex">
            {/* Left Sidebar */}
            <div className="w-80 p-6 space-y-6 overflow-y-auto">
              <ControlsPanel
                onFiltersChange={setFilters}
                onSearchChange={setSearchTerm}
                onConnectionsToggle={setShowConnections}
                showConnections={showConnections}
              />
              <StatsPanel data={graphData} />
            </div>

            {/* Main Visualization */}
            <div className="flex-1 relative">
              <CodeGraphVisualization
                data={graphData}
                onNodeSelect={handleNodeSelect}
                filters={filters}
                searchTerm={searchTerm}
                showConnections={showConnections}
              />
            </div>

            {/* Right Sidebar */}
            <div className="w-96 p-6 overflow-y-auto">
              <NodeInfoPanel
                selectedNode={selectedNode}
                connections={selectedNode ? calculateConnections(selectedNode) : undefined}
              />
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="relative z-10 p-4 border-t border-white border-opacity-10 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto text-center">
          <p className="text-gray-400 text-sm">
            CodeGrapher - Interactive code visualization tool • 
            <a 
              href="https://github.com" 
              className="text-blue-400 hover:text-blue-300 ml-2 transition-colors"
            >
              View on GitHub
            </a>
          </p>
        </div>
      </footer>
    </div>
  );
}
