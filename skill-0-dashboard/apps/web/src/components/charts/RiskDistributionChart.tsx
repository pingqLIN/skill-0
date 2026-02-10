<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
import { PieChart, Pie, Cell, Legend, ResponsiveContainer, Tooltip } from 'recharts';
import type { RiskDistribution } from '@/api/types';

const RISK_COLORS = {
  safe: '#22c55e',
  low: '#eab308',
  medium: '#f97316',
  high: '#ef4444',
  critical: '#dc2626',
  blocked: '#6b7280',
};

interface Props {
  data: RiskDistribution;
}

export function RiskDistributionChart({ data }: Props) {
  const chartData = Object.entries(data).map(([name, value]) => ({
    name,
    value,
    color: RISK_COLORS[name as keyof typeof RISK_COLORS],
  }));

  return (
    <ResponsiveContainer width="100%" height={250}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={80}
          paddingAngle={5}
          dataKey="value"
        >
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}
=======
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
import { PieChart, Pie, Cell, Legend, ResponsiveContainer, Tooltip } from 'recharts';
import type { RiskDistribution } from '@/api/types';

const RISK_COLORS = {
  safe: '#22c55e',
  low: '#eab308',
  medium: '#f97316',
  high: '#ef4444',
  critical: '#dc2626',
  blocked: '#6b7280',
};

interface Props {
  data: RiskDistribution;
}

export function RiskDistributionChart({ data }: Props) {
  const chartData = Object.entries(data).map(([name, value]) => ({
    name,
    value,
    color: RISK_COLORS[name as keyof typeof RISK_COLORS],
  }));

  return (
    <ResponsiveContainer width="100%" height={250}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={80}
          paddingAngle={5}
          dataKey="value"
        >
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}
<<<<<<< Updated upstream
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
