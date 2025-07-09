"""
Test script for the Bazel to CMake converter
"""

import subprocess
import tempfile
import textwrap
from pathlib import Path


def test_simple_library():
    """Test conversion of a simple library"""

    # Create a test BUILD file
    build_content = textwrap.dedent("""
        load("@rules_cc//cc:cc_library.bzl", "cc_library")
        load("@rules_cc//cc:cc_test.bzl", "cc_test")

        cc_library(
            name = "my_lib",
            hdrs = ["my_lib.h"],
            srcs = ["my_lib.cc"],
            visibility = ["//visibility:public"],
        )

        cc_test(
            name = "my_lib_test",
            srcs = ["my_lib_test.cc"],
            deps = [
                ":my_lib",
                "@com_google_googletest//:gtest_main",
            ],
        )
    """)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        build_file = tmpdir / "BUILD.bazel"
        cmake_file = tmpdir / "CMakeLists.txt"

        build_file.write_text(build_content)

        # Run the converter
        result = subprocess.run([
            "python3", "bazel_to_cmake.py",
            "--build-file", str(build_file),
            "--output", str(cmake_file),
            "--project-name", "test_project"
        ], capture_output=True, text=True)

        # Assert on failures only
        assert result.returncode == 0, f"Converter failed with code {result.returncode}:\n{result.stderr}"
        assert cmake_file.exists(), "CMakeLists.txt was not generated!"

        # Verify basic content exists
        cmake_content = cmake_file.read_text()
        assert "project(test_project" in cmake_content, "Project name not found in CMakeLists.txt"

        # Verify library target is created with correct sources
        assert "add_library(my_lib" in cmake_content, "Library target not found"
        lib_section = _extract_target_section(cmake_content, "add_library(my_lib")
        assert "my_lib.cc" in lib_section, "Library source file not included in target"
        assert "my_lib.h" in lib_section, "Library header file not included in target"
        assert "target_include_directories(my_lib PUBLIC" in cmake_content, "Library include directories not set correctly"

        # Verify test target is created with correct sources and dependencies
        assert "add_executable(my_lib_test" in cmake_content, "Test target not found"
        test_section = _extract_target_section(cmake_content, "add_executable(my_lib_test")
        assert "my_lib_test.cc" in test_section, "Test source file not included in target"

        # Verify test target has correct dependencies
        test_link_section = _extract_target_section(cmake_content, "target_link_libraries(my_lib_test")
        assert "my_lib" in test_link_section, "Library dependency not linked to test"
        assert "GTest::gtest_main" in test_link_section, "GoogleTest dependency not linked to test"

        # Verify CTest integration
        assert "add_test(NAME my_lib_test COMMAND my_lib_test)" in cmake_content, "CTest integration not correct"


def _extract_target_section(content: str, start_marker: str) -> str:
    """Extract a target section from CMakeLists.txt content"""
    lines = content.split('\n')
    section_lines = []
    in_section = False
    paren_count = 0

    for line in lines:
        if start_marker in line:
            in_section = True
            section_lines.append(line)
            paren_count += line.count('(') - line.count(')')
        elif in_section:
            section_lines.append(line)
            paren_count += line.count('(') - line.count(')')
            if paren_count <= 0:
                break

    return '\n'.join(section_lines)


def test_missing_file():
    """Test that missing BUILD file raises proper error"""
    result = subprocess.run([
        "python3", "bazel_to_cmake.py",
        "--build-file", "nonexistent.bazel",
        "--output", "output.txt"
    ], capture_output=True, text=True)

    assert result.returncode != 0, "Expected failure for missing BUILD file"


def test_invalid_build_file():
    """Test that invalid BUILD file syntax raises proper error"""
    invalid_content = "this is not valid python syntax {"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        build_file = tmpdir / "BUILD.bazel"
        cmake_file = tmpdir / "CMakeLists.txt"

        build_file.write_text(invalid_content)

        result = subprocess.run([
            "python3", "bazel_to_cmake.py",
            "--build-file", str(build_file),
            "--output", str(cmake_file)
        ], capture_output=True, text=True)

        assert result.returncode != 0, "Expected failure for invalid BUILD file"


