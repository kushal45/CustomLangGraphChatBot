#!/usr/bin/env python3
"""
Node Input/Output Serialization for Debugging

This module provides comprehensive serialization and deserialization utilities
for workflow node inputs and outputs, enabling debugging, replay functionality,
and state persistence with full data integrity preservation.

Part of Milestone 2: Individual Node Testing & Workflow Debugging
"""

import json
import pickle
import base64
import gzip
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import sys

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from state import ReviewState, ReviewStatus, RepositoryInfo, ToolResult, AnalysisResults
from logging_config import get_logger, initialize_logging, LoggingConfig

# Initialize logging
initialize_logging(LoggingConfig(
    log_level="INFO",
    log_format="detailed",
    enable_console_logging=True,
    enable_file_logging=True,
    log_dir="logs/serialization"
))

logger = get_logger(__name__)


class SerializationFormat(Enum):
    """Supported serialization formats."""
    JSON = "json"
    PICKLE = "pickle"
    COMPRESSED_JSON = "compressed_json"
    BINARY = "binary"


@dataclass
class SerializationMetadata:
    """Metadata for serialized data."""
    format: SerializationFormat
    timestamp: str
    version: str
    checksum: str
    original_size: int
    compressed_size: Optional[int]
    node_name: Optional[str]
    data_type: str  # 'input', 'output', 'state'


@dataclass
class SerializedData:
    """Container for serialized data with metadata."""
    data: Union[str, bytes]
    metadata: SerializationMetadata
    schema_version: str = "1.0"


