"""
Security utilities for document handling

This module provides security functions for:
- UUID-based filename generation (prevents path traversal)
- Path sanitization
- Secure file storage
- Magic byte validation (prevents MIME type spoofing)
"""
import os
import uuid
import re
from pathlib import Path
import magic


def generate_secure_filename(original_filename):
    """
    Generate a secure filename using UUID to prevent path traversal attacks.
    
    This function:
    1. Generates a unique UUID for the filename
    2. Preserves the original file extension
    3. Ensures no path traversal characters are included
    
    Args:
        original_filename (str): The original filename from upload
        
    Returns:
        str: A secure UUID-based filename with original extension
        
    Example:
        >>> generate_secure_filename("../../etc/passwd")
        "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        
        >>> generate_secure_filename("document.pdf")
        "a1b2c3d4-e5f6-7890-abcd-ef1234567890.pdf"
    """
    # Extract the file extension safely
    _, ext = os.path.splitext(original_filename)
    
    # Sanitize the extension (remove any path traversal attempts)
    ext = sanitize_path_component(ext)
    
    # Generate UUID-based filename
    secure_name = str(uuid.uuid4())
    
    # Add extension if present and valid
    if ext and ext.startswith('.') and len(ext) <= 10:
        # Ensure extension only contains alphanumeric and dot
        if re.match(r'^\.[a-zA-Z0-9]+$', ext):
            secure_name += ext.lower()
    
    return secure_name


def sanitize_path_component(component):
    """
    Sanitize a path component to prevent path traversal attacks.
    
    This function:
    1. Removes any path traversal sequences (../, .., etc.)
    2. Removes absolute path indicators (/, \\, C:, etc.)
    3. Removes null bytes and other dangerous characters
    4. Ensures the result is a safe filename component
    
    Args:
        component (str): A filename or path component to sanitize
        
    Returns:
        str: Sanitized component safe for use in file paths
        
    Example:
        >>> sanitize_path_component("../../etc/passwd")
        "etc_passwd"
        
        >>> sanitize_path_component("C:\\\\Windows\\\\System32")
        "Windows_System32"
    """
    if not component:
        return ""
    
    # Remove null bytes
    component = component.replace('\x00', '')
    
    # Remove or replace dangerous characters
    # Replace path separators with underscores
    component = component.replace('/', '_').replace('\\', '_')
    
    # Remove drive letters (Windows)
    component = re.sub(r'^[a-zA-Z]:', '', component)
    
    # Remove parent directory references
    component = component.replace('..', '')
    
    # Remove leading/trailing dots and spaces
    component = component.strip('. ')
    
    # Replace any remaining problematic characters
    component = re.sub(r'[<>:"|?*]', '_', component)
    
    # Ensure it's not empty after sanitization
    if not component:
        component = "file"
    
    return component


def generate_secure_file_path(company_id, original_filename):
    """
    Generate a complete secure file path for document storage.
    
    This function:
    1. Creates a safe directory structure based on company ID
    2. Generates a UUID-based filename
    3. Ensures the path cannot escape the documents directory
    
    Args:
        company_id: The company ID (UUID or int)
        original_filename (str): The original filename from upload
        
    Returns:
        str: A secure file path relative to storage root
        
    Example:
        >>> generate_secure_file_path("123", "document.pdf")
        "documents/123/a1b2c3d4-e5f6-7890-abcd-ef1234567890.pdf"
    """
    # Sanitize company ID (convert to string and remove dangerous chars)
    safe_company_id = sanitize_path_component(str(company_id))
    
    # Generate secure filename
    secure_filename = generate_secure_filename(original_filename)
    
    # Construct path (always starts with documents/)
    file_path = f"documents/{safe_company_id}/{secure_filename}"
    
    # Verify the path doesn't contain traversal sequences
    # This is a safety check - should never trigger with our sanitization
    if '..' in file_path or file_path.startswith('/') or ':' in file_path:
        raise ValueError("Generated path contains unsafe characters")
    
    return file_path


def validate_file_path(file_path):
    """
    Validate that a file path is safe and within expected boundaries.
    
    This function checks:
    1. Path doesn't contain traversal sequences
    2. Path doesn't start with absolute path indicators
    3. Path is within the documents directory
    
    Args:
        file_path (str): The file path to validate
        
    Returns:
        bool: True if path is safe, False otherwise
        
    Example:
        >>> validate_file_path("documents/123/file.pdf")
        True
        
        >>> validate_file_path("../../etc/passwd")
        False
    """
    if not file_path:
        return False
    
    # Check for path traversal
    if '..' in file_path:
        return False
    
    # Check for absolute paths
    if file_path.startswith('/') or file_path.startswith('\\'):
        return False
    
    # Check for Windows drive letters
    if re.match(r'^[a-zA-Z]:', file_path):
        return False
    
    # Check for null bytes
    if '\x00' in file_path:
        return False
    
    # Ensure path starts with documents/
    if not file_path.startswith('documents/'):
        return False
    
    # Use pathlib to normalize and check the path
    try:
        normalized = Path(file_path).as_posix()
        # After normalization, should still start with documents/
        if not normalized.startswith('documents/'):
            return False
    except (ValueError, OSError):
        return False
    
    return True



