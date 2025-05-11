import httpx
from typing import List, Dict, Any, Optional, Tuple, Set

class LNBitsClientError(Exception):
    """Custom exception for LNBits client errors."""
    pass

class LNBitsClient:
    """
    Client for interacting with the LNBits API to fetch Lightning Network data.

    Requires the LNBits API endpoint and an appropriate API key/token (e.g., Admin token).
    Uses 'Authorization: Bearer <token>' header based on provided documentation examples.
    """
    def __init__(self, endpoint: str, api_key: str): # api_key is the Admin Token here
        """
        Initializes the LNBitsClient.

        Args:
            endpoint: The base URL of the LNBits instance (e.g., "http://localhost:5000").
            api_key: The Admin Token (or relevant API key) for authentication.
        """
        if not endpoint or not api_key:
            raise ValueError("LNBits endpoint and api_key (Admin Token) are required.")

        self.endpoint = endpoint.rstrip('/')
        # Use Authorization: Bearer token based on provided examples
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-type": "application/json",
        }
        self.client = httpx.AsyncClient(base_url=self.endpoint, headers=self.headers, timeout=30.0)

    async def close(self):
         """Close the underlying HTTP client."""
         # Check if client exists and has the method before calling
         if hasattr(self, 'client') and hasattr(self.client, 'aclose'):
              await self.client.aclose()

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        """ Helper method for making API requests. """
        url = path
        try:
            # DEBUG: Print request details
            # print(f"DEBUG: LNBits Request: {method} {url} Headers: {self.headers} Data: {kwargs.get('json')}")
            response = await self.client.request(method, url, **kwargs)
            # DEBUG: Print response status and text
            # print(f"DEBUG: LNBits Response Status: {response.status_code}")
            # print(f"DEBUG: LNBits Response Body: {response.text}")
            response.raise_for_status()
            # Handle cases where response might be empty (e.g., DELETE success)
            if response.status_code == 204: # No Content
                 return None
            # Handle cases where response might be plain text (rare for LNBits?)
            content_type = response.headers.get("content-type", "").lower()
            if "application/json" in content_type:
                 return response.json()
            else:
                 return response.text # Or handle as needed
        except httpx.TimeoutException as e:
            print(f"Error: Timeout connecting to LNBits at {self.endpoint}{path}")
            raise LNBitsClientError(f"Timeout: {e}") from e
        except httpx.RequestError as e:
            print(f"Error: Could not connect to LNBits at {self.endpoint}{path}: {e}")
            raise LNBitsClientError(f"Connection Error: {e}") from e
        except httpx.HTTPStatusError as e:
            print(f"Error: LNBits API request failed ({e.response.status_code}): {e.response.text}")
            detail = f"LNBits API Error ({e.response.status_code})"
            try:
                 # Try to parse JSON error detail
                 error_data = e.response.json()
                 error_detail = error_data.get("detail")
                 if error_detail: detail += f": {error_detail}"
            except Exception: # If response is not JSON or key missing
                 detail += f": {e.response.text[:100]}..." # Show snippet of text
            raise LNBitsClientError(detail) from e
        except Exception as e:
            print(f"Error during LNBits API request or processing: {e}")
            raise LNBitsClientError(f"Unexpected Error: {e}") from e

    # --- Methods to be implemented based on actual LNBits API/extensions ---

    async def get_graph_data(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Fetches the Lightning Network graph data (nodes and edges/channels).

        *** Currently NOT IMPLEMENTED as no corresponding endpoint was found in the provided documentation. ***
        This data is CRITICAL for centrality calculation and suggesting external nodes.
        The expected return format mimics LND's DescribeGraph.

        Returns:
            A tuple containing:
            - nodes: List of node dictionaries (keys: 'pub_key', 'alias', 'addresses', 'features').
            - edges: List of edge dictionaries (keys: 'channel_id', 'chan_point', 'capacity',
                     'node1_pub', 'node2_pub', 'node1_policy', 'node2_policy').
        """
        print("--- LNBitsClient: Fetching graph data ---")
        # Example: If there was an endpoint in an extension
        # try:
        #     # This is a hypothetical endpoint structure
        #     # response = await self._request("GET", "/lngraph/api/v1/graph") # Or similar
        #     # nodes = response.get("nodes", [])
        #     # edges = response.get("edges", [])
        #     # return nodes, edges
        # except LNBitsClientError as e:
        #      print(f"Could not fetch graph data from LNBits: {e}")
        #      return [], [] # Return empty on error
        # except KeyError as e:
        #      print(f"Unexpected response structure from LNBits graph endpoint: Missing key {e}")
        #      return [], []

        # Placeholder Implementation
        raise NotImplementedError("LNBits API endpoint/method for fetching full graph data is not defined in the provided documentation.")
        # Return empty lists or mock data for testing if needed
        # return [], []

    async def get_local_node_info(self) -> Dict[str, Any]:
        """
        Fetches available information about the local node managed by LNBits.
        Currently retrieves active channel peers using the documented endpoint.
        *** Cannot retrieve local node pubkey from documented endpoints. ***

        Returns:
            A dictionary containing local node info. Keys:
            - 'pubkey': str (Returns None currently)
            - 'current_peers': set[str]
        """
        print("--- LNBitsClient: Fetching local node info (active channels) ---")
        local_pubkey = None # Not available from documented endpoints
        current_peers = set()
        try:
            # Use the documented endpoint to list active channels
            active_channels = await self._request("GET", "/api/v1/channels")
            if isinstance(active_channels, list):
                for chan in active_channels:
                    # Extract peer pubkey - adjust key based on actual API response
                    peer_key = None
                    if isinstance(chan, dict):
                         # Try common keys used in LND/CLN responses
                         peer_key = chan.get('remote_pubkey') or chan.get('peer_id') or chan.get('pub_key')
                    if peer_key:
                         current_peers.add(peer_key)
            else:
                 print(f"Warning: Unexpected response format from /api/v1/channels. Expected a list, got {type(active_channels)}")

        except LNBitsClientError as e:
            print(f"Could not fetch active channels from LNBits: {e}")
            # Decide if this is fatal or if we can proceed without peer info
            # For now, let's proceed but the filtering will be less effective
        except NotImplementedError: # Should not happen for this method now
             pass
        except Exception as e: # Catch other unexpected errors
             print(f"Unexpected error parsing active channels: {e}")

        # *** Need an endpoint to get the local pubkey ***
        # For now, return None for pubkey
        print(f"Local info retrieved: Pubkey={local_pubkey}, Peers={len(current_peers)}")
        return {'pubkey': local_pubkey, 'current_peers': current_peers}

    async def get_closed_channels(self) -> List[Dict[str, Any]]:
        """
        Fetches information about recently closed channels.

        *** Currently NOT IMPLEMENTED as no corresponding endpoint was found in the provided documentation. ***
        This data is needed for the 'recent closure' filter.
        Expected return is a list of dicts with keys: 'remote_pubkey', 'close_height'.

        Returns:
            A list of dictionaries, each representing a closed channel.
        """
        print("--- LNBitsClient: Fetching closed channels ---")
        # Hypothetical call:
        # response = await self._request("GET", "/lightning/api/v1/channels/closed") # Check LNBits API docs
        # return response or []

        raise NotImplementedError("LNBits API endpoint/method for fetching closed channels is not defined in the provided documentation.")
        # return [] # Return empty list

    async def get_current_block_height(self) -> int:
        """
        Fetches the current blockchain height.

        *** Currently NOT IMPLEMENTED as no corresponding endpoint was found in the provided documentation. ***
        Needed for evaluating the age of recent closures.

        Returns:
            The current block height as an integer.
        """
        print("--- LNBitsClient: Fetching current block height ---")
        # Hypothetical call:
        # try:
        #     response = await self._request("GET", "/api/v1/wallet") # Or /lightning/api/v1/getinfo ?
        #     height = response.get('block_height') # Or a similar key
        #     if height is None:
        #         raise LNBitsClientError("Could not determine block height from LNBits API.")
        #     return int(height)
        # except LNBitsClientError as e:
        #      print(f"Failed to get block height from LNBits: {e}")
        #      raise # Re-raise the client error
        # except Exception as e:
        #      print(f"Unexpected error processing block height info: {e}")
        #      raise LNBitsClientError("Failed to process block height info") from e

        raise NotImplementedError("LNBits API endpoint/method for fetching block height is not defined in the provided documentation.")
        # return 0 # Return dummy value

# Example Usage (demonstrates instantiation)
if __name__ == "__main__":
    import asyncio
    # Assuming config_loader is in the same directory or PYTHONPATH
    try:
         from mcp.config_loader import load_config
    except ImportError:
         print("Run this example from the parent directory (e.g., python -m mcp.lnbits_client)")
         # Define dummy values if config loader not found
         DUMMY_ENDPOINT = "http://127.0.0.1:5000"
         DUMMY_KEY = "YOUR_LNBITS_API_KEY"
         # Function stub if not loaded
         def load_config(): return {}
    else:
         # Load config to get endpoint/key
         config = load_config()
         DUMMY_ENDPOINT = config.get('parameters', {}).get('lnbits_api_endpoint')
         DUMMY_KEY = config.get('parameters', {}).get('lnbits_api_key')

    async def main():
        if not DUMMY_ENDPOINT or not DUMMY_KEY or DUMMY_KEY == "YOUR_LNBITS_API_KEY":
            print("Please set LNBits endpoint and api_key via MCP_LNBITS_... env vars or in mcp_config.yaml for example usage.")
            return

        client = LNBitsClient(endpoint=DUMMY_ENDPOINT, api_key=DUMMY_KEY)
        try:
            print(f"Attempting to interact with LNBits at {client.endpoint}")

            # --- Test methods (will raise NotImplementedError for most) ---
            try:
                info = await client.get_local_node_info()
                print(f"Local Info Peers: {info['current_peers']}")
            except NotImplementedError as e:
                 print(f"get_local_node_info: {e}")
            except LNBitsClientError as e:
                 print(f"Error getting local info: {e}")

            try:
                height = await client.get_current_block_height()
                print(f"Block Height: {height}")
            except NotImplementedError as e:
                print(f"get_current_block_height: {e}")
            except LNBitsClientError as e:
                 print(f"Error getting block height: {e}")

            try:
                nodes, edges = await client.get_graph_data()
                print(f"Graph Data: Fetched {len(nodes)} nodes, {len(edges)} edges")
            except NotImplementedError as e:
                print(f"get_graph_data: {e}")
            except LNBitsClientError as e:
                print(f"Error getting graph data: {e}")

            try:
                closed = await client.get_closed_channels()
                print(f"Closed Channels: Fetched {len(closed)}")
            except NotImplementedError as e:
                print(f"get_closed_channels: {e}")
            except LNBitsClientError as e:
                 print(f"Error getting closed channels: {e}")

        finally:
             await client.close() # Important to close the client

    # Run the async main function
    try:
         asyncio.run(main())
    except KeyboardInterrupt:
         print("\nExiting example.") 