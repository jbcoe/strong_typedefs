"""
Bazel to CMake Converter

Converts Bazel BUILD.bazel files to CMakeLists.txt with modern CMake syntax.
Uses Python evaluation of BUILD files since they are valid Python syntax.

Requirements:
- Python 3.9+
- C++20 compatible compiler for generated projects

Usage:
    python3 bazel_to_cmake.py [options]

Examples:
    python3 bazel_to_cmake.py
    python3 bazel_to_cmake.py --build-file my_module/BUILD.bazel --project-name my_project
    python3 bazel_to_cmake.py --output my_cmake/CMakeLists.txt

Features:
- Header-only libraries as INTERFACE targets
- FetchContent for external dependencies
- Install rules and CTest integration
- Modern CMake generator expressions
"""

import argparse
from pathlib import Path


class BazelTarget:
    """Bazel target (cc_library, cc_test, etc.)"""

    def __init__(self, rule_type: str, name: str):
        self.rule_type = rule_type
        self.name = name
        self.hdrs: list[str] = []
        self.srcs: list[str] = []
        self.deps: list[str] = []
        self.visibility: list[str] = []
        self.data: list[str] = []

    def add_attribute(self, attr_name: str, values: list[str]):
        """Add attribute values"""
        if attr_name == "hdrs":
            self.hdrs.extend(values)
        elif attr_name == "srcs":
            self.srcs.extend(values)
        elif attr_name == "deps":
            self.deps.extend(values)
        elif attr_name == "visibility":
            self.visibility.extend(values)
        elif attr_name == "data":
            self.data.extend(values)


class BazelParser:
    """Parses Bazel BUILD files by evaluating them as Python"""

    def __init__(self):
        self.targets: list[BazelTarget] = []

    def parse_file(self, filepath: Path) -> list[BazelTarget]:
        """Parse BUILD.bazel file by evaluating as Python"""
        with open(filepath, 'r') as f:
            content = f.read()

        # Define Bazel functions that capture target definitions
        def load(*args, **kwargs):
            """Mock load function - ignore load statements"""
            pass

        def cc_library(**kwargs):
            """Mock cc_library function"""
            target = BazelTarget("cc_library", kwargs.get("name", ""))
            self._populate_target(target, kwargs)
            self.targets.append(target)

        def cc_test(**kwargs):
            """Mock cc_test function"""
            target = BazelTarget("cc_test", kwargs.get("name", ""))
            self._populate_target(target, kwargs)
            self.targets.append(target)

        def cc_binary(**kwargs):
            """Mock cc_binary function"""
            target = BazelTarget("cc_binary", kwargs.get("name", ""))
            self._populate_target(target, kwargs)
            self.targets.append(target)

        # Create execution environment with our mock functions
        exec_globals = {
            "load": load,
            "cc_library": cc_library,
            "cc_test": cc_test,
            "cc_binary": cc_binary,
        }

        # Execute the BUILD file content
        exec(content, exec_globals)

        return self.targets

    def _populate_target(self, target: BazelTarget, kwargs: dict):
        """Populate target with attributes from kwargs"""
        for attr_name in ["hdrs", "srcs", "deps", "visibility", "data"]:
            if attr_name in kwargs:
                values = kwargs[attr_name]
                if isinstance(values, list):
                    target.add_attribute(attr_name, values)
                else:
                    target.add_attribute(attr_name, [values])


