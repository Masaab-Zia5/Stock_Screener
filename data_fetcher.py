import requests


class FundamentalsFetchError(Exception):
    """Raised when fundamentals cannot be fetched due to a network/API problem,
    as opposed to the ticker simply having no data available."""


def get_fundamentals(ticker: str) -> dict:
    """Fetch fundamental data for a ticker from yfinance.

    Returns a dict of fundamental metrics, or None if the ticker has no
    usable data (e.g. an ETF or invalid symbol).

    Raises:
        FundamentalsFetchError: if the underlying request to yfinance fails
            (network error, rate limiting, malformed response), so callers
            can distinguish a transient failure from "no data available".
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
    except (requests.RequestException, ConnectionError, TimeoutError) as e:
        raise FundamentalsFetchError(f"Network error fetching {ticker}: {e}") from e

    if not info or "trailingPE" not in info and "shortName" not in info:
        # yfinance returns an empty/near-empty dict for invalid or delisted tickers
        print(f"  [!] No fundamentals data available for {ticker}")
        return None

    market_cap = info.get("marketCap")
    free_cashflow = info.get("freeCashflow")
    fcf_yield = None
    if free_cashflow and market_cap and market_cap > 0:
        fcf_yield = free_cashflow / market_cap

    return {
        "ticker":    ticker,
        "pe_ratio":  info.get("trailingPE"),
        "pb_ratio":  info.get("priceToBook"),
        "peg_ratio": info.get("pegRatio"),
        "fcf_yield": fcf_yield,
        "de_ratio":  info.get("debtToEquity"),
        "name":      info.get("shortName", ticker),
        "sector":    info.get("sector", "N/A"),
        "price":     info.get("currentPrice"),
    }