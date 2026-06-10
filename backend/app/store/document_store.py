from typing import Dict, Any, List

class DocumentStore:
    def __init__(self):
        self.documents: Dict[str, Any] = {}

    def get_document(self, filename: str) -> Any:
        return self.documents.get(filename)

    def save_document(self, filename: str, doc_data: Any) -> None:
        self.documents[filename] = doc_data

    def get_all_files(self) -> List[Dict[str, Any]]:
        return [
            {"filename": fname, "stats": doc["stats"], "chunk_count": len(doc["chunks"])}
            for fname, doc in self.documents.items()
        ]

    def document_exists(self, filename: str) -> bool:
        return filename in self.documents

document_store = DocumentStore()
