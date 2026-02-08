import { useMemo } from 'react';
import type { GraphEdge, GraphNode } from '@/api/types';

const GRAPH_WIDTH = 900;
const GRAPH_HEIGHT = 520;
const NODE_COLOR_PALETTE = ['#38bdf8', '#a78bfa', '#fbbf24', '#34d399', '#f87171', '#64748b'];
const MAX_LABEL_LENGTH = 16;
const MIN_NODE_RADIUS = 6;
const MAX_NODE_RADIUS = 14;

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
      categories.map((category, index) => [
        category,
        NODE_COLOR_PALETTE[index % NODE_COLOR_PALETTE.length],
      ]),
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

  const getNodeLabel = (name: string) =>
    name.length > MAX_LABEL_LENGTH ? `${name.slice(0, MAX_LABEL_LENGTH)}…` : name;

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
          const size = Math.max(
            MIN_NODE_RADIUS,
            Math.min(MAX_NODE_RADIUS, MIN_NODE_RADIUS + node.link_count),
          );
          const color =
            categoryColors.get(node.category || 'uncategorized') ?? NODE_COLOR_PALETTE[0];

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
                aria-label={node.name}
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
