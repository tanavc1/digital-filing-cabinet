"use client";

import { useMemo } from 'react';
import {
    PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend,
    BarChart, Bar, XAxis, YAxis, CartesianGrid
} from 'recharts';

const RISK_COLORS: Record<string, string> = {
    High: '#ef4444',    // red-500
    Medium: '#f59e0b',  // amber-500
    Low: '#22c55e',     // green-500
    Clean: '#3b82f6',   // blue-500
    Unknown: '#9ca3af'  // gray-400
};

interface RiskChartProps {
    data: Record<string, number>;
}

export function RiskPieChart({ data }: RiskChartProps) {
    const chartData = useMemo(() => {
        return Object.entries(data)
            .filter(([_, value]) => value > 0)
            .map(([name, value]) => ({ name, value }));
    }, [data]);

    return (
        <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                    <Pie
                        data={chartData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={5}
                        dataKey="value"
                    >
                        {chartData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={RISK_COLORS[entry.name] || '#8884d8'} />
                        ))}
                    </Pie>
                    <Tooltip
                        contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    />
                    <Legend verticalAlign="bottom" height={36} />
                </PieChart>
            </ResponsiveContainer>
        </div>
    );
}

export function TypeBarChart({ data }: { data: Record<string, number> }) {
    const chartData = useMemo(() => {
        return Object.entries(data)
            .sort((a, b) => b[1] - a[1]) // specific order
            .slice(0, 10) // top 10
            .map(([name, value]) => ({ name, value }));
    }, [data]);

    return (
        <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 30 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" />
                    <YAxis type="category" dataKey="name" width={140} fontSize={12} interval={0} tick={{ fill: '#6b7280' }} />
                    <Tooltip
                        cursor={{ fill: 'transparent' }}
                        contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    />
                    <Bar dataKey="value" fill="#6366f1" radius={[0, 4, 4, 0]} barSize={20} />
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}
