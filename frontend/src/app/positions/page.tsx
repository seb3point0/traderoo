'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Position } from '@/types';
import apiClient from '@/lib/api';
import { formatCurrency, formatPercentage, formatDate, formatDuration } from '@/lib/utils';
import { useWebSocket } from '@/hooks/useWebSocket';
import { X, TrendingUp, TrendingDown, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

export default function PositionsPage() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);
  const [closingId, setClosingId] = useState<number | null>(null);
  const { subscribe } = useWebSocket();

  const fetchPositions = async () => {
    try {
      const data = await apiClient.getPositions(true);
      setPositions(data.positions);
    } catch (error) {
      console.error('Error fetching positions:', error);
      toast.error('Failed to fetch positions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPositions();

    // Refresh every 10 seconds
    const interval = setInterval(fetchPositions, 10000);
    return () => clearInterval(interval);
  }, []);

  // Subscribe to WebSocket events for real-time updates
  useEffect(() => {
    const unsubscribe = subscribe('all', (message) => {
      if (
        message.type === 'POSITION_OPENED' ||
        message.type === 'POSITION_CLOSED' ||
        message.type === 'POSITION_UPDATED' ||
        message.type === 'ORDER_FILLED'
      ) {
        fetchPositions();
      }
    });

    return unsubscribe;
  }, [subscribe]);

  const handleClosePosition = async (positionId: number) => {
    setClosingId(positionId);
    try {
      await apiClient.closePosition(positionId);
      toast.success('Position closed successfully');
      fetchPositions();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to close position');
    } finally {
      setClosingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-muted-foreground">Loading positions...</div>
      </div>
    );
  }

  const totalUnrealizedPnL = positions.reduce((sum, p) => sum + p.unrealized_pnl, 0);

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Open Positions</h1>
          <p className="text-muted-foreground">
            {positions.length} active position{positions.length !== 1 ? 's' : ''}
          </p>
        </div>
        <Button onClick={fetchPositions} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Unrealized P&L</CardDescription>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${
              totalUnrealizedPnL >= 0 ? 'text-green-500' : 'text-red-500'
            }`}>
              {formatCurrency(totalUnrealizedPnL)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Winning Positions</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold flex items-center text-green-500">
              <TrendingUp className="h-6 w-6 mr-2" />
              {positions.filter(p => p.unrealized_pnl > 0).length}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Losing Positions</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold flex items-center text-red-500">
              <TrendingDown className="h-6 w-6 mr-2" />
              {positions.filter(p => p.unrealized_pnl < 0).length}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Active Positions</CardTitle>
          <CardDescription>Real-time position monitoring</CardDescription>
        </CardHeader>
        <CardContent>
          {positions.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              No open positions
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Symbol</TableHead>
                  <TableHead>Side</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead className="text-right">Entry Price</TableHead>
                  <TableHead className="text-right">Current Price</TableHead>
                  <TableHead className="text-right">Unrealized P&L</TableHead>
                  <TableHead className="text-right">P&L %</TableHead>
                  <TableHead className="text-right">Stop Loss</TableHead>
                  <TableHead className="text-right">Take Profit</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {positions.map((position) => (
                  <TableRow key={position.id}>
                    <TableCell className="font-medium">{position.symbol}</TableCell>
                    <TableCell>
                      <Badge variant={position.side === 'buy' ? 'success' : 'destructive'}>
                        {position.side.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">{position.amount.toFixed(6)}</TableCell>
                    <TableCell className="text-right">
                      {formatCurrency(position.entry_price)}
                    </TableCell>
                    <TableCell className="text-right">
                      {position.current_price ? formatCurrency(position.current_price) : 'N/A'}
                    </TableCell>
                    <TableCell className={`text-right font-semibold ${
                      position.unrealized_pnl >= 0 ? 'text-green-500' : 'text-red-500'
                    }`}>
                      {formatCurrency(position.unrealized_pnl)}
                    </TableCell>
                    <TableCell className={`text-right ${
                      position.unrealized_pnl_percentage >= 0 ? 'text-green-500' : 'text-red-500'
                    }`}>
                      {formatPercentage(position.unrealized_pnl_percentage)}
                    </TableCell>
                    <TableCell className="text-right">
                      {position.stop_loss ? formatCurrency(position.stop_loss) : '-'}
                    </TableCell>
                    <TableCell className="text-right">
                      {position.take_profit ? formatCurrency(position.take_profit) : '-'}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDuration(position.opened_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => handleClosePosition(position.id)}
                        disabled={closingId === position.id}
                      >
                        <X className="h-4 w-4 mr-1" />
                        Close
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

