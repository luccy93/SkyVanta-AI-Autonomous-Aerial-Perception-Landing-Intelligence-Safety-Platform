cmake_minimum_required(VERSION 3.14)
project(SkyVanta_CPP VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find OpenCV package
find_package(OpenCV REQUIRED)

include_directories(${OpenCV_INCLUDE_DIRS})

add_executable(skyvanta_cpp_demo src/main.cpp)
target_link_libraries(skyvanta_cpp_demo PRIVATE ${OpenCV_LIBS})

message(STATUS "SkyVanta C++ Demo configured with OpenCV version: ${OpenCV_VERSION}")
