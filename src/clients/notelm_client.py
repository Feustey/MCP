from typing import Dict, List, Optional
import httpx

class NotelmClient:
    def __init__(self, api_key: str, base_url: str = "https://api.notelm.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )

    async def get_notes(self, limit: int = 10, offset: int = 0) -> List[Dict]:
        response = await self.client.get(
            f"{self.base_url}/notes",
            params={"limit": limit, "offset": offset}
        )
        response.raise_for_status()
        return response.json()

    async def get_note(self, note_id: str) -> Dict:
        response = await self.client.get(f"{self.base_url}/notes/{note_id}")
        response.raise_for_status()
        return response.json()

    async def create_note(self, content: str, title: Optional[str] = None) -> Dict:
        data = {"content": content}
        if title:
            data["title"] = title
        response = await self.client.post(f"{self.base_url}/notes", json=data)
        response.raise_for_status()
        return response.json()

    async def update_note(self, note_id: str, content: Optional[str] = None, title: Optional[str] = None) -> Dict:
        data = {}
        if content is not None:
            data["content"] = content
        if title is not None:
            data["title"] = title
        response = await self.client.patch(f"{self.base_url}/notes/{note_id}", json=data)
        response.raise_for_status()
        return response.json()

    async def delete_note(self, note_id: str) -> None:
        response = await self.client.delete(f"{self.base_url}/notes/{note_id}")
        response.raise_for_status()

    async def close(self):
        await self.client.aclose() 