def test_multiple_targets_with_dependencies():
    """Test conversion with multiple targets and complex dependencies"""

    build_content = textwrap.dedent("""
        load("@rules_cc//cc:cc_library.bzl", "cc_library")
        load("@rules_cc//cc:cc_test.bzl", "cc_test")
        load("@rules_cc//cc:cc_binary.bzl", "cc_binary")

        cc_library(
            name = "base_lib",
            hdrs = ["base.h"],
            srcs = ["base.cc"],
        )

        cc_library(
            name = "utils",
            hdrs = ["utils.h"],
            deps = [":base_lib"],
        )

        cc_test(
            name = "utils_test",
            srcs = ["utils_test.cc"],
            deps = [
                ":utils",
                ":base_lib",
                "@com_google_googletest//:gtest_main",
            ],
        )

        cc_binary(
            name = "main_app",
            srcs = ["main.cc"],
            deps = [":utils", ":base_lib"],
        )
    """)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        build_file = tmpdir / "BUILD.bazel"
        cmake_file = tmpdir / "CMakeLists.txt"

        build_file.write_text(build_content)

        result = subprocess.run([
            "python3", "bazel_to_cmake.py",
            "--build-file", str(build_file),
            "--output", str(cmake_file),
            "--project-name", "multi_target_project"
        ], capture_output=True, text=True)

        assert result.returncode == 0, f"Converter failed with code {result.returncode}:\n{result.stderr}"
        assert cmake_file.exists(), "CMakeLists.txt was not generated!"

        cmake_content = cmake_file.read_text()

        # Verify base_lib (regular library with sources and headers)
        assert "add_library(base_lib" in cmake_content, "base_lib target not found"
        base_lib_section = _extract_target_section(cmake_content, "add_library(base_lib")
        assert "base.cc" in base_lib_section, "base.cc not in base_lib target"
        assert "base.h" in base_lib_section, "base.h not in base_lib target"
        assert "target_include_directories(base_lib PUBLIC" in cmake_content, "base_lib include dirs not set"

        # Verify utils (header-only library with dependency)
        assert "add_library(utils INTERFACE)" in cmake_content, "utils not created as INTERFACE library"
        utils_section = _extract_target_section(cmake_content, "target_sources(utils INTERFACE")
        assert "utils.h" in utils_section, "utils.h not in utils target sources"
        utils_link_section = _extract_target_section(cmake_content, "target_link_libraries(utils INTERFACE")
        assert "base_lib" in utils_link_section, "base_lib dependency not linked to utils"

        # Verify utils_test (test executable with multiple dependencies)
        assert "add_executable(utils_test" in cmake_content, "utils_test target not found"
        test_section = _extract_target_section(cmake_content, "add_executable(utils_test")
        assert "utils_test.cc" in test_section, "utils_test.cc not in test target"
        test_link_section = _extract_target_section(cmake_content, "target_link_libraries(utils_test")
        assert "utils" in test_link_section, "utils dependency not linked to test"
        assert "base_lib" in test_link_section, "base_lib dependency not linked to test"
        assert "GTest::gtest_main" in test_link_section, "GoogleTest not linked to test"
        assert "add_test(NAME utils_test COMMAND utils_test)" in cmake_content, "CTest not configured"

        # Verify main_app (binary with multiple dependencies)
        assert "add_executable(main_app" in cmake_content, "main_app target not found"
        app_section = _extract_target_section(cmake_content, "add_executable(main_app")
        assert "main.cc" in app_section, "main.cc not in main_app target"
        app_link_section = _extract_target_section(cmake_content, "target_link_libraries(main_app")
        assert "utils" in app_link_section, "utils dependency not linked to main_app"
        assert "base_lib" in app_link_section, "base_lib dependency not linked to main_app"


def test_header_only_library():
    """Test that header-only libraries are correctly identified and created as INTERFACE targets"""

    build_content = textwrap.dedent("""
        load("@rules_cc//cc:cc_library.bzl", "cc_library")

        cc_library(
            name = "header_only",
            hdrs = ["template_lib.h", "inline_funcs.h"],
            visibility = ["//visibility:public"],
        )
    """)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        build_file = tmpdir / "BUILD.bazel"
        cmake_file = tmpdir / "CMakeLists.txt"

        build_file.write_text(build_content)

        result = subprocess.run([
            "python3", "bazel_to_cmake.py",
            "--build-file", str(build_file),
            "--output", str(cmake_file),
            "--project-name", "header_only_project"
        ], capture_output=True, text=True)

        assert result.returncode == 0, f"Converter failed: {result.stderr}"
        cmake_content = cmake_file.read_text()

        # Verify it's created as INTERFACE library
        assert "add_library(header_only INTERFACE)" in cmake_content, "Header-only lib not created as INTERFACE"

        # Verify headers are added via target_sources
        sources_section = _extract_target_section(cmake_content, "target_sources(header_only INTERFACE")
        assert "template_lib.h" in sources_section, "template_lib.h not in target sources"
        assert "inline_funcs.h" in sources_section, "inline_funcs.h not in target sources"

        # Verify INTERFACE include directories
        assert "target_include_directories(header_only INTERFACE" in cmake_content, "INTERFACE include dirs not set"
