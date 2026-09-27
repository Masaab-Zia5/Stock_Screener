"""Fetches fundamental and price-history data for stock/ETF tickers via yfinance."""

import yfinance as yf
import pandas as pd
import requests


class FundamentalsFetchError(Exception):
    """Raised when fundamentals cannot be fetched due to a network/API problem,
    as opposed to the ticker simply having no data available.
    """


class PriceHistoryFetchError(Exception):
    """Raised when price history cannot be fetched due to a network/API problem,
    as opposed to the ticker simply having no data available.
    """


def get_fundamentals(ticker: str) -> dict:
    """Fetch fundamental data (P/E, P/B, PEG, FCF yield, D/E, sector, price) for a ticker.

    Args:
        ticker: Stock ticker symbol, e.g. "AAPL".

    Returns:
        A dict of fundamental metrics, or None if the ticker has no usable
        data (e.g. an ETF, an invalid symbol, or a delisted stock).

    Raises:
        FundamentalsFetchError: if the underlying request to the data
            provider fails (network error, rate limiting, malformed
            response), so callers can distinguish a transient failure
            from "no data available for this ticker".
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
    except (requests.RequestException, ConnectionError, TimeoutError) as e:
        raise FundamentalsFetchError(f"Network error fetching {ticker}: {e}") from e

    if not info or ("trailingPE" not in info and "shortName" not in info):
        # yfinance returns an empty/near-empty dict for invalid or delisted tickers
        print(f"  [!] No fundamentals data available for {ticker}")
        return None

    market_cap = info.get("marketCap")
    free_cashflow = info.get("freeCashflow")
    fcf_yield = None
    if free_cashflow and market_cap and market_cap > 0:
        fcf_yield = free_cashflow / market_cap

    raw_de = info.get("debtToEquity")

    return {
        "ticker":    ticker,
        "pe_ratio":  info.get("trailingPE"),
        "pb_ratio":  info.get("priceToBook"),
        "peg_ratio": info.get("pegRatio"),
        "fcf_yield": fcf_yield,
        # yfinance's debtToEquity is expressed as a percentage (e.g. 150.0 == 1.5x);
        # normalize to a plain ratio here so every downstream consumer works in
        # consistent units without needing to know this API-specific quirk.
        "de_ratio":  (raw_de / 100) if raw_de is not None else None,
        "name":      info.get("shortName", ticker),
        "sector":    info.get("sector", "N/A"),
        "price":     info.get("currentPrice"),
    }


def get_price_history(ticker: str, period: str = "2y") -> pd.DataFrame:
    """Fetch historical OHLCV price data for a ticker.

    Args:
        ticker: Stock ticker symbol, e.g. "AAPL".
        period: yfinance period string (e.g. "1y", "2y", "6mo", "max").

    Returns:
        A DataFrame of price history, or None if no data is available
        for this ticker.

    Raises:
        PriceHistoryFetchError: if the underlying request to the data
            provider fails (network error, rate limiting, malformed
            response), so callers can distinguish a transient failure
            from "no history available for this ticker".
    """
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
    except (requests.RequestException, ConnectionError, TimeoutError) as e:
        raise PriceHistoryFetchError(f"Network error fetching {ticker}: {e}") from e

    if df.empty:
        print(f"  [!] No price history for {ticker}")
        return None
    return df