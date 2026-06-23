# Binomial Option Pricing, Implied Volatility, and Volatility Smile

## Binomial Option Pricing

In a one-period binomial model, risk-neutral probability is:

$$p=\frac{e^{r\Delta t}-d}{u-d}$$

The option value is:

$$V_0=e^{-r\Delta t}[pV_u+(1-p)V_d]$$

The binomial model is useful for teaching option pricing intuition and for valuing American-style options.

## Implied Volatility

Implied volatility is the volatility input that makes an option pricing model match the observed market price.

It is not a direct forecast. It reflects market pricing, supply and demand, risk premia, and expectations.

## Volatility Smile

The volatility smile occurs when implied volatility differs across strike prices. It suggests that real-world return distributions are not perfectly lognormal and that markets price tail risk.
