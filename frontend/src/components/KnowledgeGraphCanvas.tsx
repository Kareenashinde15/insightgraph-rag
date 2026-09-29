import React, { useRef, useEffect, useState, useMemo } from 'react';
import { GraphNode, GraphEdge } from '../types';
import { ZoomIn, ZoomOut, RotateCcw, Filter, Search } from 'lucide-react';

interface KnowledgeGraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onSelectNode: (node: GraphNode) => void;
  onSelectEdge?: (edge: GraphEdge) => void;
  selectedNodeId?: string | null;
  height?: string | number;
  interactive?: boolean;
}

interface NodePosition {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

export const KnowledgeGraphCanvas: React.FC<KnowledgeGraphCanvasProps> = ({
  nodes,
  edges,
  onSelectNode,
  onSelectEdge,
  selectedNodeId,
  height = '620px',
  interactive = true,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [draggedNodeId, setDraggedNodeId] = useState<string | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState('');
  const [selectedTypeFilter, setSelectedTypeFilter] = useState<string>('ALL');

  // Node position simulation state
  const positionsRef = useRef<{ [id: string]: NodePosition }>({});

  const entityTypes = ['ALL', 'Person', 'Company', 'Project', 'Technology', 'Location'];

  const filteredNodes = useMemo(() => {
    return nodes.filter((n) => {
      const matchesType = selectedTypeFilter === 'ALL' || n.type.toLowerCase() === selectedTypeFilter.toLowerCase();
      const matchesSearch = !searchFilter || n.name.toLowerCase().includes(searchFilter.toLowerCase());
      return matchesType && matchesSearch;
    });
  }, [nodes, selectedTypeFilter, searchFilter]);

  const filteredEdges = useMemo(() => {
    const nodeIds = new Set(filteredNodes.map((n) => n.id));
    return edges.filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target));
  }, [edges, filteredNodes]);

  // Color mapping based on Brand Guidelines
  const getNodeColor = (type: string) => {
    const t = (type || '').toLowerCase();
    if (t === 'person') return '#2E3A8C';
    if (t === 'company' || t === 'organization') return '#4A5FD9';
    if (t === 'project') return '#1A2254';
    if (t.includes('tech') || t.includes('database') || t.includes('framework') || t.includes('language')) return '#4355B9';
    if (t === 'location') return '#64748B';
    return '#475569';
  };

  // Initialize node layout with circular/force spread
  useEffect(() => {
    const width = 800;
    const heightVal = 600;
    const radius = Math.min(width, heightVal) * 0.38;
    const count = nodes.length;

    nodes.forEach((n, idx) => {
      if (!positionsRef.current[n.id]) {
        const angle = (idx / count) * 2 * Math.PI;
        // Group by type slightly
        const jitter = (Math.random() - 0.5) * 60;
        positionsRef.current[n.id] = {
          x: width / 2 + Math.cos(angle) * (radius + jitter),
          y: heightVal / 2 + Math.sin(angle) * (radius + jitter),
          vx: 0,
          vy: 0,
        };
      }
    });
  }, [nodes]);

  // Render loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;

