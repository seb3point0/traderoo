"""
Technical indicators wrapper using TA-Lib and pandas-ta
"""
import pandas as pd
import numpy as np
from typing import Optional, Tuple
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    import pandas_ta as ta

from app.utils.logger import log


class TechnicalIndicators:
    """Technical indicators calculator"""
    
    @staticmethod
    def calculate_sma(data: pd.Series, period: int = 20) -> pd.Series:
        """Simple Moving Average"""
        if TALIB_AVAILABLE:
            return pd.Series(talib.SMA(data.values, timeperiod=period), index=data.index)
        else:
            return data.rolling(window=period).mean()
    
    @staticmethod
    def calculate_ema(data: pd.Series, period: int = 20) -> pd.Series:
        """Exponential Moving Average"""
        if TALIB_AVAILABLE:
            return pd.Series(talib.EMA(data.values, timeperiod=period), index=data.index)
        else:
            return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        if TALIB_AVAILABLE:
            return pd.Series(talib.RSI(data.values, timeperiod=period), index=data.index)
        else:
            delta = data.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))
    
    @staticmethod
    def calculate_macd(
        data: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD, Signal, and Histogram"""
        if TALIB_AVAILABLE:
            macd, signal_line, hist = talib.MACD(
                data.values,
                fastperiod=fast,
                slowperiod=slow,
                signalperiod=signal
            )
            return (
                pd.Series(macd, index=data.index),
                pd.Series(signal_line, index=data.index),
                pd.Series(hist, index=data.index)
            )
        else:
            exp1 = data.ewm(span=fast, adjust=False).mean()
            exp2 = data.ewm(span=slow, adjust=False).mean()
            macd = exp1 - exp2
            signal_line = macd.ewm(span=signal, adjust=False).mean()
            hist = macd - signal_line
            return macd, signal_line, hist
    
    @staticmethod
    def calculate_bollinger_bands(
        data: pd.Series,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bollinger Bands (upper, middle, lower)"""
        if TALIB_AVAILABLE:
            upper, middle, lower = talib.BBANDS(
                data.values,
                timeperiod=period,
                nbdevup=std_dev,
                nbdevdn=std_dev
            )
            return (
                pd.Series(upper, index=data.index),
                pd.Series(middle, index=data.index),
                pd.Series(lower, index=data.index)
            )
        else:
            middle = data.rolling(window=period).mean()
            std = data.rolling(window=period).std()
            upper = middle + (std * std_dev)
            lower = middle - (std * std_dev)
            return upper, middle, lower
    
    @staticmethod
    def calculate_atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """Average True Range"""
        if TALIB_AVAILABLE:
            return pd.Series(
                talib.ATR(high.values, low.values, close.values, timeperiod=period),
                index=close.index
            )
        else:
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            return tr.rolling(window=period).mean()
    
    @staticmethod
    def calculate_stochastic(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        k_period: int = 14,
        d_period: int = 3
    ) -> Tuple[pd.Series, pd.Series]:
        """Stochastic Oscillator (%K and %D)"""
        if TALIB_AVAILABLE:
            slowk, slowd = talib.STOCH(
                high.values,
                low.values,
                close.values,
                fastk_period=k_period,
                slowk_period=d_period,
                slowd_period=d_period
            )
            return (
                pd.Series(slowk, index=close.index),
                pd.Series(slowd, index=close.index)
            )
        else:
            lowest_low = low.rolling(window=k_period).min()
            highest_high = high.rolling(window=k_period).max()
            k = 100 * ((close - lowest_low) / (highest_high - lowest_low))
            d = k.rolling(window=d_period).mean()
            return k, d
    
    @staticmethod
    def calculate_adx(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """Average Directional Index"""
        if TALIB_AVAILABLE:
            return pd.Series(
                talib.ADX(high.values, low.values, close.values, timeperiod=period),
                index=close.index
            )
        else:
            # Simplified ADX calculation
            plus_dm = high.diff()
            minus_dm = -low.diff()
            
            plus_dm[plus_dm < 0] = 0
            minus_dm[minus_dm < 0] = 0
            
            tr = TechnicalIndicators.calculate_atr(high, low, close, period)
            
            plus_di = 100 * (plus_dm.rolling(window=period).mean() / tr)
            minus_di = 100 * (minus_dm.rolling(window=period).mean() / tr)
            
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            adx = dx.rolling(window=period).mean()
            
            return adx
    
    @staticmethod
    def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """On-Balance Volume"""
        if TALIB_AVAILABLE:
            return pd.Series(
                talib.OBV(close.values, volume.values),
                index=close.index
            )
        else:
            obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
            return obv
    
    @staticmethod
    def calculate_vwap(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series
    ) -> pd.Series:
        """Volume Weighted Average Price"""
        typical_price = (high + low + close) / 3
        return (typical_price * volume).cumsum() / volume.cumsum()
    
    @staticmethod
    def detect_crossover(fast: pd.Series, slow: pd.Series) -> pd.Series:
        """Detect bullish crossover (fast crosses above slow)"""
        return (fast > slow) & (fast.shift(1) <= slow.shift(1))
    
    @staticmethod
    def detect_crossunder(fast: pd.Series, slow: pd.Series) -> pd.Series:
        """Detect bearish crossunder (fast crosses below slow)"""
        return (fast < slow) & (fast.shift(1) >= slow.shift(1))
    
    @staticmethod
    def calculate_support_resistance(
        data: pd.Series,
        window: int = 20
    ) -> Tuple[float, float]:
        """Calculate support and resistance levels"""
        recent_data = data.tail(window)
        support = recent_data.min()
        resistance = recent_data.max()
        return support, resistance
    
    @staticmethod
    def detect_bullish_divergence(price: pd.Series, indicator: pd.Series) -> bool:
        """Detect bullish divergence (price lower low, indicator higher low)"""
        if len(price) < 2 or len(indicator) < 2:
            return False
        
        price_ll = price.iloc[-1] < price.iloc[-2]
        indicator_hl = indicator.iloc[-1] > indicator.iloc[-2]
        
        return price_ll and indicator_hl
    
    @staticmethod
    def detect_bearish_divergence(price: pd.Series, indicator: pd.Series) -> bool:
        """Detect bearish divergence (price higher high, indicator lower high)"""
        if len(price) < 2 or len(indicator) < 2:
            return False
        
        price_hh = price.iloc[-1] > price.iloc[-2]
        indicator_lh = indicator.iloc[-1] < indicator.iloc[-2]
        
        return price_hh and indicator_lh
    
    @staticmethod
    def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Add all common indicators to a dataframe with OHLCV data"""
        if df.empty:
            return df
        
        df = df.copy()
        
        # Moving averages
        df['sma_20'] = TechnicalIndicators.calculate_sma(df['close'], 20)
        df['sma_50'] = TechnicalIndicators.calculate_sma(df['close'], 50)
        df['ema_12'] = TechnicalIndicators.calculate_ema(df['close'], 12)
        df['ema_26'] = TechnicalIndicators.calculate_ema(df['close'], 26)
        
        # RSI
        df['rsi'] = TechnicalIndicators.calculate_rsi(df['close'], 14)
        
        # MACD
        df['macd'], df['macd_signal'], df['macd_hist'] = TechnicalIndicators.calculate_macd(df['close'])
        
        # Bollinger Bands
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = TechnicalIndicators.calculate_bollinger_bands(df['close'])
        
        # ATR
        df['atr'] = TechnicalIndicators.calculate_atr(df['high'], df['low'], df['close'])
        
        # Stochastic
        df['stoch_k'], df['stoch_d'] = TechnicalIndicators.calculate_stochastic(
            df['high'], df['low'], df['close']
        )
        
        # ADX
        df['adx'] = TechnicalIndicators.calculate_adx(df['high'], df['low'], df['close'])
        
        # Volume indicators
        if 'volume' in df.columns:
            df['obv'] = TechnicalIndicators.calculate_obv(df['close'], df['volume'])
            df['vwap'] = TechnicalIndicators.calculate_vwap(
                df['high'], df['low'], df['close'], df['volume']
            )
        
        log.debug(f"Added all indicators to dataframe ({len(df)} rows)")
        
        return df