def validate_file_type(file):
    """
    Validate file type using magic bytes to prevent MIME type spoofing.
    
    This function:
    1. Reads the file's magic bytes (file signature)
    2. Determines the actual file type regardless of extension or MIME type
    3. Validates against allowed file types
    4. Prevents executable files and scripts from being uploaded
    
    Args:
        file: Django UploadedFile object
        
    Returns:
        tuple: (is_valid, detected_type, error_message)
        
    Raises:
        None - returns validation result as tuple
        
    Example:
        >>> validate_file_type(pdf_file)
        (True, 'application/pdf', None)
        
        >>> validate_file_type(exe_file_disguised_as_pdf)
        (False, 'application/x-dosexec', 'Executable files are not allowed')
    """
    # Allowed MIME types based on magic bytes
    allowed_types = {
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/bmp',
        'image/webp',
        'text/plain',
        'text/csv',
    }
    
    # Dangerous file types that should always be blocked
    dangerous_types = {
        'application/x-dosexec',  # Windows executables
        'application/x-executable',  # Linux executables
        'application/x-mach-binary',  # macOS executables
        'application/x-sharedlib',  # Shared libraries
        'application/x-sh',  # Shell scripts
        'application/x-python',  # Python scripts
        'text/x-python',  # Python scripts (alternative)
        'application/javascript',  # JavaScript
        'text/javascript',  # JavaScript (alternative)
        'application/x-javascript',  # JavaScript (alternative)
        'text/x-shellscript',  # Shell scripts
        'application/x-bat',  # Batch files
        'application/x-msdownload',  # Windows executables
    }
    
    try:
        # Read file content for magic byte detection
        # Save current position
        file.seek(0)
        file_content = file.read()
        file.seek(0)  # Reset position for later use
        
        # Detect MIME type using magic bytes
        mime = magic.Magic(mime=True)
        detected_type = mime.from_buffer(file_content)
        
        # Check if file is empty
        if len(file_content) == 0:
            return (False, detected_type, "Empty files are not allowed")
        
        # Check for dangerous file types
        if detected_type in dangerous_types:
            return (False, detected_type, f"File type '{detected_type}' is not allowed. Executable files and scripts are blocked for security.")
        
        # Check if detected type is in allowed list
        if detected_type not in allowed_types:
            # Some files might be detected as generic types
            # Be more lenient with text files and Office documents
            if detected_type.startswith('text/') and 'text/plain' in allowed_types:
                return (True, detected_type, None)
            elif detected_type == 'application/zip':
                # Office documents are ZIP files, check extension
                filename = getattr(file, 'name', '')
                if filename.endswith(('.docx', '.xlsx', '.pptx')):
                    return (True, detected_type, None)
            
            return (False, detected_type, f"File type '{detected_type}' is not allowed. Allowed types: PDF, Word, Excel, PowerPoint, Images, Text, CSV")
        
        return (True, detected_type, None)
        
    except Exception as e:
        # If magic detection fails, reject the file for safety
        return (False, 'unknown', f"Could not validate file type: {str(e)}")


def validate_file_extension(filename):
    """
    Validate file extension to prevent double extension attacks.
    
    This function:
    1. Checks for multiple extensions (e.g., file.pdf.exe)
    2. Validates the final extension is allowed
    3. Prevents executable extensions
    
    Args:
        filename (str): The filename to validate
        
    Returns:
        tuple: (is_valid, error_message)
        
    Example:
        >>> validate_file_extension("document.pdf")
        (True, None)
        
        >>> validate_file_extension("document.pdf.exe")
        (False, "Executable extensions are not allowed")
    """
    # Dangerous extensions that should always be blocked
    dangerous_extensions = {
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
        '.jar', '.app', '.deb', '.rpm', '.dmg', '.pkg', '.sh', '.py',
        '.rb', '.pl', '.php', '.asp', '.aspx', '.jsp', '.dll', '.so',
        '.dylib', '.msi', '.apk'
    }
    
    # Allowed extensions
    allowed_extensions = {
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',
        '.txt', '.csv'
    }
    
    # Convert to lowercase for comparison
    filename_lower = filename.lower()
    
    # Check for dangerous extensions anywhere in the filename
    for ext in dangerous_extensions:
        if ext in filename_lower:
            return (False, f"Executable extensions are not allowed: {ext}")
    
    # Get the final extension
    _, ext = os.path.splitext(filename_lower)
    
    if not ext:
        return (False, "File must have an extension")
    
    if ext not in allowed_extensions:
        return (False, f"File extension '{ext}' is not allowed")
    
    return (True, None)
