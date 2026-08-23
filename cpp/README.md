# SkyVanta AI — C++ Kalman Filter & HUD Subsystem

This directory contains the standalone C++ implementation of the 2D Kalman filter and OpenCV HUD rendering primitives.

## Prerequisites
* CMake >= 3.14
* C++17 compatible compiler (GCC, Clang, or MSVC)
* OpenCV >= 4.0 (`libopencv-dev`)

## Building with CMake
```bash
mkdir build && cd build
cmake ..
cmake --build .
```

## Running the C++ Demo
```bash
./skyvanta_cpp_demo
# or on Windows:
.\skyvanta_cpp_demo.exe
```
This generates `kalman_ball_output.mp4` showing real-time 2D state estimation and HUD overlay rendering.
