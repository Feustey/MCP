from typing import List, Optional
from src.clients.notelm_client import NotelmClient
from src.models.note import Note, NoteCreate, NoteUpdate

class NoteService:
    def __init__(self, client: NotelmClient):
        self.client = client

    async def get_notes(self, limit: int = 10, offset: int = 0) -> List[Note]:
        notes = await self.client.get_notes(limit=limit, offset=offset)
        return [Note(**note) for note in notes]

    async def get_note(self, note_id: str) -> Note:
        note = await self.client.get_note(note_id)
        return Note(**note)

    async def create_note(self, note: NoteCreate) -> Note:
        created_note = await self.client.create_note(
            content=note.content,
            title=note.title
        )
        return Note(**created_note)

    async def update_note(self, note_id: str, note: NoteUpdate) -> Note:
        updated_note = await self.client.update_note(
            note_id=note_id,
            content=note.content,
            title=note.title
        )
        return Note(**updated_note)

    async def delete_note(self, note_id: str) -> None:
        await self.client.delete_note(note_id) 