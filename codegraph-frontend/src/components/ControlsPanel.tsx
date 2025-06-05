'use client';

import { useState } from 'react';

interface ControlsPanelProps {
  onFiltersChange: (filters: {
    showFiles: boolean;
    showClasses: boolean;
    showMethods: boolean;
    showFunctions: boolean;
    showImports: boolean;
  }) => void;
  onSearchChange: (searchTerm: string) => void;
  onConnectionsToggle: (show: boolean) => void;
  showConnections: boolean;
  className?: string;
}

export default function ControlsPanel({
  onFiltersChange,
  onSearchChange,
  onConnectionsToggle,
  showConnections,
  className = ''
}: ControlsPanelProps) {
  const [filters, setFilters] = useState({
    showFiles: true,
    showClasses: true,
    showMethods: true,
    showFunctions: true,
    showImports: true
  });

  const [searchTerm, setSearchTerm] = useState('');
  const [isExpanded, setIsExpanded] = useState(true);

  const handleFilterChange = (filterName: keyof typeof filters) => {
    const newFilters = { ...filters, [filterName]: !filters[filterName] };
    setFilters(newFilters);
    onFiltersChange(newFilters);
  };

  const handleSearchChange = (value: string) => {
    setSearchTerm(value);
    onSearchChange(value);
  };

  const resetFilters = () => {
    const resetFilters = {
      showFiles: true,
      showClasses: true,
      showMethods: true,
      showFunctions: true,
      showImports: true
    };
    setFilters(resetFilters);
    onFiltersChange(resetFilters);
    setSearchTerm('');
    onSearchChange('');
  };

  return (
    <div className={`bg-black bg-opacity-80 backdrop-blur-md rounded-xl border border-white border-opacity-20 shadow-2xl transition-all duration-300 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white border-opacity-10">
        <h3 className="text-white font-semibold text-lg flex items-center">
          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4" />
          </svg>
          Controls
        </h3>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-white hover:text-blue-300 transition-colors"
        >
          <svg 
            className={`w-5 h-5 transition-transform ${isExpanded ? 'rotate-180' : ''}`} 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
          </svg>
        </button>
      </div>

      {/* Content */}
      {isExpanded && (
        <div className="p-4 space-y-6">
          {/* Search */}
          <div>
            <label className="block text-white text-sm font-medium mb-2">
              Search Nodes
            </label>
            <div className="relative">
              <svg 
                className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => handleSearchChange(e.target.value)}
                placeholder="Search by name..."
                className="w-full pl-10 pr-4 py-2 bg-white bg-opacity-10 border border-white border-opacity-20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              />
              {searchTerm && (
                <button
                  onClick={() => handleSearchChange('')}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
          </div>

          {/* Display Options */}
          <div>
            <label className="block text-white text-sm font-medium mb-3">
              Display Options
            </label>
            <div className="space-y-2">
              <label className="flex items-center text-white cursor-pointer hover:text-blue-300 transition-colors">
                <input
                  type="checkbox"
                  checked={showConnections}
                  onChange={(e) => onConnectionsToggle(e.target.checked)}
                  className="mr-3 rounded bg-white bg-opacity-10 border-white border-opacity-20 text-blue-500 focus:ring-blue-500 focus:ring-opacity-50"
                />
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                </svg>
                Show Connections
              </label>
            </div>
          </div>

          {/* Node Type Filters */}
          <div>
            <label className="block text-white text-sm font-medium mb-3">
              Node Types
            </label>
            <div className="space-y-2">
              {[
                { key: 'showFiles', label: 'Files', icon: '📄', color: '#FF6B6B' },
                { key: 'showClasses', label: 'Classes', icon: '🏗️', color: '#4ECDC4' },
                { key: 'showMethods', label: 'Methods', icon: '⚙️', color: '#45B7D1' },
                { key: 'showFunctions', label: 'Functions', icon: '🔧', color: '#96CEB4' },
                { key: 'showImports', label: 'Imports', icon: '📦', color: '#DDA0DD' }
              ].map(({ key, label, icon, color }) => (
                <label 
                  key={key}
                  className="flex items-center text-white cursor-pointer hover:text-blue-300 transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={filters[key as keyof typeof filters]}
                    onChange={() => handleFilterChange(key as keyof typeof filters)}
                    className="mr-3 rounded bg-white bg-opacity-10 border-white border-opacity-20 text-blue-500 focus:ring-blue-500 focus:ring-opacity-50"
                  />
                  <span className="mr-2">{icon}</span>
                  <span className="flex-1">{label}</span>
                  <div 
                    className="w-3 h-3 rounded-full ml-2"
                    style={{ backgroundColor: color }}
                  ></div>
                </label>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="space-y-2">
            <button
              onClick={resetFilters}
              className="w-full bg-gradient-to-r from-gray-600 to-gray-700 hover:from-gray-700 hover:to-gray-800 text-white py-2 px-4 rounded-lg transition-all duration-300 flex items-center justify-center space-x-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span>Reset Filters</span>
            </button>
          </div>

          {/* Legend */}
          <div>
            <label className="block text-white text-sm font-medium mb-3">
              Connection Types
            </label>
            <div className="space-y-2 text-sm">
              {[
                { type: 'calls', color: '#45b7d1', style: 'solid' },
                { type: 'inherits', color: '#ff6b6b', style: 'dashed' },
                { type: 'implements', color: '#4ecdc4', style: 'dotted' },
                { type: 'instantiates', color: '#ffa500', style: 'solid' }
              ].map(({ type, color, style }) => (
                <div key={type} className="flex items-center text-gray-300">
                  <svg className="w-6 h-2 mr-3" viewBox="0 0 24 2">
                    <line
                      x1="0"
                      y1="1"
                      x2="24"
                      y2="1"
                      stroke={color}
                      strokeWidth="2"
                      strokeDasharray={style === 'dashed' ? '4,2' : style === 'dotted' ? '2,2' : 'none'}
                    />
                  </svg>
                  <span className="capitalize">{type}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}