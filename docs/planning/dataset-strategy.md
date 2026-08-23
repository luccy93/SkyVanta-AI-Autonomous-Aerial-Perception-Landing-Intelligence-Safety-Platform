# SkyVanta AI — Dataset & Model Training Strategy

## 1. Dataset Taxonomy & Data Collection Pillars
A high-reliability aerial perception system requires diverse training data spanning varied altitudes, lighting angles, surface textures, weather conditions, and lens distortions. SkyVanta AI leverages a **four-pillar dataset architecture**:

```
+-----------------------------------------------------------------------------------------+
|                                DATASET ARCHITECTURE                                     |
|                                                                                         |
|  +------------------------+  +--------------------------+  +--------------------------+  |
|  | 1. Public Aerial &     |  | 2. Synthetic Domain      |  | 3. Custom Real-World     |  |
|  | Drone Datasets         |  | Generation (Gazebo/Unity)|  | Drone Video Clips        |  |
|  +-----------+------------+  +------------+-------------+  +------------+-------------+  |
|              |                            |                             |                |
|              +----------------------------+-----------------------------+                |
|                                           |                                             |
|                                           v                                             |
|                             +---------------------------+                               |
|                             | 4. Data Processing Engine |                               |
|                             | - Auto-Annotation Pipeline|                               |
|                             | - Physics-Aware Augment   |                               |
|                             | - Stratified Train/Val/Test|                              |
|                             +-------------+-------------+                               |
|                                           |                                             |
|                                           v                                             |
|                             +---------------------------+                               |
|                             | Model Registry & MLflow   |                               |
|                             | (FP16 / INT8 TensorRT)    |                               |
|                             +---------------------------+                               |
+-----------------------------------------------------------------------------------------+
```

---

## 2. Dataset Sources & Volumes

### A. Public Benchmark Datasets
* **VisDrone (Target Detection & Tracking)**: 10,000+ aerial images and video sequences captured across various urban environments. Used for general drone and small object aerial perception baselines.
* **DroneDeploy & UAVid**: Aerial semantic segmentation datasets used for ground texture classification and obstacle avoidance.
* **AprilTag / ArUco Benchmark Sets**: Standardized fiducial datasets across extreme angles (up to $75^\circ$) and blurred conditions.

### B. Synthetic Photorealistic Dataset (Domain Randomization)
* Generated using Gazebo Harmonic, AirSim, and Blender.
* Automated parameter sweeps:
  * **Sun Angle & Illumination**: $0^\circ$ (zenith) to $85^\circ$ (grazing), 10 lux to 100,000 lux.
  * **Landing Pad Textures**: Concrete, asphalt, gravel, grass, ship deck steel, wet tarmac with specular puddles.
  * **Camera Motion Perturbations**: Synthesized motion blur kernels matching angular velocities up to $120^\circ/\text{s}$.
* Target Volume: 25,000 labeled synthetic frames with pixel-perfect ground truth bounding boxes, corner keypoints, and 6-DoF poses.

### C. Custom Real-World Video Dataset
* Sourced from real downward-facing drone flights (including the baseline test sequences in the current repository).
* Real-world edge cases: Shadow transitions beneath trees/structures, rotor shadow flickering on camera lens, dynamic crosswinds.
* Target Volume: 5,000 carefully curated, high-diversity frames.

---

## 3. Data Annotation & Labeling Standards

### Standardized Classes & Keypoints
```yaml
Classes:
  0: landing_pad_h        # Standard 'H' circular landing pad
  1: landing_pad_circle   # Concentric circular target pad
  2: fiducial_april       # AprilTag 36h11 marker pattern
  3: fiducial_aruco       # ArUco 6x6 marker pattern
  4: obstacle_hazard      # Person, vehicle, or debris obstructing the pad
  5: drone_airframe       # Other UAV / peer drone in airspace

Keypoint Annotations (for 6-DoF PnP Pose Estimation):
  - Top-Left Corner (u0, v0)
  - Top-Right Corner (u1, v1)
  - Bottom-Right Corner (u2, v2)
  - Bottom-Left Corner (u3, v3)
  - Center Pad Target (uc, vc)
```

---

## 4. Physics-Aware Augmentation Pipeline

Training augmentations simulate real physical phenomena encountered during drone flight:
1. **Motion Blur & Defocus**: Random linear motion blur simulating wind gusts and motor vibrations ($k_{size} \in [3, 11]$).
2. **Radial Lens Distortion**: Simulating wide-angle and fish-eye drone lens distortion profiles ($k_1 \in [-0.2, 0.2]$).
3. **Photometric Glare & Shadows**: Random polygonal shadow injection and simulated lens flare bright spots.
4. **Scale & Perspective Jitter**: Affine and projective warps simulating extreme drone pitch/roll angles up to $\pm 35^\circ$.
5. **Color Temperature & Grain**: Random RGB shifts, Gaussian sensor noise, and ISO grain simulation.

---

## 5. Dataset Splitting & Evaluation Benchmark
* **Split Ratio**: 70% Train, 15% Validation, 15% Test (Split stratified by environmental conditions to prevent frame leakage).
* **Hard Test Benchmark**: A separate frozen test suite containing 1,000 "adversarial" frames (extreme glare, heavy blur, 80% occlusion) used to gate production model deployments.
* **Model Registry Policy**: Models must achieve $\ge 92.0\%$ mAP@50 on the standard validation set and $\ge 75.0\%$ mAP@50 on the adversarial benchmark before export to TensorRT INT8.
