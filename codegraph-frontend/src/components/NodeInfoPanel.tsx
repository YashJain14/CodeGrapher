'use client';

import { D3Node } from '@/types/graph';

interface NodeInfoPanelProps {
  selectedNode: D3Node | null;
  connections?: {
    incoming: Record<string, number>;
    outgoing: Record<string, number>;
  };
  className?: string;
}

export default function NodeInfoPanel({ selectedNode, connections, className = '' }: NodeInfoPanelProps) {
  if (!selectedNode) {
    return (
      <div className={`bg-black bg-opacity-80 backdrop-blur-md rounded-xl border border-white border-opacity-20 shadow-2xl ${className}`}>
        <div className="p-6 text-center">
          <div className="text-gray-400 mb-4">
            <svg className="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 className="text-white font-semibold text-lg mb-2">Node Information</h3>
          <p className="text-gray-400 text-sm">
            Click on a node in the graph to see detailed information about it.
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

  const getNodeTypeColor = (type: string) => {
    const colors: Record<string, string> = {
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
    return colors[type] || '#999';
  };

  const formatPath = (path: string) => {
    const parts = path.split('/');
    if (parts.length > 3) {
      return `.../${parts.slice(-2).join('/')}`;
    }
    return path;
  };

  return (
    <div className={`bg-black bg-opacity-80 backdrop-blur-md rounded-xl border border-white border-opacity-20 shadow-2xl overflow-hidden ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-white border-opacity-10">
        <div className="flex items-center space-x-3">
          <div 
            className="w-4 h-4 rounded-full"
            style={{ backgroundColor: getNodeTypeColor(selectedNode.type) }}
          ></div>
          <h3 className="text-white font-semibold text-lg flex items-center">
            <span className="mr-2">{getNodeTypeIcon(selectedNode.type)}</span>
            Node Details
          </h3>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-4 max-h-96 overflow-y-auto">
        {/* Basic Information */}
        <div className="space-y-3">
          <div>
            <label className="block text-blue-300 text-sm font-medium mb-1">Name</label>
            <p className="text-white bg-white bg-opacity-5 rounded-lg p-2 break-words">
              {selectedNode.name}
            </p>
          </div>

          <div>
            <label className="block text-blue-300 text-sm font-medium mb-1">Type</label>
            <p className="text-white bg-white bg-opacity-5 rounded-lg p-2 flex items-center">
              <span className="mr-2">{getNodeTypeIcon(selectedNode.type)}</span>
              <span className="capitalize">{selectedNode.type}</span>
            </p>
          </div>

          <div>
            <label className="block text-blue-300 text-sm font-medium mb-1">File Path</label>
            <p className="text-white bg-white bg-opacity-5 rounded-lg p-2 break-words text-sm">
              <span className="text-gray-400" title={selectedNode.file}>
                {formatPath(selectedNode.file)}
              </span>
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-blue-300 text-sm font-medium mb-1">Line</label>
              <p className="text-white bg-white bg-opacity-5 rounded-lg p-2">
                {selectedNode.line || 'N/A'}
              </p>
            </div>
            <div>
              <label className="block text-blue-300 text-sm font-medium mb-1">Column</label>
              <p className="text-white bg-white bg-opacity-5 rounded-lg p-2">
                {selectedNode.column || 'N/A'}
              </p>
            </div>
          </div>
        </div>

        {/* Hierarchy Information */}
        <div className="border-t border-white border-opacity-10 pt-4">
          <label className="block text-blue-300 text-sm font-medium mb-2">Hierarchy</label>
          <div className="space-y-2">
            <div className="text-sm">
              <span className="text-gray-400">Level:</span>
              <span className="text-white ml-2">{selectedNode.level}</span>
            </div>
            {selectedNode.children && selectedNode.children.length > 0 && (
              <div className="text-sm">
                <span className="text-gray-400">Children:</span>
                <span className="text-white ml-2">{selectedNode.children.length}</span>
              </div>
            )}
          </div>
        </div>

        {/* Connections */}
        {connections && (Object.keys(connections.incoming).length > 0 || Object.keys(connections.outgoing).length > 0) && (
          <div className="border-t border-white border-opacity-10 pt-4">
            <label className="block text-blue-300 text-sm font-medium mb-3">Connections</label>
            
            {Object.keys(connections.outgoing).length > 0 && (
              <div className="mb-3">
                <h4 className="text-white text-sm font-medium mb-2 flex items-center">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                  </svg>
                  Outgoing
                </h4>
                <div className="space-y-1">
                  {Object.entries(connections.outgoing).map(([type, count]) => (
                    <div key={type} className="flex justify-between text-sm bg-white bg-opacity-5 rounded p-2">
                      <span className="text-gray-300 capitalize">{type}</span>
                      <span className="text-white font-medium">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {Object.keys(connections.incoming).length > 0 && (
              <div>
                <h4 className="text-white text-sm font-medium mb-2 flex items-center">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16l-4-4m0 0l4-4m-4 4h18" />
                  </svg>
                  Incoming
                </h4>
                <div className="space-y-1">
                  {Object.entries(connections.incoming).map(([type, count]) => (
                    <div key={type} className="flex justify-between text-sm bg-white bg-opacity-5 rounded p-2">
                      <span className="text-gray-300 capitalize">{type}</span>
                      <span className="text-white font-medium">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Metadata */}
        {selectedNode.metadata && Object.keys(selectedNode.metadata).length > 0 && (
          <div className="border-t border-white border-opacity-10 pt-4">
            <label className="block text-blue-300 text-sm font-medium mb-2">Metadata</label>
            <div className="space-y-1">
              {Object.entries(selectedNode.metadata).map(([key, value]) => (
                <div key={key} className="text-sm bg-white bg-opacity-5 rounded p-2">
                  <span className="text-gray-400">{key}:</span>
                  <span className="text-white ml-2">
                    {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer Actions */}
      <div className="border-t border-white border-opacity-10 p-4">
        <button
          onClick={() => {
            if (selectedNode.file && selectedNode.line) {
              const message = `File: ${selectedNode.file}\nLine: ${selectedNode.line}\nNode: ${selectedNode.name} (${selectedNode.type})`;
              navigator.clipboard.writeText(message).then(() => {
                // Could add a toast notification here
              });
            }
          }}
          className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white py-2 px-4 rounded-lg transition-all duration-300 flex items-center justify-center space-x-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          <span>Copy Info</span>
        </button>
      </div>
    </div>
  );
}