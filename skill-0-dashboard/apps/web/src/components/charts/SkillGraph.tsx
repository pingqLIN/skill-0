import { useMemo } from 'react';
import type { GraphEdge, GraphNode } from '@/api/types';

const GRAPH_WIDTH = 900;
const GRAPH_HEIGHT = 520;
const CATEGORY_COLOR_PALETTE = [
  '#38bdf8',
  '#a78bfa',
  '#fbbf24',
  '#34d399',
  '#f87171',
  '#64748b',
];
const MAX_LABEL_LENGTH = 16;
const MIN_NODE_RADIUS = 6;
const MAX_NODE_RADIUS = 14;
const GRAPH_PADDING = 60;
const LABEL_VERTICAL_OFFSET = 12;

const truncateNodeLabel = (name: string) =>
  name.length > MAX_LABEL_LENGTH ? `${name.slice(0, MAX_LABEL_LENGTH)}…` : name;

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  width?: number;
  height?: number;
}

export function SkillGraph({ nodes, edges, width = GRAPH_WIDTH, height = GRAPH_HEIGHT }: Props) {
  const categoryColors = useMemo(() => {
    const categories = Array.from(
      new Set(nodes.map((node) => node.category || 'uncategorized')),
    ).sort();
    return new Map(
      categories.map((category, index) => [
        category,
        CATEGORY_COLOR_PALETTE[index % CATEGORY_COLOR_PALETTE.length],
      ]),
    );
  }, [nodes]);

  const nodePositions = useMemo(() => {
    if (nodes.length === 0) {
      return new Map<string, { x: number; y: number }>();
    }
    const radius = Math.min(width, height) / 2 - GRAPH_PADDING;
    const centerX = width / 2;
    const centerY = height / 2;
    const total = Math.max(nodes.length, 1);

    return new Map(
      nodes.map((node, index) => {
        const angle = (2 * Math.PI * index) / total;
        const x = centerX + radius * Math.cos(angle);
        const y = centerY + radius * Math.sin(angle);
        return [node.id, { x, y }];
      }),
    );
  }, [nodes, width, height]);

  const maxLinkCount = useMemo(
    () => (nodes.length === 0 ? 1 : Math.max(1, ...nodes.map((node) => node.link_count))),
    [nodes],
  );

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full h-full"
      role="img"
      aria-label="Skill relationship graph"
    >
      <g stroke="#94a3b8" strokeWidth={1} opacity={0.6}>
        {edges.map((edge) => {
          const source = nodePositions.get(edge.source);
          const target = nodePositions.get(edge.target);
          if (!source || !target) {
            return null;
          }
          return (
            <line
              key={`${edge.source}-${edge.target}-${edge.link_type}`}
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
          const size =
            MIN_NODE_RADIUS +
            (node.link_count / maxLinkCount) * (MAX_NODE_RADIUS - MIN_NODE_RADIUS);
          const color =
            categoryColors.get(node.category || 'uncategorized') ?? CATEGORY_COLOR_PALETTE[0];

          return (
            <g key={node.id}>
              <circle cx={position.x} cy={position.y} r={size} fill={color}>
                <title>{node.name}</title>
              </circle>
              <text
                x={position.x}
                y={position.y + size + LABEL_VERTICAL_OFFSET}
                textAnchor="middle"
                className="fill-slate-700 text-[10px]"
                aria-label={node.name}
              >
                {truncateNodeLabel(node.name)}
              </text>
            </g>
          );
        })}
      </g>
    </svg>
  );
}
