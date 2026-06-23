# Credit Risk: Merton Model and Expected Loss

## Merton Structural Credit Risk Model

The Merton model treats equity as a call option on firm assets. Default occurs when asset value falls below debt value at maturity.

Equity can be represented as:

$$E=VN(d_1)-De^{-rT}N(d_2)$$

Where $V$ is firm asset value and $D$ is debt face value. This links credit risk to asset volatility, leverage, and time to maturity.

## Expected Loss

Expected loss in credit risk is commonly approximated by:

$$EL=PD\times LGD\times EAD$$

Where:

- $PD$ is probability of default.
- $LGD$ is loss given default.
- $EAD$ is exposure at default.

Interpretation: expected loss is a mean loss estimate, while economic capital usually targets unexpected loss under stress or high confidence levels.
