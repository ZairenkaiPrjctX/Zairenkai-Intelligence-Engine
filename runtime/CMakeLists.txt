# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
# zie-run against llama.cpp's core libraries only (scripts/build-android.sh passes LLAMA_CPP_SRC).
cmake_minimum_required(VERSION 3.22)
project(zie_run CXX C)

set(LLAMA_CPP_SRC "" CACHE PATH "llama.cpp checkout at the commit runtime/llama.cpp.json pins")
if (NOT EXISTS "${LLAMA_CPP_SRC}/CMakeLists.txt")
    message(FATAL_ERROR "LLAMA_CPP_SRC must point at a llama.cpp checkout")
endif()

set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
foreach(opt LLAMA_BUILD_COMMON LLAMA_BUILD_TESTS LLAMA_BUILD_TOOLS LLAMA_BUILD_EXAMPLES LLAMA_BUILD_SERVER
            LLAMA_BUILD_APP LLAMA_BUILD_UI LLAMA_OPENSSL LLAMA_SUBPROCESS LLAMA_LLGUIDANCE LLAMA_BUILD_MTMD
            GGML_OPENMP GGML_NATIVE GGML_BACKEND_DL GGML_CPU_ALL_VARIANTS GGML_VULKAN GGML_OPENCL GGML_CCACHE)
    set(${opt} OFF CACHE BOOL "" FORCE)
endforeach()
add_subdirectory(${LLAMA_CPP_SRC} llama.cpp EXCLUDE_FROM_ALL)

add_executable(zie-run zie_run.cpp)
target_link_libraries(zie-run PRIVATE llama)
target_compile_features(zie-run PRIVATE cxx_std_17)
set(ZIE_LLAMA_TAG "unknown" CACHE STRING "llama.cpp tag, for --version")
target_compile_definitions(zie-run PRIVATE ZIE_LLAMA_TAG="${ZIE_LLAMA_TAG}")
