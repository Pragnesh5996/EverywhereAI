from decimal import Decimal


def bid_calc(
    pay_permil,
    total_streams,
    total_listeners,
    total_streams_country,
    total_listeners_country,
    total_streams_playlist,
    total_listeners_playlist,
    profit_margin,
    roas=1,
    ctr=100,
    inflation=0,
    dollar_to_euro=0.85,
):
    """
    Calculates a Bid

    Parameters:
    pay_permil (Decimal): Pay Per Million Streams (dollars)
    total_streams (int): total Streams for the current genre
    total_listeners (int: total Listeners for the current genre
    total_streams_country (int): total Streams for the current country in the current genre
    total_listeners_country (int): total Listeners for the current country in the current genre
    total_streams_playlist (int): total Streams in the current genre that come from SF playlists
    total_listeners_playlist (int): total Listeners in the current genre of the SF playlists
    profit_margin (int): profit margin for this calculation
    roas (Decimal): return on ads spend
    ctr (Decimal): click-through rate of the current ad
    inflation (int): inflation value for current genre [negative numbers for deflation]
    dollar_to_euro (Decimal): conversion rate from USD to Euro

    Returns: unrounded final bid (Decimal)
    """

    # make sure values cannot be negative
    # will also catch TypeError if parameters are not numbers
    if (
        pay_permil < 0
        or total_streams < 0
        or total_listeners < 0
        or total_streams_country < 0
        or total_listeners_country < 0
        or total_streams_playlist < 0
        or total_listeners_playlist < 0
        or profit_margin < 0
        or roas < 0
        or ctr < 0
    ):
        raise ValueError(
            "In Optimizer.py in bid_calc: a value that should be positive was negative or zero"
        )
    if dollar_to_euro <= 0:
        raise ValueError(
            "In Optimizer.py in bid_calc: dollar_to_euro <= 0; API call might not work properly"
        )

    # CTR may not surpass 100
    ctr = min(ctr, 100)
    try:
        avg_streams_per_listener_total = Decimal(total_streams) / Decimal(
            total_listeners
        )
        avg_streams_per_listener_country = Decimal(total_streams_country) / Decimal(
            total_listeners_country
        )
        streams_per_listener_from_playlist = Decimal(total_streams_playlist) / Decimal(
            total_listeners_playlist
        )
        playlist_listeners_weighted = (
            1
            + (avg_streams_per_listener_country - avg_streams_per_listener_total)
            / avg_streams_per_listener_total
        ) * streams_per_listener_from_playlist

        bid_playlist_euro = (
            Decimal(pay_permil)
            / Decimal(1000000 / playlist_listeners_weighted)
            * Decimal(str(dollar_to_euro))
        )

        bid_with_ctr_euro = bid_playlist_euro * Decimal(
            ctr / 100
        )  # Scale with CTR, CTR can be 100 at most

        final_bid_euro = bid_with_ctr_euro * ((100 - Decimal(profit_margin)) / 100)

        if inflation != 0:
            final_bid_euro = final_bid_euro * (100 + Decimal(inflation)) / 100

        if roas <= 1:
            final_bid_euro = final_bid_euro * Decimal(roas)

    except Exception:
        raise ArithmeticError(
            "Een berekening in optimizer.py in bid_calc is foutegegaan"
        )
    return final_bid_euro


def calculate_roas(total_streams_country, pay_permil, spend, dollar_to_euro):
    """
    Calculates ROAS

    Parameters:
    total_streams_country (int): total Streams for the current country in the current genre
    pay_permil (Decimal): Pay Per Million Streams (Dollar)
    spend (Decimal): amount of money spend (Euro)
    dollar_to_euro (Decimal): conversion rate from USD to Euro

    Returns: unrounded ROAS (Decimal)
    """
    if total_streams_country < 0 or pay_permil < 0 or spend < 0:
        raise ValueError(
            "In Optimizer.py in bid_calc: a value that should be positive was negative or zero"
        )
    if dollar_to_euro <= 0:
        raise ValueError(
            "In Optimizer.py in bid_calc: dollar_to_euro <= 0; API call might not work properly"
        )

    pay_per_stream = Decimal(pay_permil) / Decimal("1000000")
    revenue_dollars = Decimal(pay_per_stream) * Decimal(total_streams_country)
    revenue_euros = Decimal(revenue_dollars) * Decimal(dollar_to_euro)
    return revenue_euros / Decimal(spend)
