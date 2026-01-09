"""
Property-based tests for file format validation.

Feature: menu-image-analyzer, Property 1: File Format Validation
"""

import pytest
from hypothesis import given, strategies as st
from app.app import allowed_file


class TestFileFormatValidationProperty:
    """Property-based tests for file format validation."""
    
    @given(st.sampled_from(['jpg', 'jpeg', 'png', 'webp', 'JPG', 'JPEG', 'PNG', 'WEBP']))
    def test_valid_extensions_accepted(self, extension):
        """
        Property 1: File Format Validation - Valid Extensions
        
        For any valid image format (JPEG, PNG, WebP), the system should accept the file.
        **Validates: Requirements 1.1, 1.5**
        """
        allowed_extensions = {'png', 'jpg', 'jpeg', 'webp'}
        filename = f"test_image.{extension}"
        
        result = allowed_file(filename, allowed_extensions)
        assert result is True, f"Valid extension {extension} should be accepted"
    
    @given(st.sampled_from(['txt', 'pdf', 'doc', 'gif', 'bmp', 'tiff', 'svg', 'exe', 'zip']))
    def test_invalid_extensions_rejected(self, extension):
        """
        Property 1: File Format Validation - Invalid Extensions
        
        For any invalid file format, the system should reject the file.
        **Validates: Requirements 1.1, 1.5**
        """
        allowed_extensions = {'png', 'jpg', 'jpeg', 'webp'}
        filename = f"test_file.{extension}"
        
        result = allowed_file(filename, allowed_extensions)
        assert result is False, f"Invalid extension {extension} should be rejected"
    
    @given(st.text(min_size=1, max_size=50).filter(lambda x: '.' not in x))
    def test_files_without_extension_rejected(self, filename):
        """
        Property 1: File Format Validation - No Extension
        
        For any filename without an extension, the system should reject the file.
        **Validates: Requirements 1.1, 1.5**
        """
        allowed_extensions = {'png', 'jpg', 'jpeg', 'webp'}
        
        result = allowed_file(filename, allowed_extensions)
        assert result is False, f"File without extension '{filename}' should be rejected"
    
    @given(st.text(min_size=1, max_size=20), st.sampled_from(['jpg', 'png', 'webp']))
    def test_valid_filenames_with_valid_extensions(self, base_name, extension):
        """
        Property 1: File Format Validation - Valid Combinations
        
        For any valid filename with a valid extension, the system should accept the file.
        **Validates: Requirements 1.1, 1.5**
        """
        # Filter out problematic characters that might cause issues
        if not base_name.strip() or any(c in base_name for c in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']):
            return
        
        allowed_extensions = {'png', 'jpg', 'jpeg', 'webp'}
        filename = f"{base_name.strip()}.{extension}"
        
        result = allowed_file(filename, allowed_extensions)
        assert result is True, f"Valid filename '{filename}' should be accepted"
    
    def test_empty_filename_rejected(self):
        """
        Property 1: File Format Validation - Empty Filename
        
        Empty filenames should be rejected.
        **Validates: Requirements 1.1, 1.5**
        """
        allowed_extensions = {'png', 'jpg', 'jpeg', 'webp'}
        
        result = allowed_file('', allowed_extensions)
        assert result is False, "Empty filename should be rejected"
    
    def test_dot_only_filename_rejected(self):
        """
        Property 1: File Format Validation - Dot Only
        
        Filenames with only dots should be rejected.
        **Validates: Requirements 1.1, 1.5**
        """
        allowed_extensions = {'png', 'jpg', 'jpeg', 'webp'}
        
        result = allowed_file('.', allowed_extensions)
        assert result is False, "Dot-only filename should be rejected"
        
        result = allowed_file('..', allowed_extensions)
        assert result is False, "Double-dot filename should be rejected"
    
    @given(st.sampled_from(['jpg', 'png', 'webp']))
    def test_case_insensitive_validation(self, extension):
        """
        Property 1: File Format Validation - Case Insensitive
        
        File extension validation should be case insensitive.
        **Validates: Requirements 1.1, 1.5**
        """
        allowed_extensions = {'png', 'jpg', 'jpeg', 'webp'}
        
        # Test various case combinations
        test_cases = [
            extension.lower(),
            extension.upper(),
            extension.capitalize()
        ]
        
        for ext in test_cases:
            filename = f"test.{ext}"
            result = allowed_file(filename, allowed_extensions)
            assert result is True, f"Extension '{ext}' should be accepted (case insensitive)"