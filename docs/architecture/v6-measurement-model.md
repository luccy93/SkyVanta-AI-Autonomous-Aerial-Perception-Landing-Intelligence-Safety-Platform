# SkyVanta AI — Volume 6 Measurement Model Specification

---

## 1. Visual 6-DoF Pose Observation Model

A discrete visual pose observation provides:
$$\mathbf{z} = \begin{bmatrix} \mathbf{p}_{\text{meas}} \\ \mathbf{R}_{\text{meas}} \end{bmatrix}$$

where $\mathbf{p}_{\text{meas}} \in \mathbb{R}^3$ is position in World frame, and $\mathbf{R}_{\text{meas}} \in \mathbb{SO}(3)$ is orientation in World frame.

---

## 2. Measurement Residuals & Manifold Innovation

1. **Position Residual**:
   $$\mathbf{r}_p = \mathbf{p}_{\text{meas}} - \mathbf{p}_{\text{est}} \in \mathbb{R}^3$$

2. **Orientation Residual (on Lie Algebra $\mathfrak{so}(3)$)**:
   $$\mathbf{r}_\theta = \text{Log}(\mathbf{R}_{\text{est}}^T \mathbf{R}_{\text{meas}}) \in \mathbb{R}^3$$

3. **Combined 6-Vector Residual**:
   $$\mathbf{r} = \begin{bmatrix} \mathbf{r}_p \\ \mathbf{r}_\theta \end{bmatrix} \in \mathbb{R}^6$$

---

## 3. Measurement Jacobian Matrix $H$

$$H = \begin{bmatrix}
\mathbf{I}_{3\times 3} & \mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} \\
\mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} & \mathbf{I}_{3\times 3} & \mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3}
\end{bmatrix} \in \mathbb{R}^{6 \times 15}$$

---

## 4. Innovation Gating (Normalized Innovation Squared)

Innovation Covariance:
$$S = H P H^T + R_m \in \mathbb{R}^{6 \times 6}$$

Mahalanobis / NIS Distance:
$$d_M^2 = \mathbf{r}^T S^{-1} \mathbf{r}$$

* If $d_M^2 \le \chi^2(6, \alpha=0.01) \approx 16.81$: The measurement is accepted and processed.
* If $d_M^2 > 16.81$: The measurement is rejected as an outlier. State $\mathbf{x}$ and covariance $P$ remain untouched.

---

## 5. Kalman Gain & Error-State Injection

1. **Kalman Gain**:
   $$K = P H^T S^{-1} \in \mathbb{R}^{15 \times 6}$$
2. **Error Vector Estimate**:
   $$\delta \hat{\mathbf{x}} = K \mathbf{r} \in \mathbb{R}^{15}$$
3. **Injection**:
   $$\mathbf{p} \leftarrow \mathbf{p} + \delta \hat{\mathbf{p}}$$
   $$\mathbf{v} \leftarrow \mathbf{v} + \delta \hat{\mathbf{v}}$$
   $$\mathbf{R} \leftarrow \mathbf{R} \text{Exp}(\delta \hat{\boldsymbol{\theta}})$$
   $$\mathbf{b}_g \leftarrow \mathbf{b}_g + \delta \hat{\mathbf{b}}_g$$
   $$\mathbf{b}_a \leftarrow \mathbf{b}_a + \delta \hat{\mathbf{b}}_a$$
4. **Joseph-Form Covariance Reset**:
   $$P \leftarrow (\mathbf{I}_{15} - K H) P (\mathbf{I}_{15} - K H)^T + K R_m K^T$$
   $$P \leftarrow \frac{1}{2}(P + P^T)$$
