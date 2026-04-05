# Twelve Data Market Data Skill

## When to use this service

- You need real-time or historical prices, OHLCV, volume, or quotes
- Portfolio analysis, trading signals, backtesting, research reports, risk management
- Technical indicators (RSI, MACD, Bollinger Bands, and 100+ more)
- Fundamentals, earnings, dividends, splits, income statements, balance sheets
- Analyst ratings, price targets, EPS estimates, growth forecasts
- Forex exchange rates, crypto prices, ETF/mutual fund data
- Symbol search, exchange schedules, market state

## How to invoke

Two modes: **structured** (fast, deterministic) and **natural language** (flexible, AI-routed).

### Structured — use `function`

Specify `function` to call a Twelve Data endpoint directly. The value maps to the endpoint path (e.g. `TIME_SERIES` → `/time_series`). All other keys in `input` are forwarded as query parameters.

```json
{ "input": { "function": "QUOTE", "symbol": "AAPL" } }
```

```json
{ "input": { "function": "TIME_SERIES", "symbol": "TSLA", "interval": "5min", "outputsize": 50 } }
```

```json
{ "input": { "function": "RSI", "symbol": "AAPL", "interval": "1day", "time_period": 14 } }
```

```json
{ "input": { "function": "EARNINGS", "symbol": "MSFT" } }
```

```json
{ "input": { "function": "RECOMMENDATIONS", "symbol": "NVDA" } }
```

If the REST call fails, the proxy automatically falls back to the natural language MCP server.

### Natural language — use `query`

Ask in plain English. Routed through Twelve Data's MCP server with AI interpretation.

```json
{ "input": { "query": "What is the 14-day RSI for AAPL?" } }
```

```json
{ "input": { "query": "Show me MACD for BTC/USD on the daily chart" } }
```

```json
{ "input": { "query": "What are analysts saying about NVDA? Include price targets." } }
```

Use `query` when the exact endpoint is unclear, or to combine multiple data points in one call.

## Response format

```json
{
  "output": { ... },
  "provider": "Twelve Data",
  "source": "https://twelvedata.com"
}
```

`output.status` is `"ok"` on success and `"error"` on failure (bad symbol, unsupported interval, etc.).

---

## Available endpoints

### Market data

Access real-time and historical prices for equities, forex, crypto, ETFs, and more.

- `/time_series` — OHLCV time series. Params: `symbol`, `interval` (1min/5min/15min/30min/45min/1h/2h/4h/1day/1week/1month), `outputsize`, `start_date`, `end_date`
- `/time_series/cross` — Cross-asset time series
- `/quote` — Full quote (open, high, low, close, volume, change, percent change)
- `/price` — Latest price only
- `/eod` — End-of-day price
- `/market_movers/{market}` — Top movers. Market: `stocks`, `etfs`, `forex`, `crypto`

### Technical indicators

100+ indicators. All require `symbol` and `interval`. Common additional params: `time_period`, `series_type` (open/high/low/close).

**Overlap studies** (plotted on price chart):
- `/bbands` — Bollinger Bands
- `/ema` — Exponential moving average
- `/sma` — Simple moving average
- `/wma` — Weighted moving average
- `/dema` — Double EMA
- `/tema` — Triple EMA
- `/t3ma` — Triple exponential moving average
- `/trima` — Triangular moving average
- `/kama` — Kaufman adaptive moving average
- `/mama` — MESA adaptive moving average
- `/ma` — Generic moving average (specify `ma_type`)
- `/vwap` — Volume weighted average price
- `/ichimoku` — Ichimoku cloud
- `/keltner` — Keltner channel
- `/sar` — Parabolic SAR
- `/sarext` — Parabolic SAR extended
- `/ht_trendline` — Hilbert transform instantaneous trendline
- `/pivot_points_hl` — Pivot points high/low
- `/mcginley_dynamic` — McGinley dynamic
- `/midpoint` — Midpoint
- `/midprice` — Midprice

**Momentum indicators**:
- `/rsi` — Relative strength index
- `/macd` — MACD. Params: `fast_period`, `slow_period`, `signal_period`
- `/macdext` — MACD extension
- `/macd_slope` — MACD slope
- `/stoch` — Stochastic oscillator
- `/stochf` — Stochastic fast
- `/stochrsi` — Stochastic RSI
- `/adx` — Average directional index
- `/adxr` — Average directional movement index rating
- `/cci` — Commodity channel index
- `/mfi` — Money flow index
- `/willr` — Williams %R
- `/aroon` — Aroon indicator
- `/aroonosc` — Aroon oscillator
- `/apo` — Absolute price oscillator
- `/ppo` — Percentage price oscillator
- `/mom` — Momentum
- `/roc` — Rate of change
- `/rocp` — Rate of change percentage
- `/rocr` — Rate of change ratio
- `/rocr100` — Rate of change ratio 100
- `/dx` — Directional movement index
- `/minus_di` — Minus directional indicator
- `/minus_dm` — Minus directional movement
- `/plus_di` — Plus directional indicator
- `/plus_dm` — Plus directional movement
- `/bop` — Balance of power
- `/cmo` — Chande momentum oscillator
- `/dpo` — Detrended price oscillator
- `/kst` — Know sure thing
- `/coppock` — Coppock curve
- `/crsi` — Connors RSI
- `/ultosc` — Ultimate oscillator
- `/percent_b` — Percent B

