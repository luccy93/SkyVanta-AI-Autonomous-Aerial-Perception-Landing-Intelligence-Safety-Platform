# SkyVanta AI — Volume 6 State & Noise Model Specification

---

## 1. Nominal State Space

The physical nominal state $\mathbf{x}$ is defined on the manifold:
$$\mathcal{M} = \mathbb{R}^3 \times \mathbb{R}^3 \times \mathbb{SO}(3) \times \mathbb{R}^3 \times \mathbb{R}^3$$

$$\mathbf{x} = \begin{bmatrix} \mathbf{p} \\ \mathbf{v} \\ \mathbf{R} \\ \mathbf{b}_g \\ \mathbf{b}_a \end{bmatrix}$$

| Symbol | Parameter | Dimension | Coordinate Frame | Units |
| :--- | :--- | :--- | :--- | :--- |
| $\mathbf{p}$ | Position | $\mathbb{R}^3$ | $\text{World}$ (NED) | $\text{m}$ |
| $\mathbf{v}$ | Linear Velocity | $\mathbb{R}^3$ | $\text{World}$ (NED) | $\text{m/s}$ |
| $\mathbf{R}$ | Orientation Rotation Matrix | $\mathbb{SO}(3)$ | $\text{Body} \to \text{World}$ | Dimensionless |
| $\mathbf{b}_g$ | Gyroscope Bias | $\mathbb{R}^3$ | $\text{Body}$ | $\text{rad/s}$ |
| $\mathbf{b}_a$ | Accelerometer Bias | $\mathbb{R}^3$ | $\text{Body}$ | $\text{m/s}^2$ |

---

## 2. 15-Dimensional Error State Vector

The uncertainty in the state estimate is parameterized by the minimal true error vector $\delta \mathbf{x} \in \mathbb{R}^{15}$:

$$\delta \mathbf{x} = \begin{bmatrix} \delta \mathbf{p} \\ \delta \mathbf{v} \\ \delta \boldsymbol{\theta} \\ \delta \mathbf{b}_g \\ \delta \mathbf{b}_a \end{bmatrix} \in \mathbb{R}^{15}$$

### State Ordering & Slicing:
* **Indices 0..2 (`INDEX_POS`)**: $\delta \mathbf{p} = \mathbf{p}_{\text{true}} - \mathbf{p} \in \mathbb{R}^3$ (Position error in World frame)
* **Indices 3..5 (`INDEX_VEL`)**: $\delta \mathbf{v} = \mathbf{v}_{\text{true}} - \mathbf{v} \in \mathbb{R}^3$ (Velocity error in World frame)
* **Indices 6..8 (`INDEX_ATT`)**: $\delta \boldsymbol{\theta} \in \mathbb{R}^3$ (Body attitude error vector: $\mathbf{R}_{\text{true}} = \mathbf{R} \text{Exp}(\delta \boldsymbol{\theta})$)
* **Indices 9..11 (`INDEX_BG`)**: $\delta \mathbf{b}_g = \mathbf{b}_{g, \text{true}} - \mathbf{b}_g \in \mathbb{R}^3$ (Gyro bias error in Body frame)
* **Indices 12..14 (`INDEX_BA`)**: $\delta \mathbf{b}_a = \mathbf{b}_{a, \text{true}} - \mathbf{b}_a \in \mathbb{R}^3$ (Accel bias error in Body frame)

---

## 3. Error-State Continuous Dynamics Matrix $F_c$

$$\delta \dot{\mathbf{x}} = F_c \delta \mathbf{x} + G_c \mathbf{n}$$

$$F_c = \begin{bmatrix}
\mathbf{0}_{3\times 3} & \mathbf{I}_{3\times 3} & \mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} \\
\mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} & -\mathbf{R} [\hat{\mathbf{a}}]_\times & \mathbf{0}_{3\times 3} & -\mathbf{R} \\
\mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} & -[\hat{\boldsymbol{\omega}}]_\times & -\mathbf{I}_{3\times 3} & \mathbf{0}_{3\times 3} \\
\mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} \\
\mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3}
\end{bmatrix}$$

where $[\hat{\mathbf{a}}]_\times = [\mathbf{a}_m - \mathbf{b}_a]_\times$ and $[\hat{\boldsymbol{\omega}}]_\times = [\boldsymbol{\omega}_m - \mathbf{b}_g]_\times$.

---

## 4. Discrete Process Noise Covariance Matrix $Q_k$

$$Q_k = \begin{bmatrix}
\frac{1}{3} \sigma_a^2 \Delta t^3 \mathbf{I}_3 & \frac{1}{2} \sigma_a^2 \Delta t^2 \mathbf{I}_3 & \mathbf{0} & \mathbf{0} & \mathbf{0} \\
\frac{1}{2} \sigma_a^2 \Delta t^2 \mathbf{I}_3 & \sigma_a^2 \Delta t \mathbf{I}_3 & \mathbf{0} & \mathbf{0} & \mathbf{0} \\
\mathbf{0} & \mathbf{0} & \sigma_g^2 \Delta t \mathbf{I}_3 & \mathbf{0} & \mathbf{0} \\
\mathbf{0} & \mathbf{0} & \mathbf{0} & \sigma_{bg}^2 \Delta t \mathbf{I}_3 & \mathbf{0} \\
\mathbf{0} & \mathbf{0} & \mathbf{0} & \mathbf{0} & \sigma_{ba}^2 \Delta t \mathbf{I}_3
\end{bmatrix}$$
