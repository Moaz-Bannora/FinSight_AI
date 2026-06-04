# Mean-Variance Portfolio Theory

Mean-variance analysis studies the tradeoff between expected return and risk. It is a foundation of modern portfolio theory and postgraduate asset-pricing courses.

For a portfolio with weights $w$, expected returns $\mu$, and covariance matrix $\Sigma$:

$$E(R_p)=w^\top\mu$$

$$\sigma_p^2=w^\top\Sigma w$$

The minimum-variance portfolio solves:

$$\min_w w^\top\Sigma w$$

subject to:

$$\mathbf{1}^\top w=1$$

With a target return, the optimization adds:

$$w^\top\mu=\mu^*$$

Interpretation: diversification depends on covariance, not only individual asset volatility. A portfolio can reduce risk when assets do not move together perfectly.