**Volume indicators**:
- `/ad` — Accumulation/distribution
- `/adosc` — Accumulation/distribution oscillator
- `/obv` — On balance volume
- `/rvol` — Relative volume

**Volatility indicators**:
- `/atr` — Average true range
- `/natr` — Normalized ATR
- `/trange` — True range
- `/supertrend` — Supertrend
- `/supertrend_heikinashicandles` — Supertrend Heikin Ashi candles

**Price transforms**:
- `/avgprice` — Average price
- `/medprice` — Median price
- `/typprice` — Typical price
- `/wclprice` — Weighted close price
- `/hlc3` — High/low/close average
- `/heikinashicandles` — Heikin Ashi candles
- `/add`, `/sub`, `/mult`, `/div`, `/sum`, `/avg`, `/sqrt`, `/exp`, `/ln`, `/log10`, `/ceil`, `/floor` — Math transforms

**Cycle indicators**:
- `/ht_dcperiod` — Dominant cycle period
- `/ht_dcphase` — Dominant cycle phase
- `/ht_phasor` — Phasor components
- `/ht_sine` — Sine wave
- `/ht_trendmode` — Trend vs cycle mode

**Statistic functions**:
- `/stddev` — Standard deviation
- `/var` — Variance
- `/beta` — Beta
- `/correl` — Correlation
- `/linearreg` — Linear regression
- `/linearregangle`, `/linearregintercept`, `/linearregslope` — Linear regression components
- `/tsf` — Time series forecast
- `/max`, `/min`, `/minmax`, `/maxindex`, `/minindex`, `/minmaxindex` — Extremes

### Fundamentals

- `/profile` — Company profile and metadata
- `/logo` — Company logo URL
- `/statistics` — Key ratios (P/E, market cap, EV, etc.)
- `/market_cap` — Market capitalization
- `/earnings` — Earnings history
- `/earnings_calendar` — Upcoming earnings dates
- `/dividends` — Dividend history
- `/dividends_calendar` — Upcoming dividend dates
- `/splits` — Split history
- `/splits_calendar` — Upcoming split dates
- `/ipo_calendar` — Upcoming IPOs
- `/income_statement` — Income statement
- `/income_statement/consolidated` — Consolidated income statement
- `/balance_sheet` — Balance sheet
- `/balance_sheet/consolidated` — Consolidated balance sheet
- `/cash_flow` — Cash flow statement
- `/cash_flow/consolidated` — Consolidated cash flow
- `/key_executives` — C-suite and board members
- `/press_releases` — Recent press releases
- `/last_change/{endpoint}` — Last update timestamp for any fundamental endpoint

### Analysis

- `/recommendations` — Analyst buy/sell/hold recommendations
- `/analyst_ratings/light` — Analyst ratings snapshot
- `/analyst_ratings/us_equities` — Detailed analyst ratings for US equities
- `/price_target` — Consensus price targets
- `/earnings_estimate` — Forward earnings estimates
- `/revenue_estimate` — Forward revenue estimates
- `/eps_trend` — EPS trend over time
- `/eps_revisions` — EPS revision history
- `/growth_estimates` — Growth projections

### Reference data

- `/symbol_search` — Search for symbols by name or ticker
- `/stocks` — Full list of available stocks
- `/forex_pairs` — All forex pairs
- `/cryptocurrencies` — All crypto pairs
- `/etfs` — ETF universe
- `/funds` — Mutual fund universe
- `/commodities` — Commodities list
- `/bonds` — Fixed income instruments
- `/exchanges` — Exchange list
- `/exchange_schedule` — Trading hours by exchange
- `/cryptocurrency_exchanges` — Crypto exchange list
- `/market_state` — Which markets are currently open
- `/countries` — Supported countries
- `/earliest_timestamp` — Earliest available data date for a symbol
- `/cross_listings` — Cross-listed symbols across exchanges

---

## Pricing

- Model: `per_call`
- Price: ~0.28 NEAR per call
- Use payment channels for >10 calls per job (reduces per-call overhead)

## Service details

- **Service name**: Twelve Data Market Data API
- **Category**: data
- **Tags**: market-data, stocks, crypto, forex, real-time, historical, fundamentals, technical-indicators, mcp, natural-language
