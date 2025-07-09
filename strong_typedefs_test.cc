// Tests for strong typedefs
#include "strong_typedefs.h"

#include <gtest/gtest.h>

namespace xyz {

struct ATag {};

using AType = xyz::StrongTypedef<ATag, double>;

XYZ_DEFINE_STRONG_TYPEDEF(BType, double);

TEST(StrongTypedefsTest, Equality) {
  AType x(1.0);
  AType xx(2.0);

  EXPECT_EQ(x, x);
  EXPECT_NE(x, xx);
}

TEST(StrongTypedefsTest, EqualityComparableTraits) {
  AType x(1.0);
  BType y(2.0);

  static_assert(std::equality_comparable_with<AType, AType>);
  static_assert(std::equality_comparable_with<BType, BType>);
  static_assert(!std::equality_comparable_with<AType, BType>);
}

TEST(StrongTypedefsTest, ThreeWayComparison) {
  AType x(1.0);
  AType xx(2.0);

  EXPECT_TRUE(x < xx);
  EXPECT_TRUE(xx > x);
  EXPECT_FALSE(x == xx);
  EXPECT_TRUE(x <= xx);
  EXPECT_TRUE(xx >= x);
}

TEST(StrongTypedefsTest, ThreeWayComparableTraits) {
  AType x(1.0);
  BType y(2.0);

  static_assert(std::three_way_comparable_with<AType, AType>);
  static_assert(std::three_way_comparable_with<BType, BType>);
  static_assert(!std::three_way_comparable_with<AType, BType>);
}

TEST(StrongTypedefsTest, ArithmeticOperations) {
  AType x(1.0);
  AType y(2.0);

  auto sum = x + y;
  auto diff = x - y;

  EXPECT_EQ(sum.value(), 3.0);
  EXPECT_EQ(diff.value(), -1.0);
}
}  // namespace xyz
