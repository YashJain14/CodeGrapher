'use client';

import { GraphData } from '@/types/graph';
import { useMemo } from 'react';

interface StatsPanelProps {
  data: GraphData | null;
  className?: string;
}

export default function StatsPanel({ data, className = '' }: StatsPanelProps) {
  const stats = useMemo(() => {
    if (!data) return null;

    const totalNodes = data.nodes.length;
    const totalEdges = data.edges.length;
    
    const nodesByType: Record<string, number> = {};
    const edgesByType: Record<string, number> = {};
    
    data.nodes.forEach(node => {
      nodesByType[node.type] = (nodesByType[node.type] || 0) + 1;
    });
    
    data.edges.forEach(edge => {
      edgesByType[edge.type] = (edgesByType[edge.type] || 0) + 1;
    });

    // Calculate cross-file connections
    const crossFileConnections = data.edges.filter(edge => {
      const sourceNode = data.nodes.find(n => n.id === edge.source);
      const targetNode = data.nodes.find(n => n.id === edge.target);
      return sourceNode && targetNode && sourceNode.file !== targetNode.file;
    }).length;

    return {
      totalNodes,
      totalEdges,
      nodesByType,
      edgesByType,
      crossFileConnections,
      language: data.language,
      rootPath: data.root_path,
      externalDependencies: data.external_dependencies?.length || 0
    };
  }, [data]);

  if (!stats) {
    return (
      <div className={`bg-black bg-opacity-80 backdrop-blur-md rounded-xl border border-white border-opacity-20 shadow-2xl ${className}`}>
        <div className="p-6 text-center">
          <div className="text-gray-400 mb-4">
            <svg className="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <h3 className="text-white font-semibold text-lg mb-2">Graph Statistics</h3>
          <p className="text-gray-400 text-sm">
            Load a graph to see detailed statistics about your codebase.
          </p>
        </div>
      </div>
    );
  }

  const getNodeTypeIcon = (type: string) => {
    const icons: Record<string, string> = {
      file: '📄',
      class: '🏗️',
      interface: '🔌',
      method: '⚙️',
      function: '🔧',
      variable: '📝',
      import: '📦',
      module: '📚',
      package: '📦'
    };
    return icons[type] || '📄';
  };

  const getGraphSizeCategory = () => {
    if (stats.totalNodes > 500) return { label: 'Massive', color: 'text-red-400', icon: '🚀' };
    if (stats.totalNodes > 100) return { label: 'Large', color: 'text-orange-400', icon: '⚡' };
    if (stats.totalNodes > 50) return { label: 'Medium', color: 'text-yellow-400', icon: '📊' };
    return { label: 'Small', color: 'text-green-400', icon: '✨' };
  };

  const sizeCategory = getGraphSizeCategory();

  return (
    <div className={`bg-black bg-opacity-80 backdrop-blur-md rounded-xl border border-white border-opacity-20 shadow-2xl overflow-hidden ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-white border-opacity-10">
        <h3 className="text-white font-semibold text-lg flex items-center">
          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          Statistics
        </h3>
      </div>

      {/* Content */}
      <div className="p-4 space-y-6 max-h-96 overflow-y-auto">
        {/* Project Overview */}
        <div>
          <h4 className="text-blue-300 text-sm font-medium mb-3">Project Overview</h4>
          <div className="space-y-2">
            <div className="bg-white bg-opacity-5 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <span className="text-gray-300 text-sm">Language</span>
                <span className="text-white font-medium capitalize">{stats.language}</span>
              </div>
            </div>
            <div className="bg-white bg-opacity-5 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <span className="text-gray-300 text-sm">Graph Size</span>
                <span className={`font-medium flex items-center ${sizeCategory.color}`}>
                  <span className="mr-1">{sizeCategory.icon}</span>
                  {sizeCategory.label}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Overview Stats */}
        <div>
          <h4 className="text-blue-300 text-sm font-medium mb-3">Overview</h4>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-gradient-to-br from-blue-600 to-blue-800 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-white">{stats.totalNodes}</div>
              <div className="text-blue-200 text-sm">Nodes</div>
            </div>
            <div className="bg-gradient-to-br from-purple-600 to-purple-800 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-white">{stats.totalEdges}</div>
              <div className="text-purple-200 text-sm">Connections</div>
            </div>
            <div className="bg-gradient-to-br from-green-600 to-green-800 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-white">{stats.crossFileConnections}</div>
              <div className="text-green-200 text-sm">Cross-File</div>
            </div>
            <div className="bg-gradient-to-br from-orange-600 to-orange-800 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-white">{stats.externalDependencies}</div>
              <div className="text-orange-200 text-sm">External</div>
            </div>
          </div>
        </div>

        {/* Node Types Breakdown */}
        <div>
          <h4 className="text-blue-300 text-sm font-medium mb-3">Node Types</h4>
          <div className="space-y-2">
            {Object.entries(stats.nodesByType)
              .sort(([,a], [,b]) => b - a)
              .map(([type, count]) => {
                const percentage = ((count / stats.totalNodes) * 100).toFixed(1);
                return (
                  <div key={type} className="bg-white bg-opacity-5 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-white flex items-center">
                        <span className="mr-2">{getNodeTypeIcon(type)}</span>
                        <span className="capitalize">{type}s</span>
                      </span>
                      <span className="text-white font-medium">{count}</span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2">
                      <div 
                        className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${percentage}%` }}
                      ></div>
                    </div>
                    <div className="text-gray-400 text-xs mt-1">{percentage}%</div>
                  </div>
                );
              })}
          </div>
        </div>

        {/* Connection Types */}
        <div>
          <h4 className="text-blue-300 text-sm font-medium mb-3">Connection Types</h4>
          <div className="space-y-2">
            {Object.entries(stats.edgesByType)
              .sort(([,a], [,b]) => b - a)
              .map(([type, count]) => {
                const percentage = ((count / stats.totalEdges) * 100).toFixed(1);
                const colors: Record<string, string> = {
                  calls: 'from-blue-500 to-blue-600',
                  inherits: 'from-red-500 to-red-600',
                  implements: 'from-teal-500 to-teal-600',
                  instantiates: 'from-orange-500 to-orange-600',
                  contains: 'from-gray-500 to-gray-600'
                };
                return (
                  <div key={type} className="bg-white bg-opacity-5 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-white capitalize">{type}</span>
                      <span className="text-white font-medium">{count}</span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2">
                      <div 
                        className={`bg-gradient-to-r ${colors[type] || 'from-gray-500 to-gray-600'} h-2 rounded-full transition-all duration-300`}
                        style={{ width: `${percentage}%` }}
                      ></div>
                    </div>
                    <div className="text-gray-400 text-xs mt-1">{percentage}%</div>
                  </div>
                );
              })}
          </div>
        </div>

        {/* Complexity Metrics */}
        <div>
          <h4 className="text-blue-300 text-sm font-medium mb-3">Complexity Metrics</h4>
          <div className="space-y-2">
            <div className="bg-white bg-opacity-5 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <span className="text-gray-300 text-sm">Avg Connections per Node</span>
                <span className="text-white font-medium">
                  {stats.totalNodes > 0 ? (stats.totalEdges / stats.totalNodes).toFixed(1) : '0'}
                </span>
              </div>
            </div>
            <div className="bg-white bg-opacity-5 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <span className="text-gray-300 text-sm">Cross-File Ratio</span>
                <span className="text-white font-medium">
                  {stats.totalEdges > 0 ? ((stats.crossFileConnections / stats.totalEdges) * 100).toFixed(1) : '0'}%
                </span>
              </div>
            </div>
            {stats.nodesByType.file && (
              <div className="bg-white bg-opacity-5 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <span className="text-gray-300 text-sm">Avg Nodes per File</span>
                  <span className="text-white font-medium">
                    {(stats.totalNodes / stats.nodesByType.file).toFixed(1)}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}