class CMakeGenerator:
    """Generates CMakeLists.txt files"""

    def __init__(self, project_name: str = "strong_typedefs"):
        self.project_name = project_name
        self.cmake_minimum_version = "3.20"
        self.cpp_standard = "20"

    def generate_cmake(self, targets: list[BazelTarget], output_path: Path):
        """Generate CMakeLists.txt from targets"""
        lines = []

        lines.extend(self._generate_header())
        lines.append("")

        external_deps = self._find_external_deps(targets)
        if external_deps:
            lines.extend(self._generate_find_package_section(external_deps))
            lines.append("")

        for target in targets:
            lines.extend(self._generate_target(target))
            lines.append("")

        library_targets = [t for t in targets if t.rule_type == "cc_library"]
        if library_targets:
            lines.extend(self._generate_install_rules(library_targets))

        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))

    def _generate_header(self) -> list[str]:
        """Generate CMakeLists.txt header"""
        return [
            f"cmake_minimum_required(VERSION {self.cmake_minimum_version})",
            f"project({self.project_name} LANGUAGES CXX)",
            "",
            f"set(CMAKE_CXX_STANDARD {self.cpp_standard})",
            "set(CMAKE_CXX_STANDARD_REQUIRED ON)",
            "set(CMAKE_CXX_EXTENSIONS OFF)",
            "",
            "# Enable testing",
            "include(CTest)",
            "enable_testing()"
        ]

    def _find_external_deps(self, targets: list[BazelTarget]) -> set[str]:
        """Find external dependencies"""
        external_deps = set()

        for target in targets:
            for dep in target.deps:
                if dep.startswith("@"):
                    if "googletest" in dep or "gtest" in dep:
                        external_deps.add("GTest")

        return external_deps

    def _generate_find_package_section(self, external_deps: set[str]) -> list[str]:
        """Generate external dependencies section"""
        lines = ["# External dependencies"]

        if "GTest" in external_deps:
            lines.extend([
                "include(FetchContent)",
                "",
                "# Fetch GoogleTest",
                "FetchContent_Declare(",
                "    googletest",
                "    GIT_REPOSITORY https://github.com/google/googletest.git",
                "    GIT_TAG        v1.14.0",
                ")",
                "FetchContent_MakeAvailable(googletest)"
            ])

        return lines

    def _generate_target(self, target: BazelTarget) -> list[str]:
        """Generate CMake target"""
        lines = [f"# {target.rule_type}: {target.name}"]

        if target.rule_type == "cc_library":
            return self._generate_library_target(target)
        elif target.rule_type == "cc_test":
            return self._generate_test_target(target)
        elif target.rule_type == "cc_binary":
            return self._generate_binary_target(target)

        return lines

    def _generate_library_target(self, target: BazelTarget) -> list[str]:
        """Generate CMake library target"""
        lines = [f"# Library: {target.name}"]

        # Determine if header-only
        is_header_only = not target.srcs and target.hdrs

        if is_header_only:
            lines.append(f"add_library({target.name} INTERFACE)")

            if target.hdrs:
                # INTERFACE libraries use target_sources
                lines.append(f"target_sources({target.name} INTERFACE")
                for hdr in target.hdrs:
                    lines.append(f"    ${{CMAKE_CURRENT_SOURCE_DIR}}/{hdr}")
                lines.append(")")

            lines.append(f"target_include_directories({target.name} INTERFACE")
            lines.append("    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>")
            lines.append("    $<INSTALL_INTERFACE:include>")
            lines.append(")")

        else:
            # Regular library with sources
            sources = target.srcs + target.hdrs
            lines.append(f"add_library({target.name}")
            for src in sources:
                lines.append(f"    {src}")
            lines.append(")")

            lines.append(f"target_include_directories({target.name} PUBLIC")
            lines.append("    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>")
            lines.append("    $<INSTALL_INTERFACE:include>")
            lines.append(")")

        # Add dependencies
        if target.deps:
            cmake_deps = self._convert_deps_to_cmake(target.deps)
            if cmake_deps:
                scope = "INTERFACE" if is_header_only else "PUBLIC"
                lines.append(f"target_link_libraries({target.name} {scope}")
                for dep in cmake_deps:
                    lines.append(f"    {dep}")
                lines.append(")")

        return lines

    def _generate_test_target(self, target: BazelTarget) -> list[str]:
        """Generate CMake test target"""
        lines = [f"# Test: {target.name}"]

        lines.append(f"add_executable({target.name}")
        for src in target.srcs:
            lines.append(f"    {src}")
        lines.append(")")

        cmake_deps = self._convert_deps_to_cmake(target.deps)
        if cmake_deps:
            lines.append(f"target_link_libraries({target.name}")
            for dep in cmake_deps:
                lines.append(f"    {dep}")
            lines.append(")")

        lines.append(f"add_test(NAME {target.name} COMMAND {target.name})")

        return lines

    def _generate_binary_target(self, target: BazelTarget) -> list[str]:
        """Generate CMake binary target"""
        lines = [f"# Binary: {target.name}"]

        lines.append(f"add_executable({target.name}")
        for src in target.srcs:
            lines.append(f"    {src}")
        lines.append(")")

        cmake_deps = self._convert_deps_to_cmake(target.deps)
        if cmake_deps:
            lines.append(f"target_link_libraries({target.name}")
            for dep in cmake_deps:
                lines.append(f"    {dep}")
            lines.append(")")

        return lines

    def _convert_deps_to_cmake(self, bazel_deps: list[str]) -> list[str]:
        """Convert Bazel dependencies to CMake targets"""
        cmake_deps = []

        for dep in bazel_deps:
            if dep.startswith(":"):
                cmake_deps.append(dep[1:])  # Remove ':'
            elif dep.startswith("//"):
                target_name = dep.split(":")[-1] if ":" in dep else dep.split("/")[-1]
                cmake_deps.append(target_name)
            elif "@com_google_googletest//:gtest_main" in dep:
                cmake_deps.append("GTest::gtest_main")
            elif "@com_google_googletest//:gtest" in dep:
                cmake_deps.append("GTest::gtest")
            elif dep.startswith("@"):
                if "googletest" in dep or "gtest" in dep:
                    if "main" in dep:
                        cmake_deps.append("GTest::gtest_main")
                    else:
                        cmake_deps.append("GTest::gtest")

        return cmake_deps

    def _generate_install_rules(self, library_targets: list[BazelTarget]) -> list[str]:
        """Generate install rules"""
        lines = ["# Install rules"]

        for target in library_targets:
            if target.hdrs:
                lines.append("install(FILES")
                for hdr in target.hdrs:
                    lines.append(f"    {hdr}")
                lines.append("    DESTINATION include)")

        target_names = [t.name for t in library_targets]
        if target_names:
            lines.append("install(TARGETS")
            for name in target_names:
                lines.append(f"    {name}")
            lines.append("    EXPORT ${PROJECT_NAME}Targets")
            lines.append("    LIBRARY DESTINATION lib")
            lines.append("    ARCHIVE DESTINATION lib")
            lines.append("    RUNTIME DESTINATION bin")
            lines.append("    INCLUDES DESTINATION include)")

        return lines


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Convert Bazel BUILD.bazel to CMakeLists.txt"
    )
    parser.add_argument(
        "--build-file",
        type=Path,
        default="BUILD.bazel",
        help="Path to BUILD.bazel file (default: BUILD.bazel)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default="CMakeLists.txt",
        help="Output CMakeLists.txt file (default: CMakeLists.txt)"
    )
    parser.add_argument(
        "--project-name",
        default="strong_typedefs",
        help="CMake project name (default: strong_typedefs)"
    )

    args = parser.parse_args()

    if not args.build_file.exists():
        print(f"Error: BUILD file not found: {args.build_file}")
        return 1

    # Parse Bazel BUILD file
    parser = BazelParser()
    targets = parser.parse_file(args.build_file)

    if not targets:
        print("No targets found in BUILD file")
        return 1

    print(f"Found {len(targets)} targets:")
    for target in targets:
        print(f"  - {target.rule_type}: {target.name}")

    # Generate CMakeLists.txt
    generator = CMakeGenerator(args.project_name)
    generator.generate_cmake(targets, args.output)

    print(f"Generated {args.output}")
    return 0


if __name__ == "__main__":
    exit(main())