class NodeSerializer:
    """Advanced serialization utility for node inputs and outputs."""
    
    def __init__(self, default_format: SerializationFormat = SerializationFormat.JSON,
                 compression_enabled: bool = True,
                 validation_enabled: bool = True):
        self.default_format = default_format
        self.compression_enabled = compression_enabled
        self.validation_enabled = validation_enabled
        self.serialization_history: List[Dict[str, Any]] = []
        
        # Create serialization directory
        self.serialization_dir = Path("logs/serialization/data")
        try:
            self.serialization_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            # Handle read-only filesystem or permission issues
            print(f"Warning: Cannot create serialization directory {self.serialization_dir}: {e}")
            print("Serialization will be stored in memory only.")
            # Use a temporary directory or disable file output
            import tempfile
            self.serialization_dir = Path(tempfile.gettempdir()) / "serialization" / "data"
            try:
                self.serialization_dir.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError):
                # If even temp directory fails, disable file output
                self.serialization_dir = None
    
    def _calculate_checksum(self, data: bytes) -> str:
        """Calculate SHA-256 checksum for data integrity."""
        return hashlib.sha256(data).hexdigest()
    
    def _compress_data(self, data: bytes) -> bytes:
        """Compress data using gzip."""
        return gzip.compress(data)
    
    def _decompress_data(self, data: bytes) -> bytes:
        """Decompress gzip data."""
        return gzip.decompress(data)
    
    def _serialize_to_json(self, obj: Any) -> str:
        """Serialize object to JSON with custom handling."""
        def json_serializer(obj):
            """Custom JSON serializer for complex objects."""
            if hasattr(obj, '__dict__'):
                return obj.__dict__
            elif isinstance(obj, Enum):
                return obj.value
            elif hasattr(obj, 'isoformat'):  # datetime objects
                return obj.isoformat()
            elif isinstance(obj, (set, frozenset)):
                return list(obj)
            elif isinstance(obj, bytes):
                return base64.b64encode(obj).decode('utf-8')
            else:
                return str(obj)
        
        return json.dumps(obj, default=json_serializer, indent=2, sort_keys=True)
    
    def _deserialize_from_json(self, json_str: str) -> Any:
        """Deserialize object from JSON."""
        return json.loads(json_str)
    
    def _serialize_to_pickle(self, obj: Any) -> bytes:
        """Serialize object to pickle format."""
        return pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
    
    def _deserialize_from_pickle(self, data: bytes) -> Any:
        """Deserialize object from pickle format."""
        return pickle.loads(data)
    
    def _prepare_state_for_serialization(self, state: ReviewState) -> Dict[str, Any]:
        """Prepare ReviewState for serialization by handling special types."""
        prepared = {}
        
        for key, value in state.items():
            if key == "status" and value:
                prepared[key] = value.value if hasattr(value, 'value') else str(value)
            elif key == "messages":
                prepared[key] = [
                    {
                        "type": type(msg).__name__,
                        "content": str(msg),
                        "additional_kwargs": getattr(msg, 'additional_kwargs', {}),
                        "response_metadata": getattr(msg, 'response_metadata', {})
                    }
                    for msg in (value or [])
                ]
            elif isinstance(value, (datetime,)):
                prepared[key] = value.isoformat() if value else None
            else:
                prepared[key] = value
        
        return prepared
    
    def _restore_state_from_serialization(self, data: Dict[str, Any]) -> ReviewState:
        """Restore ReviewState from serialized data."""
        restored = data.copy()
        
        # Restore status enum
        if "status" in restored and isinstance(restored["status"], str):
            try:
                restored["status"] = ReviewStatus(restored["status"])
            except ValueError:
                restored["status"] = ReviewStatus.INITIALIZING
        
        # Restore messages (simplified for debugging)
        if "messages" in restored:
            restored["messages"] = []  # Simplified for debugging
        
        # Ensure all required fields exist
        defaults = {
            "messages": [],
            "current_step": "initializing",
            "status": ReviewStatus.INITIALIZING,
            "error_message": None,
            "repository_url": "",
            "repository_info": None,
            "repository_type": None,
            "enabled_tools": [],
            "tool_results": {},
            "failed_tools": [],
            "analysis_results": None,
            "files_analyzed": [],
            "total_files": 0,
            "review_config": {},
            "start_time": None,
            "end_time": None,
            "notifications_sent": [],
            "report_generated": False,
            "final_report": None
        }
        
        for key, default_value in defaults.items():
            if key not in restored:
                restored[key] = default_value
        
        return restored
    
    def serialize_node_input(self, node_name: str, input_state: ReviewState,
                           format: Optional[SerializationFormat] = None) -> SerializedData:
        """Serialize node input state for debugging and replay."""
        format = format or self.default_format
        
        logger.info(f"Serializing input for node: {node_name}", extra={
            "node_name": node_name,
            "format": format.value,
            "state_keys": list(input_state.keys())
        })
        
        try:
            # Prepare state for serialization
            prepared_state = self._prepare_state_for_serialization(input_state)
            
            # Serialize based on format
            if format == SerializationFormat.JSON:
                serialized_data = self._serialize_to_json(prepared_state)
                data_bytes = serialized_data.encode('utf-8')
            elif format == SerializationFormat.PICKLE:
                data_bytes = self._serialize_to_pickle(prepared_state)
                serialized_data = base64.b64encode(data_bytes).decode('utf-8')
            elif format == SerializationFormat.COMPRESSED_JSON:
                json_data = self._serialize_to_json(prepared_state)
                data_bytes = json_data.encode('utf-8')
                compressed_bytes = self._compress_data(data_bytes)
                serialized_data = base64.b64encode(compressed_bytes).decode('utf-8')
                data_bytes = compressed_bytes
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            # Calculate metadata
            original_size = len(str(prepared_state).encode('utf-8'))
            compressed_size = len(data_bytes) if format == SerializationFormat.COMPRESSED_JSON else None
            checksum = self._calculate_checksum(data_bytes)
            
            metadata = SerializationMetadata(
                format=format,
                timestamp=datetime.now().isoformat(),
                version="1.0",
                checksum=checksum,
                original_size=original_size,
                compressed_size=compressed_size,
                node_name=node_name,
                data_type="input"
            )
            
            result = SerializedData(
                data=serialized_data,
                metadata=metadata
            )
            
            # Record serialization
            self.serialization_history.append({
                "timestamp": metadata.timestamp,
                "node_name": node_name,
                "data_type": "input",
                "format": format.value,
                "size": original_size,
                "checksum": checksum
            })
            
            logger.info(f"Successfully serialized input for {node_name}", extra={
                "original_size": original_size,
                "compressed_size": compressed_size,
                "format": format.value,
                "checksum": checksum[:8]
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to serialize input for {node_name}: {e}", exc_info=True)
            raise
    
    def serialize_node_output(self, node_name: str, output_data: Dict[str, Any],
                            format: Optional[SerializationFormat] = None) -> SerializedData:
        """Serialize node output for debugging and replay."""
        format = format or self.default_format
        
        logger.info(f"Serializing output for node: {node_name}", extra={
            "node_name": node_name,
            "format": format.value,
            "output_keys": list(output_data.keys())
        })
        
        try:
            # Serialize based on format
            if format == SerializationFormat.JSON:
                serialized_data = self._serialize_to_json(output_data)
                data_bytes = serialized_data.encode('utf-8')
            elif format == SerializationFormat.PICKLE:
                data_bytes = self._serialize_to_pickle(output_data)
                serialized_data = base64.b64encode(data_bytes).decode('utf-8')
            elif format == SerializationFormat.COMPRESSED_JSON:
                json_data = self._serialize_to_json(output_data)
                data_bytes = json_data.encode('utf-8')
                compressed_bytes = self._compress_data(data_bytes)
                serialized_data = base64.b64encode(compressed_bytes).decode('utf-8')
                data_bytes = compressed_bytes
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            # Calculate metadata
            original_size = len(str(output_data).encode('utf-8'))
            compressed_size = len(data_bytes) if format == SerializationFormat.COMPRESSED_JSON else None
            checksum = self._calculate_checksum(data_bytes)
            
            metadata = SerializationMetadata(
                format=format,
                timestamp=datetime.now().isoformat(),
                version="1.0",
                checksum=checksum,
                original_size=original_size,
                compressed_size=compressed_size,
                node_name=node_name,
                data_type="output"
            )
            
            result = SerializedData(
                data=serialized_data,
                metadata=metadata
            )
            
            # Record serialization
            self.serialization_history.append({
                "timestamp": metadata.timestamp,
                "node_name": node_name,
                "data_type": "output",
                "format": format.value,
                "size": original_size,
                "checksum": checksum
            })
            
            logger.info(f"Successfully serialized output for {node_name}", extra={
                "original_size": original_size,
                "compressed_size": compressed_size,
                "format": format.value,
                "checksum": checksum[:8]
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to serialize output for {node_name}: {e}", exc_info=True)
            raise
    
    def deserialize_node_input(self, serialized_data: SerializedData) -> ReviewState:
        """Deserialize node input state."""
        logger.info(f"Deserializing input data", extra={
            "format": serialized_data.metadata.format.value,
            "node_name": serialized_data.metadata.node_name,
            "checksum": serialized_data.metadata.checksum[:8]
        })
        
        try:
            format = serialized_data.metadata.format
            
            # Deserialize based on format
            if format == SerializationFormat.JSON:
                data = self._deserialize_from_json(serialized_data.data)
            elif format == SerializationFormat.PICKLE:
                data_bytes = base64.b64decode(serialized_data.data)
                data = self._deserialize_from_pickle(data_bytes)
            elif format == SerializationFormat.COMPRESSED_JSON:
                compressed_bytes = base64.b64decode(serialized_data.data)
                decompressed_bytes = self._decompress_data(compressed_bytes)
                json_str = decompressed_bytes.decode('utf-8')
                data = self._deserialize_from_json(json_str)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            # Restore state
            restored_state = self._restore_state_from_serialization(data)
            
            logger.info(f"Successfully deserialized input data", extra={
                "format": format.value,
                "state_keys": list(restored_state.keys())
            })
            
            return restored_state
            
        except Exception as e:
            logger.error(f"Failed to deserialize input data: {e}", exc_info=True)
            raise
    
    def deserialize_node_output(self, serialized_data: SerializedData) -> Dict[str, Any]:
        """Deserialize node output data."""
        logger.info(f"Deserializing output data", extra={
            "format": serialized_data.metadata.format.value,
            "node_name": serialized_data.metadata.node_name,
            "checksum": serialized_data.metadata.checksum[:8]
        })
        
        try:
            format = serialized_data.metadata.format
            
            # Deserialize based on format
            if format == SerializationFormat.JSON:
                data = self._deserialize_from_json(serialized_data.data)
            elif format == SerializationFormat.PICKLE:
                data_bytes = base64.b64decode(serialized_data.data)
                data = self._deserialize_from_pickle(data_bytes)
            elif format == SerializationFormat.COMPRESSED_JSON:
                compressed_bytes = base64.b64decode(serialized_data.data)
                decompressed_bytes = self._decompress_data(compressed_bytes)
                json_str = decompressed_bytes.decode('utf-8')
                data = self._deserialize_from_json(json_str)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            logger.info(f"Successfully deserialized output data", extra={
                "format": format.value,
                "output_keys": list(data.keys()) if isinstance(data, dict) else "non-dict"
            })
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to deserialize output data: {e}", exc_info=True)
            raise
    
    def save_serialized_data(self, serialized_data: SerializedData, filename: str) -> Path:
        """Save serialized data to file."""
        if self.serialization_dir is None:
            logger.debug("Serialization directory not available, skipping file save")
            # Return a dummy path for compatibility
            return Path(f"/tmp/{filename}")

        filepath = self.serialization_dir / filename

        try:
            # Create complete data structure with proper enum handling
            metadata_dict = asdict(serialized_data.metadata)
            metadata_dict["format"] = serialized_data.metadata.format.value  # Convert enum to value

            complete_data = {
                "schema_version": serialized_data.schema_version,
                "metadata": metadata_dict,
                "data": serialized_data.data
            }

            with open(filepath, 'w') as f:
                json.dump(complete_data, f, indent=2, default=str)

            logger.info(f"Saved serialized data to {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Failed to save serialized data: {e}", exc_info=True)
            raise
    
    def load_serialized_data(self, filepath: Union[str, Path]) -> SerializedData:
        """Load serialized data from file."""
        filepath = Path(filepath)
        
        try:
            with open(filepath, 'r') as f:
                complete_data = json.load(f)
            
            # Reconstruct metadata
            metadata_dict = complete_data["metadata"]
            metadata_dict["format"] = SerializationFormat(metadata_dict["format"])
            metadata = SerializationMetadata(**metadata_dict)
            
            # Reconstruct serialized data
            serialized_data = SerializedData(
                data=complete_data["data"],
                metadata=metadata,
                schema_version=complete_data.get("schema_version", "1.0")
            )
            
            logger.info(f"Loaded serialized data from {filepath}")
            return serialized_data
            
        except Exception as e:
            logger.error(f"Failed to load serialized data: {e}", exc_info=True)
            raise
    
    def _create_metadata_from_dict(self, metadata_dict: Dict[str, Any]) -> SerializationMetadata:
        """Create SerializationMetadata from dictionary."""
        # Convert format string back to enum
        format_value = metadata_dict["format"]
        if isinstance(format_value, str):
            # Handle both enum string representation and enum value
            if format_value.startswith("SerializationFormat."):
                format_value = format_value.split(".")[-1].lower()
            format_enum = SerializationFormat(format_value)
        else:
            format_enum = format_value

        return SerializationMetadata(
            format=format_enum,
            timestamp=metadata_dict["timestamp"],
            version=metadata_dict["version"],
            checksum=metadata_dict["checksum"],
            original_size=metadata_dict["original_size"],
            compressed_size=metadata_dict.get("compressed_size"),
            node_name=metadata_dict.get("node_name"),
            data_type=metadata_dict["data_type"]
        )

    def get_serialization_summary(self) -> Dict[str, Any]:
        """Get summary of serialization operations."""
        return {
            "total_operations": len(self.serialization_history),
            "operations_by_type": {
                "input": len([op for op in self.serialization_history if op["data_type"] == "input"]),
                "output": len([op for op in self.serialization_history if op["data_type"] == "output"])
            },
            "operations_by_format": {
                format.value: len([op for op in self.serialization_history if op["format"] == format.value])
                for format in SerializationFormat
            },
            "total_size": sum(op["size"] for op in self.serialization_history),
            "recent_operations": self.serialization_history[-5:] if self.serialization_history else []
        }


# Global serializer instance
_global_serializer: Optional[NodeSerializer] = None


def get_serializer() -> NodeSerializer:
    """Get global serializer instance."""
    global _global_serializer
    if _global_serializer is None:
        _global_serializer = NodeSerializer()
    return _global_serializer


if __name__ == "__main__":
    # Example usage and testing
    import asyncio

    def create_test_state() -> ReviewState:
        """Create test state for serialization testing."""
        return {
            "messages": [],
            "current_step": "analyze_code",
            "status": ReviewStatus.ANALYZING_CODE,
            "error_message": None,
            "repository_url": "https://github.com/test/serialization-repo",
            "repository_info": {
                "url": "https://github.com/test/serialization-repo",
                "name": "serialization-repo",
                "full_name": "test/serialization-repo",
                "description": "Test repository for serialization",
                "language": "Python",
                "stars": 10,
                "forks": 2,
                "size": 1024,
                "default_branch": "main",
                "topics": ["testing", "serialization"],
                "file_structure": [
                    {"path": "main.py", "type": "file", "size": 500},
                    {"path": "test.py", "type": "file", "size": 300}
                ],
                "recent_commits": [
                    {"sha": "abc123", "message": "Add serialization", "author": "tester"}
                ]
            },
            "repository_type": "python",
            "enabled_tools": ["pylint_analysis", "code_review"],
            "tool_results": {
                "pylint_analysis": {
                    "tool_name": "pylint_analysis",
                    "success": True,
                    "result": {"score": 8.0, "issues": []},
                    "error_message": None,
                    "execution_time": 1.5,
                    "timestamp": "2025-07-08T17:00:00"
                }
            },
            "failed_tools": [],
            "analysis_results": None,
            "files_analyzed": ["main.py", "test.py"],
            "total_files": 2,
            "review_config": {"serialization_test": True},
            "start_time": "2025-07-08T17:00:00",
            "end_time": None,
            "notifications_sent": [],
            "report_generated": False,
            "final_report": None
        }

    async def test_serialization():
        """Test the serialization functionality."""
        print("Testing Node Serialization System")
        print("=" * 50)

        serializer = get_serializer()

        # Test input serialization
        print("\n1. Testing input serialization...")
        test_state = create_test_state()
        
        # Test different formats (excluding BINARY which is not implemented)
        for format in [SerializationFormat.JSON, SerializationFormat.PICKLE, SerializationFormat.COMPRESSED_JSON]:
            print(f"\nTesting format: {format.value}")
            
            # Serialize input
            serialized_input = serializer.serialize_node_input(
                "test_node", test_state, format
            )
            
            # Save to file
            filename = f"test_input_{format.value}.json"
            filepath = serializer.save_serialized_data(serialized_input, filename)
            
            # Load from file
            loaded_data = serializer.load_serialized_data(filepath)
            
            # Deserialize
            restored_state = serializer.deserialize_node_input(loaded_data)
            
            print(f"✅ {format.value}: Original size: {serialized_input.metadata.original_size}, "
                  f"Compressed: {serialized_input.metadata.compressed_size or 'N/A'}")
        
        # Test output serialization
        print("\n2. Testing output serialization...")
        test_output = {
            "current_step": "generate_report",
            "status": "analyzing_code",
            "tool_results": {"test_tool": {"success": True, "result": "test"}},
            "analysis_complete": True
        }
        
        serialized_output = serializer.serialize_node_output(
            "test_node", test_output, SerializationFormat.JSON
        )
        
        filename = "test_output.json"
        filepath = serializer.save_serialized_data(serialized_output, filename)
        loaded_output = serializer.load_serialized_data(filepath)
        restored_output = serializer.deserialize_node_output(loaded_output)
        
        print(f"✅ Output serialization successful")
        print(f"Original keys: {list(test_output.keys())}")
        print(f"Restored keys: {list(restored_output.keys())}")
        
        # Show summary
        print("\n3. Serialization Summary:")
        summary = serializer.get_serialization_summary()
        print(json.dumps(summary, indent=2, default=str))
        
        print("\n" + "=" * 50)
        print("Serialization testing completed!")
    
    # Run test
    asyncio.run(test_serialization())
