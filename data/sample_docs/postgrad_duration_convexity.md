# Bond Duration and Convexity

Macaulay duration is the weighted average timing of bond cash flows:

$$D_M=\sum_{t=1}^{n}t\frac{PV(CF_t)}{P}$$

Modified duration approximates price sensitivity to yield:

$$D_{mod}=\frac{D_M}{1+y}$$

Convexity improves the approximation for larger yield changes:

$$\frac{\Delta P}{P}\approx-D_{mod}\Delta y+\frac{1}{2}Convexity(\Delta y)^2$$

Interpretation: duration captures the first-order price effect of yield changes, while convexity captures curvature. Bonds with higher convexity gain more when yields fall and lose less when yields rise, all else equal.
