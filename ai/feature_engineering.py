"""
Feature engineering for ML models
"""
import pandas as pd
import numpy as np
from typing import List, Optional
from app.utils.logger import log


class FeatureEngineer:
    """Feature engineering for ML trading models"""
    
    @staticmethod
    def create_price_features(df: pd.DataFrame) -> pd.DataFrame:
        """Create price-based features"""
        df = df.copy()
        
        # Returns
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # Price momentum
        df['momentum_5'] = df['close'] - df['close'].shift(5)
        df['momentum_10'] = df['close'] - df['close'].shift(10)
        df['momentum_20'] = df['close'] - df['close'].shift(20)
        
        # Price rate of change
        df['roc_5'] = (df['close'] - df['close'].shift(5)) / df['close'].shift(5) * 100
        df['roc_10'] = (df['close'] - df['close'].shift(10)) / df['close'].shift(10) * 100
        
        return df
    
    @staticmethod
    def create_volatility_features(df: pd.DataFrame) -> pd.DataFrame:
        """Create volatility-based features"""
        df = df.copy()
        
        # Historical volatility
        df['volatility_10'] = df['returns'].rolling(window=10).std()
        df['volatility_20'] = df['returns'].rolling(window=20).std()
        df['volatility_50'] = df['returns'].rolling(window=50).std()
        
        # Parkinson volatility (high-low)
        df['parkinson_vol'] = np.sqrt(
            (1 / (4 * np.log(2))) * 
            ((np.log(df['high'] / df['low'])) ** 2).rolling(window=20).mean()
        )
        
        return df
    
    @staticmethod
    def create_volume_features(df: pd.DataFrame) -> pd.DataFrame:
        """Create volume-based features"""
        df = df.copy()
        
        if 'volume' not in df.columns:
            return df
        
        # Volume changes
        df['volume_change'] = df['volume'].pct_change()
        df['volume_ratio_5'] = df['volume'] / df['volume'].rolling(window=5).mean()
        df['volume_ratio_20'] = df['volume'] / df['volume'].rolling(window=20).mean()
        
        # Volume momentum
        df['volume_momentum'] = df['volume'] - df['volume'].shift(5)
        
        return df
    
    @staticmethod
    def create_trend_features(df: pd.DataFrame) -> pd.DataFrame:
        """Create trend-based features"""
        df = df.copy()
        
        # Moving average distances
        if 'sma_20' in df.columns and 'sma_50' in df.columns:
            df['ma_distance_20_50'] = (df['sma_20'] - df['sma_50']) / df['sma_50'] * 100
        
        # Price vs MA
        if 'sma_20' in df.columns:
            df['price_vs_ma20'] = (df['close'] - df['sma_20']) / df['sma_20'] * 100
        
        # Trend strength
        df['trend_strength'] = df['close'].rolling(window=20).apply(
            lambda x: 1 if x.iloc[-1] > x.iloc[0] else -1,
            raw=False
        )
        
        return df
    
    @staticmethod
    def create_pattern_features(df: pd.DataFrame) -> pd.DataFrame:
        """Create pattern recognition features"""
        df = df.copy()
        
        # Candlestick patterns (simplified)
        df['body'] = df['close'] - df['open']
        df['upper_shadow'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['lower_shadow'] = df[['open', 'close']].min(axis=1) - df['low']
        
        # Doji detection
        df['is_doji'] = (abs(df['body']) / (df['high'] - df['low']) < 0.1).astype(int)
        
        # Engulfing patterns
        df['bullish_engulfing'] = (
            (df['body'] > 0) & 
            (df['body'].shift(1) < 0) & 
            (df['open'] < df['close'].shift(1)) & 
            (df['close'] > df['open'].shift(1))
        ).astype(int)
        
        df['bearish_engulfing'] = (
            (df['body'] < 0) & 
            (df['body'].shift(1) > 0) & 
            (df['open'] > df['close'].shift(1)) & 
            (df['close'] < df['open'].shift(1))
        ).astype(int)
        
        return df
    
    @staticmethod
    def create_time_features(df: pd.DataFrame) -> pd.DataFrame:
        """Create time-based features"""
        df = df.copy()
        
        if not isinstance(df.index, pd.DatetimeIndex):
            return df
        
        # Time components
        df['hour'] = df.index.hour
        df['day_of_week'] = df.index.dayofweek
        df['day_of_month'] = df.index.day
        df['month'] = df.index.month
        
        # Cyclic encoding
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        
        return df
    
    @staticmethod
    def create_all_features(df: pd.DataFrame) -> pd.DataFrame:
        """Create all features"""
        log.info("Creating ML features...")
        
        df = FeatureEngineer.create_price_features(df)
        df = FeatureEngineer.create_volatility_features(df)
        df = FeatureEngineer.create_volume_features(df)
        df = FeatureEngineer.create_trend_features(df)
        df = FeatureEngineer.create_pattern_features(df)
        df = FeatureEngineer.create_time_features(df)
        
        # Drop NaN values
        df = df.dropna()
        
        log.info(f"Created {len(df.columns)} features")
        
        return df
    
    @staticmethod
    def select_features(
        df: pd.DataFrame,
        target: str = 'returns',
        top_n: int = 20
    ) -> List[str]:
        """Select top N most important features using correlation"""
        if target not in df.columns:
            return []
        
        # Calculate correlation with target
        correlations = df.corr()[target].abs().sort_values(ascending=False)
        
        # Remove target itself and select top N
        top_features = correlations[1:top_n+1].index.tolist()
        
        log.info(f"Selected top {len(top_features)} features")
        
        return top_features

