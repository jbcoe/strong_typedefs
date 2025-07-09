# Strong Typedefs

[![Tests](https://github.com/jbcoe/strong_typedefs/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/jbcoe/strong_typedefs/actions/workflows/test.yml)
[![Pre-commit](https://github.com/jbcoe/strong_typedefs/actions/workflows/pre-commit.yml/badge.svg?branch=main)](https://github.com/jbcoe/strong_typedefs/actions/workflows/pre-commit.yml)
[![C++20](https://img.shields.io/badge/C%2B%2B-20-blue.svg)](https://en.cppreference.com/w/cpp/20)

A minimal C++20 header-only library for creating type-safe wrappers around
primitive types.

## Overview

Strong typedefs prevent accidental mixing of semantically different values that
share the same underlying type. They provide compile-time type safety with zero
runtime overhead.

## Use cases

- **Units**: Distinguish between meters, feet, seconds, etc.
- **IDs**: Prevent mixing user IDs, product IDs, session IDs
- **Coordinates**: Separate X and Y coordinates, latitude and longitude
- **Currency**: Avoid mixing USD, EUR, GBP amounts

## Usage

```cpp
#include "strong_typedefs.h"

// Define distinct types
XYZ_DEFINE_STRONG_TYPEDEF(UserId, int);
XYZ_DEFINE_STRONG_TYPEDEF(ProductId, int);
XYZ_DEFINE_STRONG_TYPEDEF(Meters, double);

UserId user_id(123);
ProductId product_id(456);

// Compile error - different types!
// bool same = (user_id == product_id);

// Arithmetic works for numeric types
Meters a(10.0), b(5.0);
Meters total = a + b;  // 15.0
```

## Building

```bash
bazel test //...
```

Requires a C++20 compiler.
