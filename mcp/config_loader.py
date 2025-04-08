import yaml
import os
from typing import Dict, Any, Union

# Define default configuration structure and values
DEFAULT_CONFIG = {
    "weights": {
        "open": { # Based on hydrus.DefaultOpenWeights
            "capacity": 1.0,
            "features": 1.0, # Note: Hydrus uses 1.0 here
            "hybrid": 0.8,
            "centrality": {
                "degree": 0.4,
                "betweenness": 0.8,
                "eigenvector": 0.5,
                "closeness": 0.8,
            },
            "channels": { # Based on hydrus.DefaultOpenWeights.Channels
                "base_fee": 1.0, # Note: Hydrus uses 1.0 here
                "fee_rate": 0.7,
                "inbound_base_fee": 0.8, # Keeping placeholder, value from Hydrus
                "inbound_fee_rate": 0.7, # Keeping placeholder, value from Hydrus
                "min_htlc": 1.0, # Note: Hydrus uses 1.0 here
                "max_htlc": 0.6,
                "age": 0.8, # Hydrus uses BlockHeight, mapping to age, value from Hydrus
            }
        },
        "close": { # Based on hydrus.DefaultCloseWeights
            "capacity": 0.5,
            "age": 0.6, # Hydrus BlockHeight
            "num_forwards": 0.8,
            "forwards_amount": 1.0,
            "fees": 1.0,
            "ping_time": 0.4, # Requires implementation
            "flap_count": 0.2, # Requires implementation
            "active": 1.0, # Requires implementation
            # local_balance_ratio: Not directly in Hydrus defaults, but useful
        }
    },
    "lists": {
        "blocklist": [], # Start with empty default blocklist
        "keeplist": [] # For close logic
    },
    "parameters": {
        "min_channel_size_sats": 1000000, # Hydrus default
        "max_channel_size_sats": 10000000,# Hydrus default
        "max_suggestions": 10,
        "allocation_percent": 60,      # Hydrus default
        "min_channels": 2,             # Hydrus default
        "max_channels": 200,           # Hydrus default
        "min_batch_size": 1,           # Hydrus doesn't specify default, assuming 1
        "target_conf": 6,              # Hydrus default
        "allow_force_closes": False,   # Hydrus doesn't specify default, assuming False
        "lnbits_api_endpoint": None,
        "lnbits_api_key": None
    },
    "preprocessing": {
        "max_channel_fee_rate_ppm": 20000, # Value from Hydrus code
        "max_channel_base_fee_msat": 100000 # Value from Hydrus code
    },
    "selection": {
         "recent_closure_threshold_blocks": 144 * 30 * 3 # Approx 3 months (Hydrus value)
    },
    "routing_policies": { # From Hydrus config structure
         "activity_period_hours": 24 # Hydrus uses time.Duration, simplifying to hours
    }
}

