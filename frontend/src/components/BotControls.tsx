'use client';

import { useState } from 'react';
import { Play, Square, Pause, PlayCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { BotStatus } from '@/types';
import apiClient from '@/lib/api';
import { toast } from 'sonner';

interface BotControlsProps {
  status: BotStatus | null;
  onStatusChange: () => void;
}

export function BotControls({ status, onStatusChange }: BotControlsProps) {
  const [isLoading, setIsLoading] = useState(false);

  const handleStart = async () => {
    setIsLoading(true);
    try {
      await apiClient.startBot({
        exchange: 'binance',
        initial_balance: 10000,
      });
      toast.success('Bot started successfully');
      onStatusChange();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to start bot');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStop = async () => {
    setIsLoading(true);
    try {
      await apiClient.stopBot();
      toast.success('Bot stopped successfully');
      onStatusChange();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to stop bot');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePause = async () => {
    setIsLoading(true);
    try {
      await apiClient.pauseBot();
      toast.success('Bot paused');
      onStatusChange();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to pause bot');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResume = async () => {
    setIsLoading(true);
    try {
      await apiClient.resumeBot();
      toast.success('Bot resumed');
      onStatusChange();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to resume bot');
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusBadge = () => {
    if (!status) return <Badge variant="secondary">Unknown</Badge>;
    if (status.running && !status.paused) return <Badge variant="success">Running</Badge>;
    if (status.paused) return <Badge variant="warning">Paused</Badge>;
    return <Badge variant="secondary">Stopped</Badge>;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Bot Control</CardTitle>
        <CardDescription>Start, stop, or pause the trading bot</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium mb-1">Status</div>
              {getStatusBadge()}
            </div>
            <div className="text-right">
              <div className="text-sm font-medium mb-1">Exchange</div>
              <div className="text-sm text-muted-foreground">
                {status?.exchange || 'N/A'}
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium mb-1">Mode</div>
              <Badge variant={status?.paper_trading ? 'secondary' : 'destructive'}>
                {status?.paper_trading ? 'Paper Trading' : 'Live Trading'}
              </Badge>
            </div>
            <div className="text-right">
              <div className="text-sm font-medium mb-1">Active Strategies</div>
              <div className="text-sm text-muted-foreground">
                {status?.active_strategies || 0}
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            {!status?.running ? (
              <Button onClick={handleStart} disabled={isLoading} className="flex-1">
                <Play className="mr-2 h-4 w-4" />
                Start Bot
              </Button>
            ) : (
              <>
                {status.paused ? (
                  <Button onClick={handleResume} disabled={isLoading} className="flex-1">
                    <PlayCircle className="mr-2 h-4 w-4" />
                    Resume
                  </Button>
                ) : (
                  <Button onClick={handlePause} disabled={isLoading} variant="secondary" className="flex-1">
                    <Pause className="mr-2 h-4 w-4" />
                    Pause
                  </Button>
                )}
                <Button onClick={handleStop} disabled={isLoading} variant="destructive" className="flex-1">
                  <Square className="mr-2 h-4 w-4" />
                  Stop
                </Button>
              </>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