    const render = () => {
      const width = canvas.width;
      const heightVal = canvas.height;

      ctx.clearRect(0, 0, width, heightVal);
      ctx.save();

      // Pan & Zoom transform
      ctx.translate(pan.x, pan.y);
      ctx.scale(zoom, zoom);

      // Draw Edges
      filteredEdges.forEach((edge) => {
        const p1 = positionsRef.current[edge.source];
        const p2 = positionsRef.current[edge.target];
        if (!p1 || !p2) return;

        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.strokeStyle = '#94A3B8';
        ctx.lineWidth = 1.4;
        ctx.stroke();

        // Arrow head
        const headlen = 8;
        const angle = Math.atan2(p2.y - p1.y, p2.x - p1.x);
        const midX = (p1.x + p2.x) / 2;
        const midY = (p1.y + p2.y) / 2;

        ctx.beginPath();
        ctx.moveTo(midX, midY);
        ctx.lineTo(midX - headlen * Math.cos(angle - Math.PI / 6), midY - headlen * Math.sin(angle - Math.PI / 6));
        ctx.lineTo(midX - headlen * Math.cos(angle + Math.PI / 6), midY - headlen * Math.sin(angle + Math.PI / 6));
        ctx.fillStyle = '#64748B';
        ctx.fill();

        // Relationship label
        ctx.font = '10px Inter, sans-serif';
        ctx.fillStyle = '#475569';
        ctx.textAlign = 'center';
        ctx.fillText(edge.relationship_type, midX, midY - 6);
      });

      // Draw Nodes
      filteredNodes.forEach((node) => {
        const pos = positionsRef.current[node.id];
        if (!pos) return;

        const isSelected = selectedNodeId === node.id;
        const isHovered = hoveredNodeId === node.id;
        const baseColor = getNodeColor(node.type);
        const radius = isSelected ? 24 : isHovered ? 22 : 18;

        // Outer Glow / Selection Ring
        if (isSelected || isHovered) {
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, radius + 5, 0, 2 * Math.PI);
          ctx.fillStyle = 'rgba(74, 95, 217, 0.25)';
          ctx.fill();
        }

        // Main Node Circle
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, radius, 0, 2 * Math.PI);
        ctx.fillStyle = baseColor;
        ctx.fill();
        ctx.lineWidth = isSelected ? 3 : 2;
        ctx.strokeStyle = '#FFFFFF';
        ctx.stroke();

        // Node Label
        ctx.font = isSelected ? 'bold 12px Inter, sans-serif' : '11px Inter, sans-serif';
        ctx.fillStyle = isSelected ? '#1A1A1A' : '#334155';
        ctx.textAlign = 'center';
        ctx.fillText(node.name, pos.x, pos.y + radius + 15);

        // Type subtitle
        ctx.font = '9px Inter, sans-serif';
        ctx.fillStyle = '#64748B';
        ctx.fillText(node.type.toUpperCase(), pos.x, pos.y + radius + 27);
      });

      ctx.restore();
    };

    render();
  }, [filteredNodes, filteredEdges, zoom, pan, selectedNodeId, hoveredNodeId]);

  // Mouse interaction handlers
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!interactive) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mouseX = (e.clientX - rect.left - pan.x) / zoom;
    const mouseY = (e.clientY - rect.top - pan.y) / zoom;

    // Check if clicked a node
    for (const node of filteredNodes) {
      const pos = positionsRef.current[node.id];
      if (pos) {
        const dist = Math.hypot(pos.x - mouseX, pos.y - mouseY);
        if (dist <= 22) {
          setDraggedNodeId(node.id);
          onSelectNode(node);
          return;
        }
      }
    }

    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!interactive) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mouseX = (e.clientX - rect.left - pan.x) / zoom;
    const mouseY = (e.clientY - rect.top - pan.y) / zoom;

    if (draggedNodeId) {
      if (positionsRef.current[draggedNodeId]) {
        positionsRef.current[draggedNodeId].x = mouseX;
        positionsRef.current[draggedNodeId].y = mouseY;
        setPan({ ...pan }); // force redraw
      }
      return;
    }

    if (isDragging) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
      return;
    }

    // Hover detection
    let foundHover: string | null = null;
    for (const node of filteredNodes) {
      const pos = positionsRef.current[node.id];
      if (pos) {
        const dist = Math.hypot(pos.x - mouseX, pos.y - mouseY);
        if (dist <= 22) {
          foundHover = node.id;
          break;
        }
      }
    }
    setHoveredNodeId(foundHover);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setDraggedNodeId(null);
  };

  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    if (!interactive) return;
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    setZoom((prev) => Math.max(0.4, Math.min(2.5, prev * zoomFactor)));
  };

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  return (
    <div style={{ position: 'relative', width: '100%', height, overflow: 'hidden', borderRadius: '12px', border: '1px solid var(--jm-border)', backgroundColor: 'var(--bg-surface)' }}>
      {/* Canvas Controls Toolbar */}
      {interactive && (
        <div style={{
          position: 'absolute',
          top: '14px',
          left: '14px',
          zIndex: 10,
          display: 'flex',
          gap: '8px',
          backgroundColor: 'rgba(255, 255, 255, 0.92)',
          backdropFilter: 'blur(8px)',
          padding: '6px 12px',
          borderRadius: '8px',
          border: '1px solid var(--jm-border)',
          boxShadow: '0 2px 6px rgba(0, 0, 0, 0.08)',
        }}>
          {/* Entity Type Filter Tabs */}
          <div style={{ display: 'flex', gap: '4px' }}>
            {entityTypes.map((t) => (
              <button
                key={t}
                onClick={() => setSelectedTypeFilter(t)}
                style={{
                  padding: '4px 9px',
                  borderRadius: '6px',
                  border: 'none',
                  fontSize: '11.5px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  backgroundColor: selectedTypeFilter === t ? 'var(--jm-dark-blue)' : 'transparent',
                  color: selectedTypeFilter === t ? '#FFFFFF' : 'var(--text-secondary)',
                  transition: 'all 0.14s ease',
                }}
              >
                {t}
              </button>
            ))}
          </div>

          <div style={{ width: '1px', backgroundColor: 'var(--jm-border)', margin: '0 4px' }} />

          {/* Search inside canvas */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Search size={14} color="#64748B" />
            <input
              type="text"
              placeholder="Filter nodes..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              style={{
                border: 'none',
                background: 'transparent',
                fontSize: '12px',
                outline: 'none',
                width: '95px',
              }}
            />
          </div>
        </div>
      )}

      {/* Zoom / Pan Action Floating Controls */}
      {interactive && (
        <div style={{
          position: 'absolute',
          bottom: '16px',
          right: '16px',
          zIndex: 10,
          display: 'flex',
          flexDirection: 'column',
          gap: '6px',
          backgroundColor: 'rgba(255, 255, 255, 0.92)',
          padding: '6px',
          borderRadius: '8px',
          border: '1px solid var(--jm-border)',
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
        }}>
          <button onClick={() => setZoom((z) => Math.min(2.5, z + 0.15))} title="Zoom In" style={{ border: 'none', background: 'transparent', cursor: 'pointer', padding: '4px' }}>
            <ZoomIn size={16} color="#334155" />
          </button>
          <button onClick={() => setZoom((z) => Math.max(0.4, z - 0.15))} title="Zoom Out" style={{ border: 'none', background: 'transparent', cursor: 'pointer', padding: '4px' }}>
            <ZoomOut size={16} color="#334155" />
          </button>
          <button onClick={resetView} title="Reset View" style={{ border: 'none', background: 'transparent', cursor: 'pointer', padding: '4px' }}>
            <RotateCcw size={16} color="#334155" />
          </button>
        </div>
      )}

      {/* Main Canvas */}
      <canvas
        ref={canvasRef}
        width={1000}
        height={650}
        style={{ width: '100%', height: '100%', cursor: isDragging ? 'grabbing' : 'grab' }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onWheel={handleWheel}
      />
    </div>
  );
};