def merge_configs(default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merges the user config into the default config.
    Overwrites default values with user values, adds keys from user if not in default.
    """
    merged = default.copy()
    for key, value in user.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_configs(merged[key], value)
        else:
            # If user value is provided, it overrides default, regardless of type
            merged[key] = value
    return merged

def _validate_weights(weights_dict: Dict[str, Any], path: str) -> None:
    """ Recursively validates that all weights are floats between 0 and 1. """
    for key, value in weights_dict.items():
        current_path = f"{path}.{key}"
        if isinstance(value, dict):
            _validate_weights(value, current_path)
        elif isinstance(value, (int, float)):
            if not (0.0 <= float(value) <= 1.0):
                 raise ValueError(f"Configuration Error: Weight at '{current_path}' must be between 0.0 and 1.0 (found: {value})")
        else:
             # Ignore non-numeric values in weight structures if any
             pass

def _validate_config(config: Dict[str, Any]) -> None:
    """ Performs validation checks on the loaded configuration. """
    print("Validating configuration...")
    # Validate weights range (0-1)
    if 'weights' in config:
         if 'open' in config['weights']:
              _validate_weights(config['weights']['open'], "weights.open")
         if 'close' in config['weights']:
              _validate_weights(config['weights']['close'], "weights.close")

    # Validate parameters
    params = config.get('parameters', {})
    if not (0 < params.get('allocation_percent', 0) <= 100):
         raise ValueError("Configuration Error: parameters.allocation_percent must be between 1 and 100.")
    if params.get('min_channel_size_sats', 0) < 20000: # LND min limit often enforced
         print("Warning: parameters.min_channel_size_sats is less than 20000 sats.")
         # raise ValueError("Configuration Error: parameters.min_channel_size_sats must be at least 20000.")
    if params.get('min_channel_size_sats', 0) > params.get('max_channel_size_sats', 0):
         raise ValueError("Configuration Error: parameters.min_channel_size_sats cannot be greater than max_channel_size_sats.")
    if params.get('min_channels', 0) > params.get('max_channels', 0):
         raise ValueError("Configuration Error: parameters.min_channels cannot be greater than max_channels.")
    if params.get('target_conf', 0) < 1:
         raise ValueError("Configuration Error: parameters.target_conf must be at least 1.")

    # Validate LNBits connection details (essential)
    if not params.get('lnbits_api_endpoint'):
         raise ValueError("Configuration Error: LNBits API endpoint is not configured (parameters.lnbits_api_endpoint).")
    if not params.get('lnbits_api_key'):
         raise ValueError("Configuration Error: LNBits API key is not configured (parameters.lnbits_api_key).")

    # Validate preprocessing thresholds
    preproc = config.get('preprocessing', {})
    if preproc.get('max_channel_fee_rate_ppm', -1) < 0:
         raise ValueError("Configuration Error: preprocessing.max_channel_fee_rate_ppm must be non-negative.")
    if preproc.get('max_channel_base_fee_msat', -1) < 0:
         raise ValueError("Configuration Error: preprocessing.max_channel_base_fee_msat must be non-negative.")

    print("Configuration validation passed.")

def load_config(config_path: str = "mcp_config.yaml") -> Dict[str, Any]:
    """
    Loads configuration from a YAML file, merging it with default values and validating it.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        A dictionary containing the final, validated configuration.
    Raises:
         ValueError: If the configuration fails validation.
         FileNotFoundError: If the config file specified cannot be found.
         yaml.YAMLError: If the config file has syntax errors.
    """
    user_config = {}
    config_file_path = os.path.abspath(config_path)

    if os.path.exists(config_file_path):
        print(f"Loading configuration from: {config_file_path}")
        try:
            with open(config_file_path, 'r') as f:
                loaded_user_config = yaml.safe_load(f)
                if loaded_user_config: # Ensure file is not empty
                     user_config = loaded_user_config
        except yaml.YAMLError as e:
            print(f"Error parsing YAML file {config_file_path}: {e}")
            raise # Re-raise the YAML error
        except Exception as e:
            print(f"Error reading config file {config_file_path}: {e}")
            raise # Re-raise other file reading errors
    else:
        # Changed: Raise error if specified file not found, instead of defaulting silently
        # If default behaviour is desired, revert to printing warning and using default.
        # print(f"Configuration file not found at: {config_file_path}")
        # print("Warning: Using default configuration values.")
        # final_config = DEFAULT_CONFIG.copy() # Use only defaults if file not found?
        raise FileNotFoundError(f"Configuration file not found at: {config_file_path}")

    # Merge user config into defaults
    final_config = merge_configs(DEFAULT_CONFIG, user_config)

    # Environment Variable Overrides (before validation)
    env_api_key = os.environ.get('MCP_LNBITS_API_KEY')
    if env_api_key:
        print("Overriding LNBits API key from environment variable MCP_LNBITS_API_KEY.")
        final_config.setdefault('parameters', {})['lnbits_api_key'] = env_api_key

    env_api_endpoint = os.environ.get('MCP_LNBITS_API_ENDPOINT')
    if env_api_endpoint:
         print("Overriding LNBits API endpoint from environment variable MCP_LNBITS_API_ENDPOINT.")
         final_config.setdefault('parameters', {})['lnbits_api_endpoint'] = env_api_endpoint

    # Validate the final merged configuration
    try:
         _validate_config(final_config)
    except ValueError as e:
         print(f"Configuration Error: {e}")
         raise # Re-raise validation errors

    return final_config

# Example usage:
if __name__ == "__main__":
    # Create a dummy config file for testing
    dummy_config = {
        "weights": {
            "open": {
                "capacity": 1.5, # Override default -> SHOULD FAIL VALIDATION
                "centrality": { "betweenness": 0.8 } # Override nested
            }
        },
        "lists": {
            "blocklist": ["NODE_X", "NODE_Y"] # Override list
        },
        "parameters": {
            "lnbits_api_endpoint": "http://user.config:5000", # Missing API key -> Should raise error
             "new_param": True # Add new parameter
        }
    }
    dummy_path = "dummy_mcp_config_invalid.yaml"
    try:
        with open(dummy_path, 'w') as f:
            yaml.dump(dummy_config, f, default_flow_style=False)
        print(f"Created dummy INVALID config file: {dummy_path}")

        # Test loading (should fail validation)
        try:
             loaded = load_config(dummy_path)
             print("\n--- Loaded Config (merged with defaults - UNEXPECTED SUCCESS) ---")
             print(yaml.dump(loaded, indent=2, default_flow_style=False))
        except (ValueError, FileNotFoundError, yaml.YAMLError) as e:
             print(f"\n--- Loading failed as expected ---")
             print(f"Error: {e}")

    finally:
        # Clean up dummy file
        if os.path.exists(dummy_path):
            os.remove(dummy_path)
            print(f"\nRemoved dummy config file: {dummy_path}") 