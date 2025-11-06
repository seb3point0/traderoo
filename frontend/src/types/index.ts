// API Types matching backend models

export interface BotStatus {
  running: boolean;
  paused: boolean;
  paper_trading: boolean;
  exchange: string;
  active_strategies: number;
  strategies: StrategyInfo[];
}

export interface StrategyInfo {
  name: string;
  symbol: string;
  timeframe: string;
  ai_enabled?: boolean;
}

export interface Portfolio {
  initial_balance: number;
  current_balance: number;
  unrealized_pnl: number;
  realized_pnl: number;
  total_pnl: number;
  total_return_pct: number;
  open_positions: number;
  total_trades: number;
}

export interface Position {
  id: number;
  symbol: string;
  side: string;
  amount: number;
  entry_price: number;
  current_price?: number;
  unrealized_pnl: number;
  unrealized_pnl_percentage: number;
  stop_loss?: number;
  take_profit?: number;
  opened_at: string;
  closed_at?: string;
  is_open: boolean;
}

export interface Trade {
  id: number;
  symbol: string;
  side: string;
  order_type: string;
  amount: number;
  price: number;
  fee: number;
  realized_pnl?: number;
  status: string;
  strategy_name?: string;
  created_at: string;
  closed_at?: string;
}

export interface PerformanceMetrics {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl: number;
  total_fees: number;
  average_win: number;
  average_loss: number;
  profit_factor: number;
  sharpe_ratio: number;
  max_drawdown: number;
  max_drawdown_pct: number;
}

export interface DailyPnL {
  date: string;
  pnl: number;
}

export interface SymbolPerformance {
  symbol: string;
  trades: number;
  pnl: number;
  wins: number;
  win_rate: number;
}

export interface AvailableStrategy {
  name: string;
  description: string;
  default_params: Record<string, any>;
}

export interface StrategyState {
  id: number;
  strategy_name: string;
  symbol: string;
  exchange: string;
  timeframe: string;
  is_active: boolean;
  parameters: Record<string, any>;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  total_pnl: number;
  win_rate?: number;
}

export interface AIStats {
  strategy_name: string;
  symbol: string;
  ai_approvals: number;
  ai_rejections: number;
  approval_rate: number;
}

export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
  source?: string;
}

// Request types
export interface BotStartRequest {
  exchange: string;
  initial_balance: number;
}

export interface AddStrategyRequest {
  strategy_name: string;
  symbol: string;
  timeframe: string;
  params?: Record<string, any>;
  enable_ai_validation: boolean;
}

