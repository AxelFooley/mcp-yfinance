---
wave: 1
depends_on: []
files_modified:
  - server.py
  - tests/test_technical.py
autonomous: true
requirements:
  - TECH-01
  - TECH-02
  - TECH-03
  - TECH-04
  - TECH-05
  - TECH-06
---

# Plan 4.1: Technical Indicator Calculations

**Phase:** 4 - Analysis
**Wave:** 1 (autonomous)
**Goal:** Implement technical analysis indicators for stock price data

---

## Overview

This plan implements technical analysis indicators commonly used in financial trading: RSI (Relative Strength Index), MACD (Moving Average Convergence Divergence), Bollinger Bands, ATR (Average True Range), moving averages (SMA/EMA), and support/resistance levels. All indicators are calculated from historical price data using pandas operations.

**Success Criteria:**
- `get_technical_analysis` returns all 6 technical indicators
- RSI correctly identifies overbought (>70) and oversold (<30) conditions
- MACD includes histogram and crossover detection
- Bollinger Bands include bandwidth and percent-B metrics
- ATR measures volatility using 14-period calculation
- Support/resistance identified from recent price action
- Unit tests cover all indicators with 80%+ coverage

---

## Tasks

<tasks>
<task id="04-01-01">
<summary>Implement technical indicator calculation functions</summary>
<details>
Add indicator calculation functions to server.py (helper functions, not MCP tools):

```python
def _compute_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index (RSI)."""
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def _compute_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """Calculate MACD (Moving Average Convergence Divergence)."""
    exp1 = df["Close"].ewm(span=fast, adjust=False).mean()
    exp2 = df["Close"].ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=signal, adjust=False).mean()
    histogram = macd - signal
    
    # Crossover detection
    crossover = "none"
    if len(macd) >= 2:
        if macd.iloc[-2] <= signal.iloc[-2] and macd.iloc[-1] > signal.iloc[-1]:
            crossover = "bullish"
        elif macd.iloc[-2] >= signal.iloc[-2] and macd.iloc[-1] < signal.iloc[-1]:
            crossover = "bearish"
    
    return {
        "macd": _series_to_dict(macd),
        "signal": _series_to_dict(signal),
        "histogram": _series_to_dict(histogram),
        "crossover": crossover,
    }

def _compute_bollinger(df: pd.DataFrame, period: int = 20, std_dev: float = 2) -> dict:
    """Calculate Bollinger Bands."""
    sma = df["Close"].rolling(window=period).mean()
    std = df["Close"].rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    
    # Bandwidth and percent-B
    bandwidth = ((upper - lower) / sma * 100)
    percent_b = (df["Close"] - lower) / (upper - lower)
    
    return {
        "upper": _series_to_dict(upper),
        "middle": _series_to_dict(sma),
        "lower": _series_to_dict(lower),
        "bandwidth": _series_to_dict(bandwidth),
        "percent_b": _series_to_dict(percent_b),
    }

def _compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range (ATR)."""
    high = df["High"]
    low = df["Low"]
    close = df["Close"].shift(1)
    
    tr1 = high - low
    tr2 = (high - close).abs()
    tr3 = (low - close).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

def _compute_support_resistance(df: pd.DataFrame, lookback: int = 20) -> dict:
    """Calculate support and resistance levels from recent price action."""
    recent = df.tail(lookback)
    support = recent["Low"].min()
    resistance = recent["High"].max()
    
    return {
        "support": _safe(support),
        "resistance": _safe(resistance),
        "range": _safe(resistance - support),
    }
```

Requirements: TECH-01, TECH-02, TECH-03, TECH-04, TECH-05, TECH-06
Location: Add after get_market_overview tool, before get_technical_analysis
</details>
<verify>
<automated>pytest tests/test_technical.py::test_indicator_calculations -v</automated>
</verify>
</task>

<task id="04-01-02">
<summary>Implement get_technical_analysis tool</summary>
<details>
Add the get_technical_analysis MCP tool to server.py:

