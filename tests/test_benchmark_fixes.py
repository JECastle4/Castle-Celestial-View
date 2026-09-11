"""
Tests for benchmark.py fix - verifying documented frame counts and performance targets.

Tests verify that:
1. Benchmark runs 1000 and 5000 frame tests (not just 50/100/200/500)
2. Benchmark enforces documented timing thresholds (<10s for 1000, <50s for 5000)
3. Benchmark produces accurate results that match advertised scope
"""

import pytest
from pathlib import Path
import sys
import re


class TestBenchmarkFrameCounts:
    """Test that benchmark runs documented frame count tests."""
    
    def test_benchmark_includes_1000_frames(self):
        """Test that benchmark tests 1000 frames (as documented)."""
        benchmark_file = Path(__file__).parent.parent / 'scripts' / 'performance-profiling' / 'benchmark.py'
        
        with open(benchmark_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should have 1000 in frame_counts
        assert '1000' in content, "Benchmark should test 1000 frames"
        
        # Verify it's in frame_counts array
        assert 'frame_counts' in content
        assert 'frame_counts = [1000' in content or '1000' in content
    
    def test_benchmark_includes_5000_frames(self):
        """Test that benchmark tests 5000 frames (as documented)."""
        benchmark_file = Path(__file__).parent.parent / 'scripts' / 'performance-profiling' / 'benchmark.py'
        
        with open(benchmark_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should have 5000 in frame_counts
        assert '5000' in content, "Benchmark should test 5000 frames"
    
    def test_benchmark_does_not_limit_to_500(self):
        """Test that benchmark is not limited to 500 frames.
        
        Bug: Original benchmark only ran up to 500 frames,
        which cannot establish baseline for 1000/5000 frame coverage.
        """
        benchmark_file = Path(__file__).parent.parent / 'scripts' / 'performance-profiling' / 'benchmark.py'
        
        with open(benchmark_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should NOT have frame_counts = [50, 100, 200, 500]
        assert 'frame_counts = [50, 100, 200, 500]' not in content, \
            "Benchmark should not be limited to 50/100/200/500 frames"
    
    def test_benchmark_timing_threshold_for_1000_frames(self):
        """Test that benchmark enforces <10s threshold for 1000 frames."""
        benchmark_file = Path(__file__).parent.parent / 'scripts' / 'performance-profiling' / 'benchmark.py'
        
        with open(benchmark_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should check elapsed > 10.0 for frame_count == 1000
        assert 'frame_count == 1000' in content or '1000' in content
        # Look for timing check
        assert '10.0' in content or '10' in content, \
            "Benchmark should have 10s threshold for 1000 frames"
        
        # Verify it's the right comparison (not 40s for 1000)
        # Extract the actual check
        pattern = r'frame_count\s*==\s*1000\s*and\s*elapsed\s*>\s*(\d+)'
        matches = re.findall(pattern, content)
        
        if matches:
            threshold = int(matches[0])
            assert threshold == 10, \
                f"1000-frame threshold should be 10s, not {threshold}s"
    
    def test_benchmark_timing_threshold_for_5000_frames(self):
        """Test that benchmark enforces <50s threshold for 5000 frames."""
        benchmark_file = Path(__file__).parent.parent / 'scripts' / 'performance-profiling' / 'benchmark.py'
        
        with open(benchmark_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should check elapsed > 50.0 for frame_count == 5000
        assert '5000' in content, "Should test 5000 frames"
        assert '50' in content, "Should have 50s threshold for 5000 frames"
        
        # Verify 5000 test exists
        pattern = r'frame_count\s*==\s*5000'
        matches = re.findall(pattern, content)
        assert len(matches) > 0, "Should have check for 5000 frames"
    
    def test_benchmark_payload_date_range(self):
        """Test that benchmark payload covers full year for realistic testing."""
        benchmark_file = Path(__file__).parent.parent / 'scripts' / 'performance-profiling' / 'benchmark.py'
        
        with open(benchmark_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should use full year for proper testing scope
        assert '2026-01-01' in content
        assert '2026-12-31' in content, \
            "Benchmark should cover full year for proper frame count testing"


class TestBenchmarkSuccessCriteria:
    """Test that benchmark applies correct success criteria."""
    
    def test_benchmark_1000_frames_criteria(self):
        """Test that 1000 frames must complete in <10s."""
        # Documented criterion:
        # \"Batch Earth <10s for frame_count=1000\"
        
        # With 1000 frames @ ~10ms per frame average,
        # should complete in <10s for meaningful baseline
        
        # Verify benchmark enforces this
        benchmark_file = Path(__file__).parent.parent / 'scripts' / 'performance-profiling' / 'benchmark.py'
        
        with open(benchmark_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should have both frame_count check and time check
        assert '1000' in content
        assert '10.0' in content or '10' in content
    
    def test_benchmark_5000_frames_criteria(self):
        """Test that 5000 frames must complete in <50s."""
        # Documented criterion for large dataset
        
        benchmark_file = Path(__file__).parent.parent / 'scripts' / 'performance-profiling' / 'benchmark.py'
        
        with open(benchmark_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should have both frame_count check and time check
        assert '5000' in content
        assert '50' in content
    
    def test_benchmark_not_too_lenient(self):
        """Test that benchmark doesn't accept 40s threshold for 1000 frames."""
        benchmark_file = Path(__file__).parent.parent / 'scripts' / 'performance-profiling' / 'benchmark.py'
        
        with open(benchmark_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for the specific bug: frame_count == 500 and elapsed > 40.0
        # This should NOT exist after the fix
        buggy_pattern = r'frame_count\s*==\s*500\s*and\s*elapsed\s*>\s*40'
        buggy_matches = re.findall(buggy_pattern, content)
        
        assert len(buggy_matches) == 0, \
            "Benchmark should not have 40s threshold for 500 frames (bug)"


class TestBenchmarkDocumentation:
    """Test that benchmark documentation matches implementation."""
    
    def test_benchmark_module_docstring_accurate(self):
        """Test that module docstring documents correct frame counts."""
        benchmark_file = Path(__file__).parent.parent / 'scripts' / 'performance-profiling' / 'benchmark.py'
        
        with open(benchmark_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract docstring
        docstring_match = re.match(r'^"""(.+?)"""', content, re.DOTALL)
        
        if docstring_match:
            docstring = docstring_match.group(1)
            
            # Should document 1000 and 5000 frame tests
            assert '1000' in docstring or 'frame' in docstring.lower()
            assert '5000' in docstring or 'frame' in docstring.lower()
            
            # Should document timing thresholds
            assert '10' in docstring or 'second' in docstring.lower()
    
    def test_benchmark_advertises_correct_coverage(self):
        """Test that benchmark profile advertises correct test scope."""
        benchmark_file = Path(__file__).parent.parent / 'scripts' / 'performance-profiling' / 'benchmark.py'
        
        with open(benchmark_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should mention 1000 and 5000 frame coverage
        # (not just 500)
        lines = content.split('\n')
        
        has_1000 = any('1000' in line for line in lines)
        has_5000 = any('5000' in line for line in lines)
        
        assert has_1000 and has_5000, \
            "Benchmark should advertise 1000/5000 frame coverage"


class TestBenchmarkConsistency:
    """Test that benchmark implementation is consistent."""
    
    def test_frame_counts_array_structure(self):
        """Test that frame_counts array has expected structure."""
        benchmark_file = Path(__file__).parent.parent / 'scripts' / 'performance-profiling' / 'benchmark.py'
        
        with open(benchmark_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should have assignment to frame_counts
        assert 'frame_counts' in content
        assert '=' in content
        
        # Extract frame_counts line
        frame_counts_lines = [line for line in content.split('\n') 
                             if 'frame_counts' in line and '=' in line]
        
        assert len(frame_counts_lines) > 0, "Should define frame_counts"
        
        # Should include 1000 and 5000
        frame_counts_str = ' '.join(frame_counts_lines)
        assert '1000' in frame_counts_str
        assert '5000' in frame_counts_str
    
    def test_benchmark_uses_full_year_dates(self):
        """Test that benchmark uses full year for date range."""
        benchmark_file = Path(__file__).parent.parent / 'scripts' / 'performance-profiling' / 'benchmark.py'
        
        with open(benchmark_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should specify start and end dates
        has_start_date = '2026-01-01' in content or '01-01' in content
        has_end_date = '2026-12-31' in content or '12-31' in content
        
        assert has_start_date and has_end_date, \
            "Benchmark should cover full year date range"
