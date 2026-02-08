import { useMemo } from 'react';
import type { GraphEdge, GraphNode } from '@/api/types';

const GRAPH_WIDTH = 900;
const GRAPH_HEIGHT = 520;
const NODE_COLORS = ['#38bdf8', '#a78bfa', '#fbbf24', '#34d399', '#f87171', '#cbd5f5'];

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export function SkillGraph({ nodes, edges }: Props) {
  const categoryColors = useMemo(() => {
    const categories = Array.from(
      new Set(nodes.map((node) => node.category || 'uncategorized')),
    ).sort();
    return new Map(
      categories.map((category, index) => [category, NODE_COLORS[index % NODE_COLORS.length]]),
    );
  }, [nodes]);

  const nodePositions = useMemo(() => {
    const radius = Math.min(GRAPH_WIDTH, GRAPH_HEIGHT) / 2 - 60;
    const centerX = GRAPH_WIDTH / 2;
    const centerY = GRAPH_HEIGHT / 2;
    const total = Math.max(nodes.length, 1);

    return new Map(
      nodes.map((node, index) => {
        const angle = (2 * Math.PI * index) / total;
        const x = centerX + radius * Math.cos(angle);
        const y = centerY + radius * Math.sin(angle);
        return [node.id, { x, y }];
      }),
    );
  }, [nodes]);

  const getNodeLabel = (name: string) => (name.length > 16 ? `${name.slice(0, 16)}…` : name);

  return (
    <svg
      viewBox={`0 0 ${GRAPH_WIDTH} ${GRAPH_HEIGHT}`}
      className="w-full h-full"
      role="img"
      aria-label="Skill relationship graph"
    >
      <g stroke="#94a3b8" strokeWidth={1} opacity={0.6}>
        {edges.map((edge, index) => {
          const source = nodePositions.get(edge.source);
          const target = nodePositions.get(edge.target);
          if (!source || !target) {
            return null;
          }
          return (
            <line
              key={`${edge.source}-${edge.target}-${index}`}
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
            />
          );
        })}
      </g>
      <g>
        {nodes.map((node) => {
          const position = nodePositions.get(node.id);
          if (!position) {
            return null;
          }
          const size = Math.max(6, Math.min(14, 6 + node.link_count));
          const color = categoryColors.get(node.category || 'uncategorized') ?? NODE_COLORS[0];

          return (
            <g key={node.id}>
              <circle cx={position.x} cy={position.y} r={size} fill={color}>
                <title>{node.name}</title>
              </circle>
              <text
                x={position.x}
                y={position.y + size + 12}
                textAnchor="middle"
                className="fill-slate-700 text-[10px]"
              >
                {getNodeLabel(node.name)}
              </text>
            </g>
          );
        })}
      </g>
    </svg>
  );
}
