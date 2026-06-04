# Value at Risk and Conditional Value at Risk

## Value at Risk

Value at Risk, or VaR, estimates the maximum expected loss over a time horizon at a confidence level.

If portfolio returns are normally distributed, parametric VaR can be approximated as:

$$VaR_\alpha=z_\alpha\sigma_pV$$

Where:

- $z_\alpha$ is the critical value.
- $\sigma_p$ is portfolio volatility.
- $V$ is portfolio value.

VaR is easy to communicate, but it does not describe the size of losses beyond the VaR threshold.

## Conditional Value at Risk

Conditional Value at Risk, or CVaR, measures expected loss given that losses exceed VaR:

$$CVaR_\alpha=E[L\mid L\ge VaR_\alpha]$$

CVaR is often preferred for tail-risk analysis because it considers the severity of extreme losses.

Interpretation: VaR answers "how bad can losses get before a threshold?" while CVaR answers "if losses are beyond the threshold, how bad are they on average?"
