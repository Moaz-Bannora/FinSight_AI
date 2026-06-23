# No-Arbitrage, Forwards, and Put-Call Parity

## No-Arbitrage Pricing

No-arbitrage pricing states that two portfolios with identical future payoffs should have the same price today.

For one-period pricing:

$$P_0=\frac{E^Q[X_1]}{1+r}$$

Where $Q$ is the risk-neutral probability measure.

## Forward Contracts

For an asset with no income and no storage cost, the forward price is:

$$F_0=S_0e^{rT}$$

If the asset pays a continuous dividend yield $q$:

$$F_0=S_0e^{(r-q)T}$$

## Put-Call Parity

European put-call parity links call prices, put prices, the underlying asset, and the present value of the strike price:

$$C+Ke^{-rT}=P+S_0$$

Interpretation: if put-call parity is violated, an arbitrage opportunity may exist, ignoring transaction costs and market frictions.
