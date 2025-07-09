#ifndef XYZ_STRONG_TYPEDEFS_H
#define XYZ_STRONG_TYPEDEFS_H

#include <compare>
#include <concepts>

namespace xyz {

template <typename Tag, typename T>
class StrongTypedef {
 public:
  StrongTypedef() = delete;

  explicit StrongTypedef(const T& value) : value_(value) {}

  explicit operator T() const { return value_; }

  T value() const { return value_; }

  bool operator==(const StrongTypedef&) const
    requires std::equality_comparable<T>
  = default;

  auto operator<=>(const StrongTypedef&) const
    requires std::three_way_comparable<T>
  = default;

  friend StrongTypedef operator+(const StrongTypedef& lhs,
                                 const StrongTypedef& rhs)
    requires std::is_arithmetic_v<T>
  {
    return StrongTypedef(lhs.value_ + rhs.value_);
  }

  friend StrongTypedef operator-(const StrongTypedef& lhs,
                                 const StrongTypedef& rhs)
    requires std::is_arithmetic_v<T>
  {
    return StrongTypedef(lhs.value_ - rhs.value_);
  }

 private:
  T value_;
};
}  // namespace xyz

#ifdef XYZ_DEFINE_STRONG_TYPEDEF
#error "XYZ_DEFINE_STRONG_TYPEDEF is already defined."
#endif  // XYZ_DEFINE_STRONG_TYPEDEF
#define XYZ_DEFINE_STRONG_TYPEDEF(name, type) \
  struct name##Tag {};                        \
  using name = StrongTypedef<name##Tag, type>;

#endif  // XYZ_STRONG_TYPEDEFS_H
