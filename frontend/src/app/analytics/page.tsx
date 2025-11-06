'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { PerformanceMetrics, SymbolPerformance, AIStats } from '@/types';
import apiClient from '@/lib/api';
import { formatCurrency, formatPercentage } from '@/lib/utils';
import {
  TrendingUp,
  TrendingDown,
  Target,
  DollarSign,
  Percent,
  Activity,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Brain,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';

export default function AnalyticsPage() {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [symbolPerf, setSymbolPerf] = useState<SymbolPerformance[]>([]);
  const [aiStats, setAiStats] = useState<AIStats[]>([]);
  const [aiEnabled, setAiEnabled] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [metricsData, symbolData] = await Promise.all([
        apiClient.getPerformanceMetrics(30),
        apiClient.getSymbolPerformance(10),
      ]);

      setMetrics(metricsData);
      setSymbolPerf(symbolData.symbols);

      // Try to fetch AI stats
      try {
        const aiData = await apiClient.getAIStats();
        if (aiData.ai_enabled_strategies > 0) {
          setAiStats(aiData.strategies);
          setAiEnabled(true);
        }
      } catch (error) {
        // AI stats not available
        setAiEnabled(false);
      }
    } catch (error) {
      console.error('Error fetching analytics:', error);
      toast.error('Failed to fetch analytics data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();

    // Refresh every 60 seconds
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-muted-foreground">Loading analytics...</div>
      </div>
    );
  }

  const winLossData = [
    { name: 'Winning', value: metrics?.winning_trades || 0, color: '#22c55e' },
    { name: 'Losing', value: metrics?.losing_trades || 0, color: '#ef4444' },
  ];

  const symbolChartData = symbolPerf.slice(0, 5).map(s => ({
    symbol: s.symbol,
    pnl: s.pnl,
  }));

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Performance Analytics</h1>
        <p className="text-muted-foreground">
          Comprehensive trading performance metrics
        </p>
      </div>

      {/* Key Metrics */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Trades</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold flex items-center">
              <Target className="h-6 w-6 mr-2 text-primary" />
              {metrics?.total_trades || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Last 30 days
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Win Rate</CardDescription>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold flex items-center ${
              (metrics?.win_rate || 0) >= 50 ? 'text-green-500' : 'text-red-500'
            }`}>
              <Percent className="h-6 w-6 mr-2" />
              {metrics?.win_rate.toFixed(1) || 0}%
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {metrics?.winning_trades || 0}W / {metrics?.losing_trades || 0}L
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Profit Factor</CardDescription>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold flex items-center ${
              (metrics?.profit_factor || 0) >= 1 ? 'text-green-500' : 'text-red-500'
            }`}>
              <Activity className="h-6 w-6 mr-2" />
              {metrics?.profit_factor.toFixed(2) || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Gross profit / Gross loss
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total P&L</CardDescription>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold flex items-center ${
              (metrics?.total_pnl || 0) >= 0 ? 'text-green-500' : 'text-red-500'
            }`}>
              <DollarSign className="h-6 w-6 mr-2" />
              {formatCurrency(metrics?.total_pnl || 0)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Fees: {formatCurrency(metrics?.total_fees || 0)}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Advanced Metrics */}
      <Card>
        <CardHeader>
          <CardTitle>Advanced Metrics</CardTitle>
          <CardDescription>Risk-adjusted performance indicators</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-1">
                Average Win
              </div>
              <div className="text-lg font-bold text-green-500">
                {formatCurrency(metrics?.average_win || 0)}
              </div>
            </div>
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-1">
                Average Loss
              </div>
              <div className="text-lg font-bold text-red-500">
                {formatCurrency(metrics?.average_loss || 0)}
              </div>
            </div>
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-1">
                Sharpe Ratio
              </div>
              <div className={`text-lg font-bold ${
                (metrics?.sharpe_ratio || 0) >= 1 ? 'text-green-500' : 'text-yellow-500'
              }`}>
                {metrics?.sharpe_ratio.toFixed(2) || 0}
              </div>
            </div>
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-1">
                Max Drawdown
              </div>
              <div className="text-lg font-bold text-red-500">
                {formatCurrency(metrics?.max_drawdown || 0)} ({metrics?.max_drawdown_pct.toFixed(2) || 0}%)
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Charts */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Win/Loss Distribution</CardTitle>
            <CardDescription>Trade outcome breakdown</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={winLossData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name}: ${value}`}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {winLossData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top Symbols by P&L</CardTitle>
            <CardDescription>Best performing trading pairs</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={symbolChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2235" />
                <XAxis dataKey="symbol" stroke="#d1d4dc" />
                <YAxis stroke="#d1d4dc" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0a0e27', border: '1px solid #1e2235' }}
                  formatter={(value: any) => formatCurrency(value)}
                />
                <Bar dataKey="pnl" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Symbol Performance Table */}
      <Card>
        <CardHeader>
          <CardTitle>Symbol Performance</CardTitle>
          <CardDescription>Detailed performance by trading pair</CardDescription>
        </CardHeader>
        <CardContent>
          {symbolPerf.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              No performance data available
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Symbol</TableHead>
                  <TableHead className="text-right">Trades</TableHead>
                  <TableHead className="text-right">Wins</TableHead>
                  <TableHead className="text-right">Win Rate</TableHead>
                  <TableHead className="text-right">Total P&L</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {symbolPerf.map((symbol) => (
                  <TableRow key={symbol.symbol}>
                    <TableCell className="font-medium">{symbol.symbol}</TableCell>
                    <TableCell className="text-right">{symbol.trades}</TableCell>
                    <TableCell className="text-right">{symbol.wins}</TableCell>
                    <TableCell className="text-right">
                      <Badge variant={symbol.win_rate >= 50 ? 'success' : 'secondary'}>
                        {symbol.win_rate.toFixed(1)}%
                      </Badge>
                    </TableCell>
                    <TableCell className={`text-right font-semibold ${
                      symbol.pnl >= 0 ? 'text-green-500' : 'text-red-500'
                    }`}>
                      {formatCurrency(symbol.pnl)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* AI Insights */}
      {aiEnabled && aiStats.length > 0 && (
        <Card className="border-primary/50">
          <CardHeader>
            <CardTitle className="flex items-center">
              <Brain className="h-5 w-5 mr-2 text-primary" />
              AI Validation Statistics
            </CardTitle>
            <CardDescription>
              AI-powered signal validation performance
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {aiStats.map((stat) => (
                <Card key={`${stat.strategy_name}-${stat.symbol}`}>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">{stat.strategy_name}</CardTitle>
                    <CardDescription>{stat.symbol}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="flex items-center text-green-500">
                        <CheckCircle className="h-4 w-4 mr-1" />
                        Approvals
                      </span>
                      <span className="font-semibold">{stat.ai_approvals}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="flex items-center text-red-500">
                        <XCircle className="h-4 w-4 mr-1" />
                        Rejections
                      </span>
                      <span className="font-semibold">{stat.ai_rejections}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm pt-2 border-t">
                      <span className="text-muted-foreground">Approval Rate</span>
                      <Badge variant={stat.approval_rate >= 50 ? 'success' : 'warning'}>
                        {stat.approval_rate.toFixed(1)}%
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

