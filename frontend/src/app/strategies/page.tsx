'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { AvailableStrategy, StrategyInfo } from '@/types';
import apiClient from '@/lib/api';
import { Plus, Trash2, Settings2, TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { toast } from 'sonner';

export default function StrategiesPage() {
  const [availableStrategies, setAvailableStrategies] = useState<AvailableStrategy[]>([]);
  const [activeStrategies, setActiveStrategies] = useState<StrategyInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  
  // Add strategy form state
  const [selectedStrategy, setSelectedStrategy] = useState('');
  const [symbol, setSymbol] = useState('BTC/USDT');
  const [timeframe, setTimeframe] = useState('1h');
  const [aiEnabled, setAiEnabled] = useState(true);
  const [adding, setAdding] = useState(false);

  const fetchData = async () => {
    try {
      const [available, status] = await Promise.all([
        apiClient.listStrategies(),
        apiClient.getBotStatus(),
      ]);

      setAvailableStrategies(available.strategies);
      setActiveStrategies(status.strategies || []);
    } catch (error) {
      console.error('Error fetching strategies:', error);
      toast.error('Failed to fetch strategies');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAddStrategy = async () => {
    if (!selectedStrategy || !symbol) {
      toast.error('Please select a strategy and enter a symbol');
      return;
    }

    setAdding(true);
    try {
      await apiClient.addStrategy({
        strategy_name: selectedStrategy,
        symbol: symbol,
        timeframe: timeframe,
        enable_ai_validation: aiEnabled,
      });

      toast.success('Strategy added successfully');
      setShowAddForm(false);
      setSelectedStrategy('');
      setSymbol('BTC/USDT');
      setTimeframe('1h');
      fetchData();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to add strategy');
    } finally {
      setAdding(false);
    }
  };

  const handleRemoveStrategy = async (strategyName: string, symbol: string) => {
    try {
      await apiClient.removeStrategy(strategyName, symbol);
      toast.success('Strategy removed successfully');
      fetchData();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to remove strategy');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-muted-foreground">Loading strategies...</div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Trading Strategies</h1>
          <p className="text-muted-foreground">
            Manage and configure trading strategies
          </p>
        </div>
        <Button onClick={() => setShowAddForm(!showAddForm)}>
          <Plus className="h-4 w-4 mr-2" />
          Add Strategy
        </Button>
      </div>

      {showAddForm && (
        <Card className="border-primary">
          <CardHeader>
            <CardTitle>Add New Strategy</CardTitle>
            <CardDescription>Configure and add a trading strategy</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4">
              <div className="grid gap-2">
                <label className="text-sm font-medium">Strategy Type</label>
                <Select
                  value={selectedStrategy}
                  onChange={(e) => setSelectedStrategy(e.target.value)}
                >
                  <option value="">Select a strategy...</option>
                  {availableStrategies.map((strategy) => (
                    <option key={strategy.name} value={strategy.name}>
                      {strategy.name}
                    </option>
                  ))}
                </Select>
                {selectedStrategy && (
                  <p className="text-xs text-muted-foreground">
                    {availableStrategies.find(s => s.name === selectedStrategy)?.description}
                  </p>
                )}
              </div>

              <div className="grid gap-2">
                <label className="text-sm font-medium">Symbol</label>
                <Input
                  placeholder="BTC/USDT"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                />
              </div>

              <div className="grid gap-2">
                <label className="text-sm font-medium">Timeframe</label>
                <Select value={timeframe} onChange={(e) => setTimeframe(e.target.value)}>
                  <option value="1m">1 minute</option>
                  <option value="5m">5 minutes</option>
                  <option value="15m">15 minutes</option>
                  <option value="1h">1 hour</option>
                  <option value="4h">4 hours</option>
                  <option value="1d">1 day</option>
                </Select>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <label className="text-sm font-medium">AI Validation</label>
                  <p className="text-xs text-muted-foreground">
                    Use AI to validate trading signals
                  </p>
                </div>
                <Switch
                  checked={aiEnabled}
                  onCheckedChange={setAiEnabled}
                />
              </div>

              <div className="flex gap-2">
                <Button onClick={handleAddStrategy} disabled={adding} className="flex-1">
                  {adding ? 'Adding...' : 'Add Strategy'}
                </Button>
                <Button variant="outline" onClick={() => setShowAddForm(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Active Strategies</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold flex items-center">
              <Activity className="h-6 w-6 mr-2 text-primary" />
              {activeStrategies.length}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Available Strategies</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold flex items-center">
              <Settings2 className="h-6 w-6 mr-2 text-primary" />
              {availableStrategies.length}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>AI Enabled</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold flex items-center text-green-500">
              <TrendingUp className="h-6 w-6 mr-2" />
              {activeStrategies.filter(s => s.ai_enabled).length}
            </div>
          </CardContent>
        </Card>
      </div>

      <div>
        <h2 className="text-xl font-semibold mb-4">Active Strategies</h2>
        {activeStrategies.length === 0 ? (
          <Card>
            <CardContent className="py-12">
              <div className="text-center text-muted-foreground">
                <Settings2 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No active strategies</p>
                <p className="text-sm">Add a strategy to start trading</p>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {activeStrategies.map((strategy, index) => (
              <Card key={`${strategy.name}-${strategy.symbol}-${index}`}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <CardTitle className="text-lg">{strategy.name}</CardTitle>
                      <CardDescription>{strategy.symbol}</CardDescription>
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleRemoveStrategy(strategy.name, strategy.symbol)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Timeframe</span>
                      <Badge variant="secondary">{strategy.timeframe}</Badge>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">AI Validation</span>
                      <Badge variant={strategy.ai_enabled ? 'success' : 'secondary'}>
                        {strategy.ai_enabled ? 'Enabled' : 'Disabled'}
                      </Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      <div>
        <h2 className="text-xl font-semibold mb-4">Available Strategies</h2>
        <div className="grid gap-4 md:grid-cols-2">
          {availableStrategies.map((strategy) => (
            <Card key={strategy.name}>
              <CardHeader>
                <CardTitle className="text-lg">{strategy.name}</CardTitle>
                <CardDescription>{strategy.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="text-sm font-medium">Default Parameters:</div>
                  <div className="grid gap-1 text-sm text-muted-foreground">
                    {Object.entries(strategy.default_params).map(([key, value]) => (
                      <div key={key} className="flex justify-between">
                        <span>{key}:</span>
                        <span>{String(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}

