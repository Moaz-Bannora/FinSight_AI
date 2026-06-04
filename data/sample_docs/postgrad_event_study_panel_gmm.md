# Event Studies, Panel Regression, and GMM

## Event Study Methodology

Event studies test whether an event creates abnormal returns around an event date.

Abnormal return:

$$AR_{i,t}=R_{i,t}-(\alpha_i+\beta_iR_{m,t})$$

Cumulative abnormal return:

$$CAR_{i}(\tau_1,\tau_2)=\sum_{t=\tau_1}^{\tau_2}AR_{i,t}$$

Event studies are common in finance research for mergers, earnings announcements, regulation changes, and corporate governance events.

## Panel Regression

Panel data combines cross-sectional and time-series observations. A common fixed-effects specification is:

$$Y_{i,t}=\alpha_i+\gamma_t+\beta X_{i,t}+\epsilon_{i,t}$$

Where $\alpha_i$ controls for time-invariant firm characteristics and $\gamma_t$ controls for time effects. Robust standard errors are often clustered by firm.

## Generalized Method of Moments

Generalized Method of Moments estimates parameters using moment conditions:

$$E[g(Z_t,\theta)]=0$$

The estimator chooses $\theta$ to make sample moments as close to zero as possible:

$$\hat{\theta}=\arg\min_\theta \bar{g}(\theta)^\top W \bar{g}(\theta)$$

Interpretation: GMM is useful in asset pricing and dynamic panel models, but it requires careful instrument choice and diagnostic testing.
