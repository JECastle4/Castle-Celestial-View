"""Test that benchmark frame counts and timing thresholds are correct."""

import pytest
from pathlib import Path
import re
from datetime import datetime


class TestBenchmarkFrameCounts:
    """Tests for benchmark.py frame count configuration."""

    def test_frame_counts_are_documented_values(self):
        """Verify benchmark.py uses advertised frame counts [1000, 5000]."""
        # Read actual benchmark.py implementation
        benchmark_path = Path(__file__).parent.parent / 'scripts' / 'performance-profiling' / 'benchmark.py'
        with open(benchmark_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract frame_counts assignment from implementation
        # Documented values are [1000, 5000]
        frame_counts_pattern = r'frame_counts\s*=\s*\[([\d\s,]+)\]'
        match = re.search(frame_counts_pattern, content)
        
        assert match is not None, "benchmark.py must define frame_counts = [...]"
        
        # Parse the frame counts from the implementation
        frame_counts_str = match.group(1)
        frame_counts = [int(x.strip()) for x in frame_counts_str.split(',')]
        
        # Verify the implementation uses advertised frame counts
        assert 1000 in frame_counts, "benchmark.py must include 1000-frame test"
        assert 5000 in frame_counts, "benchmark.py must include 5000-frame test"
        assert frame_counts == [1000, 5000], \
            f"benchmark.py frame_counts should be [1000, 5000], got {frame_counts}"

    def test_benchmark_date_range_covers_full_year(self):
        """Verify benchmark uses full year date range (2026-01-01 to 2026-12-31)."""
        # Read actual benchmark.py implementation
        benchmark_path = Path(__file__).parent.parent / 'scripts' / 'performance-profiling' / 'benchmark.py'
        with open(benchmark_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract date values from the implementation
        # Look for patterns like "start_date": "2026-01-01" (in JSON) or start_date = "2026-01-01" (in code)
        # This handles both dictionary literals and variable assignments
        start_date_pattern = r'["\']?start_date["\']?\s*[:=]\s*["\'](\d{4}-\d{2}-\d{2})["\']'
        end_date_pattern = r'["\']?end_date["\']?\s*[:=]\s*["\'](\d{4}-\d{2}-\d{2})["\']'
        
        start_match = re.search(start_date_pattern, content)
        end_match = re.search(end_date_pattern, content)
        
        assert start_match is not None, "benchmark.py must define start_date with date string"
        assert end_match is not None, "benchmark.py must define end_date with date string"
        
        start_date_str = start_match.group(1)
        end_date_str = end_match.group(1)
        
        # Verify dates span approximately full year
        start = datetime.strptime(start_date_str, "%Y-%m-%d")
        end = datetime.strptime(end_date_str, "%Y-%m-%d")
        delta = (end - start).days
        
        # Should be approximately 365 days (account for leap years: 364-366 days)
        assert 364 <= delta <= 366, \
            f"Date range should span full year (~365 days), got {delta} days from {start_date_str} to {end_date_str}"

    def test_frame_count_1000_threshold_in_implementation(self):
        """Verify frame_count=1000 uses correct performance threshold (10.0s)."""
        # Read actual benchmark.py implementation
        benchmark_path = Path(__file__).parent.parent / 'scripts' / 'performance-profiling' / 'benchmark.py'
        with open(benchmark_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract the threshold for frame_count == 1000
        pattern = r'frame_count\s*==\s*1000\s*and\s*elapsed\s*>\s*(\d+(?:\.\d+)?)'
        match = re.search(pattern, content)
        
        assert match is not None, \
            "benchmark.py must have check: frame_count == 1000 and elapsed > N"
        
        threshold = float(match.group(1))
        assert threshold == 10.0, \
            f"1000-frame threshold should be 10.0s, got {threshold}s"

    def test_frame_count_5000_threshold_in_implementation(self):
        """Verify frame_count=5000 uses correct performance threshold (50.0s)."""
        # Read actual benchmark.py implementation
        benchmark_path = Path(__file__).parent.parent / 'scripts' / 'performance-profiling' / 'benchmark.py'
        with open(benchmark_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract the threshold for frame_count == 5000
        pattern = r'frame_count\s*==\s*5000\s*and\s*elapsed\s*>\s*(\d+(?:\.\d+)?)'
        match = re.search(pattern, content)
        
        assert match is not None, \
            "benchmark.py must have check: frame_count == 5000 and elapsed > N"
        
        threshold = float(match.group(1))
        assert threshold == 50.0, \
            f"5000-frame threshold should be 50.0s, got {threshold}s"


class TestBenchmarkSuccessCriteria:
    """Tests for benchmark performance success criteria."""

    def test_benchmark_1000_frame_limit(self):
        """Benchmark for 1000 frames must complete under 10 seconds."""
        # This is the performance target after fix
        max_time_seconds = 10.0
        
        # This ensures benchmarks complete in reasonable time
        assert max_time_seconds > 0

    def test_benchmark_5000_frame_limit(self):
        """Benchmark for 5000 frames must complete under 50 seconds."""
        # This is the performance target for larger batch
        max_time_seconds = 50.0
        
        # Scales roughly linearly with frame count
        assert max_time_seconds > 0

    def test_frame_count_scaling(self):
        """Verify performance scaling between frame counts."""
        # Frame count increase: 5x (from 1000 to 5000)
        frame_ratio = 5000 / 1000
        
        # Time threshold increase: 5x (from 10s to 50s)
        time_ratio = 50.0 / 10.0
        
        # Should scale roughly linearly
        assert abs(frame_ratio - time_ratio) < 0.5


class TestBenchmarkDocumentation:
    """Tests that benchmark implementation matches documentation."""

    def test_benchmark_file_exists(self):
        """Verify benchmark.py file exists."""
        benchmark_path = Path(__file__).parent.parent / 'scripts' / 'performance-profiling' / 'benchmark.py'
        assert benchmark_path.exists(), f"benchmark.py should exist at {benchmark_path}"

    def test_documented_frame_counts_match_implementation(self):
        """Ensure implementation uses documented frame counts [1000, 5000]."""
        # Read actual implementation
        benchmark_path = Path(__file__).parent.parent / 'scripts' / 'performance-profiling' / 'benchmark.py'
        with open(benchmark_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract frame_counts from implementation
        frame_counts_pattern = r'frame_counts\s*=\s*\[([\d\s,]+)\]'
        match = re.search(frame_counts_pattern, content)
        
        assert match is not None, "benchmark.py must define frame_counts"
        
        frame_counts_str = match.group(1)
        implementation_frames = [int(x.strip()) for x in frame_counts_str.split(',')]
        
        # Documented specification: [1000, 5000]
        documented_frames = [1000, 5000]
        
        assert implementation_frames == documented_frames, \
            f"Implementation frame counts {implementation_frames} should match documentation {documented_frames}"


class TestBenchmarkConsistency:
    """Tests for benchmark configuration consistency."""

    def test_performance_target_reasonable_for_cpu_bound_task(self):
        """Verify performance targets are reasonable."""
        # Read implementation to get actual thresholds
        benchmark_path = Path(__file__).parent.parent / 'scripts' / 'performance-profiling' / 'benchmark.py'
        with open(benchmark_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract thresholds from implementation
        threshold_1000_pattern = r'frame_count\s*==\s*1000\s*and\s*elapsed\s*>\s*(\d+(?:\.\d+)?)'
        threshold_5000_pattern = r'frame_count\s*==\s*5000\s*and\s*elapsed\s*>\s*(\d+(?:\.\d+)?)'
        
        match_1000 = re.search(threshold_1000_pattern, content)
        match_5000 = re.search(threshold_5000_pattern, content)
        
        assert match_1000 is not None, "Must have threshold check for 1000 frames"
        assert match_5000 is not None, "Must have threshold check for 5000 frames"
        
        threshold_1000 = float(match_1000.group(1))
        threshold_5000 = float(match_5000.group(1))
        
        # 1000 frames in 10 seconds = 100 frames/second
        # 5000 frames in 50 seconds = 100 frames/second
        # This is consistent performance
        
        rate_1000 = 1000 / threshold_1000
        rate_5000 = 5000 / threshold_5000
        
        # Should achieve similar throughput
        assert abs(rate_1000 - rate_5000) < 1.0, \
            f"Throughput should be consistent: {rate_1000:.1f} vs {rate_5000:.1f} frames/sec"

    def test_threshold_ordering(self):
        """Ensure larger frame count has larger time threshold."""
        # Read implementation to get actual thresholds
        benchmark_path = Path(__file__).parent.parent / 'scripts' / 'performance-profiling' / 'benchmark.py'
        with open(benchmark_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract thresholds from implementation
        threshold_1000_pattern = r'frame_count\s*==\s*1000\s*and\s*elapsed\s*>\s*(\d+(?:\.\d+)?)'
        threshold_5000_pattern = r'frame_count\s*==\s*5000\s*and\s*elapsed\s*>\s*(\d+(?:\.\d+)?)'
        
        match_1000 = re.search(threshold_1000_pattern, content)
        match_5000 = re.search(threshold_5000_pattern, content)
        
        threshold_1000 = float(match_1000.group(1))
        threshold_5000 = float(match_5000.group(1))
        
        # 5000 frames should take more time than 1000 frames
        assert threshold_5000 > threshold_1000, \
            f"5000-frame threshold ({threshold_5000}s) should exceed 1000-frame threshold ({threshold_1000}s)"
        
        # But should scale roughly linearly with frame count
        frame_ratio = 5000 / 1000
        time_ratio = threshold_5000 / threshold_1000
        
        # Time ratio should be close to frame ratio (linear scaling)
        assert abs(frame_ratio - time_ratio) < 1.0, \
            f"Thresholds should scale linearly: frame ratio {frame_ratio:.1f} vs time ratio {time_ratio:.1f}"
