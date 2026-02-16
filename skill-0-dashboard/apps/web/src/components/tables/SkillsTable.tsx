import { useNavigate } from 'react-router-dom';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { ArrowUpDown } from 'lucide-react';
import type { SkillSummary } from '@/api/types';

const riskColors: Record<string, string> = {
  safe: 'bg-green-100 text-green-800',
  low: 'bg-yellow-100 text-yellow-800',
  medium: 'bg-orange-100 text-orange-800',
  high: 'bg-red-100 text-red-800',
  critical: 'bg-red-200 text-red-900',
  blocked: 'bg-gray-100 text-gray-800',
};

const statusColors: Record<string, string> = {
  pending: 'bg-amber-100 text-amber-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  blocked: 'bg-gray-100 text-gray-800',
};

interface Props {
  data: SkillSummary[];
  sortBy: string;
  sortOrder: 'asc' | 'desc';
  onSort: (column: string) => void;
}

export function SkillsTable({ data, sortBy, sortOrder, onSort }: Props) {
  const navigate = useNavigate();

  const SortHeader = ({ column, label }: { column: string; label: string }) => (
    <TableHead 
      className="cursor-pointer hover:bg-slate-50"
      onClick={() => onSort(column)}
    >
      <div className="flex items-center gap-1">
        {label}
        {sortBy === column && (
          <ArrowUpDown className={`h-4 w-4 ${sortOrder === 'desc' ? 'rotate-180' : ''}`} />
        )}
      </div>
    </TableHead>
  );

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <SortHeader column="name" label="Name" />
          <SortHeader column="risk_score" label="Risk" />
          <TableHead>Equivalence</TableHead>
          <SortHeader column="status" label="Status" />
          <TableHead>Author</TableHead>
          <TableHead>License</TableHead>
          <SortHeader column="updated_at" label="Updated" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((skill) => (
          <TableRow 
            key={skill.skill_id}
            className="cursor-pointer hover:bg-slate-50"
            onClick={() => navigate(`/skills/${skill.skill_id}`)}
          >
            <TableCell className="font-medium">{skill.name}</TableCell>
            <TableCell>
              <Badge className={riskColors[skill.risk_level] || riskColors.blocked}>
                {skill.risk_level} ({skill.risk_score})
              </Badge>
            </TableCell>
            <TableCell>
              {skill.equivalence_score !== null 
                ? `${Math.round(skill.equivalence_score * 100)}%`
                : '-'}
            </TableCell>
            <TableCell>
              <Badge className={statusColors[skill.status] || statusColors.pending}>
                {skill.status}
              </Badge>
            </TableCell>
            <TableCell>{skill.author_name}</TableCell>
            <TableCell>{skill.license_spdx}</TableCell>
            <TableCell>{new Date(skill.updated_at).toLocaleDateString()}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
