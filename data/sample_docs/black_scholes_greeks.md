# Black-Scholes Option Pricing and Greeks

## Black-Scholes Formula

The Black-Scholes formula prices a European call option:

$$C=S_0N(d_1)-Ke^{-rT}N(d_2)$$

Where:

$$d_1=\frac{\ln(S_0/K)+(r+\sigma^2/2)T}{\sigma\sqrt{T}}$$

$$d_2=d_1-\sigma\sqrt{T}$$

Key assumptions include continuous trading, lognormal stock prices, constant volatility, no arbitrage, no transaction costs, and a constant risk-free rate.

## Option Greeks

Option Greeks measure sensitivity:

- Delta: sensitivity to the underlying price.
- Gamma: sensitivity of delta to the underlying price.
- Vega: sensitivity to volatility.
- Theta: sensitivity to time decay.
- Rho: sensitivity to interest rates.

Delta for a European call in Black-Scholes is:

$$\Delta_{call}=N(d_1)$$

Interpretation: Black-Scholes is useful for option pricing intuition, but real markets have volatility smiles, jumps, transaction costs, and changing liquidity.
