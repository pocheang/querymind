"""Image processing service for multi-modal RAG."""

import logging

from app.services.multimodal.models import ImageContent

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Index an image that ingestion has already read and described.

    It used to also extract images from a PDF, call GPT-4V and Claude directly,
    and run two OCR engines -- fourteen methods, none of which anything
    constructed a caller for. `ingest_paths` builds this and calls `index_image`,
    and the reading and describing happen in `app/ingestion/extraction/`, which
    is where the masking boundary is."""

    def index_entry(self, image: ImageContent) -> tuple[str, dict]:
        """The text this image is embedded as, and the metadata stored beside it.

        Separate from `index_image` so ingestion can embed the text before taking
        the index lock and hand the vector back to `index_image` under it.
        """

        text_to_index = image.description
        if image.ocr_text:
            text_to_index += f"\n\nExtracted text: {image.ocr_text}"
        return text_to_index, {
            "doc_id": image.doc_id,
            "document_id": image.document_id,
            "tenant_id": image.tenant_id,
            "owner_user_id": image.owner_user_id,
            "visibility": image.visibility,
            "version": image.version,
            "page_number": image.page_number,
            "image_id": image.image_id,
            "artifact_uri": image.artifact_uri or "",
            "source": image.metadata.get("source", image.artifact_uri or image.doc_id),
            "type": "image",
            "image_type": image.image_type,
            "has_ocr": bool(image.ocr_text),
            "width": image.metadata.get("width", 0),
            "height": image.metadata.get("height", 0),
        }

    def index_image(
        self,
        image: ImageContent,
        collection_name: str = "image_descriptions",
        *,
        embedding: list[float] | None = None,
    ) -> None:
        """Index image content in the vector database; embeds it here unless `embedding` is given.

        Synchronous: it awaits nothing, and its caller is document ingestion,
        which runs in a worker thread where an event loop must not be driven.
        """
        try:
            from app.retrievers.stores.vector import upsert_texts

            text_to_index, metadata = self.index_entry(image)
            upsert_texts(
                collection_name,
                [image.image_id],
                [text_to_index],
                [metadata],
                None if embedding is None else [embedding],
            )
            logger.info(f"Indexed image {image.image_id} in collection {collection_name}")
        except Exception:
            logger.exception(f"Error indexing image {image.image_id}")
            raise
