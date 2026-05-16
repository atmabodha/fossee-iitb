"""
Utilities for stateless API operation.

Provides encoding/decoding functionality for passing StudentState via HTTP headers
and request bodies for the stateless API endpoints.
"""

import base64
import json
from api_architecture.models.student_state import StudentState


class StateEncodingError(Exception):
    """Raised when StudentState encoding/decoding fails."""
    pass


def decode_student_state_from_header(encoded_state: str) -> StudentState:
    """
    Decode a StudentState from a base64-encoded JSON string (typically from HTTP header).
    
    Args:
        encoded_state: A base64-encoded JSON representation of StudentState
        
    Returns:
        Parsed StudentState object
        
    Raises:
        StateEncodingError: If decoding or parsing fails
        
    Example:
        # Header value: "eyJzdHVkZW50X2lkIjogIjEyMzQ1Njc4LTEyMzQtNTY3OC0xMjM0LTU2Nzg5MGFiY2QiLCAiY3VycmVudF9jb25jZXB0IjogIkMxIn0="
        state = decode_student_state_from_header(encoded_state)
    """
    try:
        # Decode from base64
        json_bytes = base64.b64decode(encoded_state, validate=True)
        json_str = json_bytes.decode('utf-8')
        
        # Parse JSON
        state_dict = json.loads(json_str)
        
        # Convert to StudentState (Pydantic will validate)
        return StudentState(**state_dict)
    
    except base64.binascii.Error as e:
        raise StateEncodingError(f"Invalid base64 encoding: {e}")
    except UnicodeDecodeError as e:
        raise StateEncodingError(f"Decoded bytes are not valid UTF-8: {e}")
    except json.JSONDecodeError as e:
        raise StateEncodingError(f"Invalid JSON in decoded state: {e}")
    except Exception as e:
        # Catches validation errors from Pydantic and other unexpected errors
        raise StateEncodingError(f"Failed to parse StudentState: {e}")


def encode_student_state_for_header(state: StudentState) -> str:
    """
    Encode a StudentState as a base64-encoded JSON string (for HTTP headers).
    
    Args:
        state: The StudentState object to encode
        
    Returns:
        Base64-encoded JSON string suitable for X-Student-State header
        
    Raises:
        StateEncodingError: If encoding fails
        
    Example:
        encoded = encode_student_state_for_header(state)
        # Returns: "eyJzdHVkZW50X2lkIjogIjEyMzQ1Njc4LTEyMzQtNTY3OC0xMjM0LTU2Nzg5MGFiY2QiLCAiY3VycmVudF9jb25jZXB0IjogIkMxIn0="
    """
    try:
        # Convert StudentState to dict (JSON-serializable)
        state_dict = state.model_dump(mode='json')
        
        # Serialize to JSON
        json_str = json.dumps(state_dict)
        json_bytes = json_str.encode('utf-8')
        
        # Encode to base64
        encoded = base64.b64encode(json_bytes).decode('ascii')
        return encoded
    
    except Exception as e:
        raise StateEncodingError(f"Failed to encode StudentState: {e}")