```python
@mcp.tool()
@cached(ttl=300)
def get_technical_analysis(symbol: str, period: str = "3mo", interval: str = "1d") -> dict | str:
    """
    Get technical analysis indicators for a stock symbol.
    
    Args:
        symbol: Stock ticker symbol
        period: Time period for historical data (default: "3mo")
        interval: Data interval (default: "1d")
    
    Returns:
        Dictionary with RSI, MACD, Bollinger Bands, ATR, moving averages,
        and support/resistance levels.
    """
    try:
        ticker = _ticker(symbol.upper())
        df = ticker.history(period=period, interval=interval)
        
        if df.empty or len(df) < 50:
            return {"error": f"Insufficient data for technical analysis on '{symbol}'"}
        
        # Normalize column names
        df.columns = [str(c).split()[-1] for c in df.columns]
        
        # Calculate all indicators
        rsi = _compute_rsi(df)
        macd = _compute_macd(df)
        bollinger = _compute_bollinger(df)
        atr = _compute_atr(df)
        sr = _compute_support_resistance(df)
        
        # Moving averages
        sma_20 = df["Close"].rolling(window=20).mean().iloc[-1]
        sma_50 = df["Close"].rolling(window=50).mean().iloc[-1]
        sma_200 = df["Close"].rolling(window=200).mean().iloc[-1]
        ema_12 = df["Close"].ewm(span=12).mean().iloc[-1]
        ema_26 = df["Close"].ewm(span=26).mean().iloc[-1]
        
        current_price = df["Close"].iloc[-1]
        current_rsi = rsi.iloc[-1]
        
        # RSI signal
        rsi_signal = "neutral"
        if current_rsi > 70:
            rsi_signal = "overbought"
        elif current_rsi < 30:
            rsi_signal = "oversold"
        
        return {
            "symbol": symbol.upper(),
            "currentPrice": _safe(current_price),
            "rsi": {
                "value": _safe(current_rsi),
                "signal": rsi_signal,
                "overbought": current_rsi > 70,
                "oversold": current_rsi < 30,
            },
            "macd": {
                "value": _safe(macd["macd"].get(str(df.index[-1])) if isinstance(macd["macd"], dict) else macd["macd"].iloc[-1]),
                "signal": _safe(macd["signal"].get(str(df.index[-1])) if isinstance(macd["signal"], dict) else macd["signal"].iloc[-1]),
                "histogram": _safe(macd["histogram"].get(str(df.index[-1])) if isinstance(macd["histogram"], dict) else macd["histogram"].iloc[-1]),
                "crossover": macd["crossover"],
            },
            "bollinger": {
                "upper": _safe(bollinger["upper"].get(str(df.index[-1])) if isinstance(bollinger["upper"], dict) else bollinger["upper"].iloc[-1]),
                "middle": _safe(bollinger["middle"].get(str(df.index[-1])) if isinstance(bollinger["middle"], dict) else bollinger["middle"].iloc[-1]),
                "lower": _safe(bollinger["lower"].get(str(df.index[-1])) if isinstance(bollinger["lower"], dict) else bollinger["lower"].iloc[-1]),
                "bandwidth": _safe(bollinger["bandwidth"].get(str(df.index[-1])) if isinstance(bollinger["bandwidth"], dict) else bollinger["bandwidth"].iloc[-1]),
                "percent_b": _safe(bollinger["percent_b"].get(str(df.index[-1])) if isinstance(bollinger["percent_b"], dict) else bollinger["percent_b"].iloc[-1]),
            },
            "atr": _safe(atr.iloc[-1]),
            "supportResistance": sr,
            "movingAverages": {
                "sma20": _safe(sma_20),
                "sma50": _safe(sma_50),
                "sma200": _safe(sma_200),
                "ema12": _safe(ema_12),
                "ema26": _safe(ema_26),
            },
            "trend": {
                "priceVsSma20": current_price > sma_20 if pd.notna(sma_20) else None,
                "sma20VsSma50": sma_20 > sma_50 if pd.notna(sma_20) and pd.notna(sma_50) else None,
            },
        }
    except Exception as e:
        logger.error(f"Failed to compute technical analysis for '{symbol}': {e}", exc_info=True)
        return {"error": f"Failed to compute technical analysis for '{symbol}': {str(e)}"}
```

Requirements: TECH-01 through TECH-06
Location: Add after indicator helper functions
</details>
<verify>
<automated>pytest tests/test_technical.py::test_get_technical_analysis -v</automated>
</verify>
</task>

<task id="04-01-03">
<summary>Add unit tests for technical indicators</summary>
<details>
Create tests/test_technical.py with comprehensive tests:

1. **test_compute_rsi()**
   - Mock price data with uptrend
   - Verify RSI > 50 for uptrend
   - Verify overbought > 70, oversold < 30

2. **test_compute_macd()**
   - Mock price data
   - Verify macd, signal, histogram returned
   - Test bullish crossover detection
   - Test bearish crossover detection

3. **test_compute_bollinger()**
   - Mock price data
   - Verify upper > middle > lower
   - Verify bandwidth calculated
   - Verify percent-b between 0-1

4. **test_compute_atr()**
   - Mock high/low/close data
   - Verify ATR > 0
   - Verify increases with volatility

5. **test_compute_support_resistance()**
   - Mock price data with known high/low
   - Verify support <= resistance
   - Verify range calculated

6. **test_get_technical_analysis_valid()**
   - Mock ticker.history with OHLCV data
   - Verify all indicators returned
   - Verify RSI signal detection
   - Verify trend analysis

7. **test_get_technical_analysis_insufficient_data()**
   - Mock empty or small DataFrame
   - Verify returns error

8. **test_rsi_overbought_oversold()**
   - Mock data with RSI > 70
   - Verify signal = "overbought"
   - Mock data with RSI < 30
   - Verify signal = "oversold"

Use unittest.mock.patch for all yfinance mocking.
</details>
<verify>
<automated>pytest tests/test_technical.py -v --cov=server --cov-report=term-missing</automated>
</verify>
</task>
</tasks>

---

## Must Haves

After completing this plan:

- [ ] server.py has _compute_rsi(), _compute_macd(), _compute_bollinger(), _compute_atr(), _compute_support_resistance() helpers
- [ ] server.py has get_technical_analysis() tool with @cached(ttl=300)
- [ ] RSI correctly identifies overbought (>70) and oversold (<30) conditions
- [ ] MACD includes crossover detection (bullish/bearish/none)
- [ ] Bollinger Bands include bandwidth and percent-B metrics
- [ ] ATR calculated using 14-period default
- [ ] Support/resistance from recent price action
- [ ] Moving averages (SMA 20/50/200, EMA 12/26) included
- [ ] tests/test_technical.py has 8+ test cases
- [ ] All tests pass: pytest tests/test_technical.py -v
- [ ] Coverage >= 80%: pytest --cov=server --cov-report=term-missing

---

## Verification

Run after plan completion:
```bash
# Lint
ruff check .
ruff format --check .

# Tests
pytest tests/test_technical.py -v --cov=server --cov-report=term-missing

# Verify MCP tools are discoverable
python server.py --host 127.0.0.1 --port 8000 &
sleep 2
curl -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | jq '.result.tools[] | .name'
pkill -f "python server.py"
```

Expected: tools/list returns 12 tools (all previous + get_technical_analysis)

---

*Plan created: 2026-03-10*
