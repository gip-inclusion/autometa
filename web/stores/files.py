"""Uploaded file persistence."""

from typing import Optional

from sqlalchemy import select

from web.db import get_db
from web.models import UploadedFile as FileModel
from web.stores.records import UploadedFile, model_to_uploaded_file


class FilesMixin:
    def add_uploaded_file(
        self,
        conversation_id: Optional[str],
        user_id: Optional[str],
        original_filename: str,
        stored_filename: str,
        storage_path: str,
        file_size: int,
        sha256_hash: str,
        mime_type: Optional[str] = None,
        is_text: bool = False,
        av_scanned: bool = False,
        av_clean: Optional[bool] = None,
    ) -> Optional[UploadedFile]:
        """Add a new uploaded file record."""
        uploaded_file = UploadedFile(
            conversation_id=conversation_id,
            user_id=user_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            storage_path=storage_path,
            file_size=file_size,
            mime_type=mime_type,
            sha256_hash=sha256_hash,
            is_text=is_text,
            av_scanned=av_scanned,
            av_clean=av_clean,
        )

        with get_db() as session:
            model = FileModel(
                conversation_id=conversation_id,
                user_id=user_id,
                original_filename=original_filename,
                stored_filename=stored_filename,
                storage_path=storage_path,
                file_size=file_size,
                mime_type=mime_type,
                sha256_hash=sha256_hash,
                is_text=is_text,
                av_scanned=av_scanned,
                av_clean=av_clean,
                created_at=uploaded_file.created_at,
            )
            session.add(model)
            session.flush()
            uploaded_file.id = model.id

        return uploaded_file

    def get_uploaded_file(self, file_id: int) -> Optional[UploadedFile]:
        with get_db() as session:
            f = session.get(FileModel, file_id)
            if not f:
                return None
            return model_to_uploaded_file(f)

    def get_uploaded_file_by_hash(self, sha256_hash: str) -> Optional[UploadedFile]:
        with get_db() as session:
            f = session.scalars(select(FileModel).where(FileModel.sha256_hash == sha256_hash).limit(1)).first()
            if not f:
                return None
            return model_to_uploaded_file(f)

    def get_conversation_files(self, conversation_id: str) -> list[UploadedFile]:
        with get_db() as session:
            models = session.scalars(
                select(FileModel).where(FileModel.conversation_id == conversation_id).order_by(FileModel.created_at)
            ).all()
            return [model_to_uploaded_file(f) for f in models]

    def update_uploaded_file_av_status(self, file_id: int, av_scanned: bool, av_clean: Optional[bool]) -> bool:
        with get_db() as session:
            f = session.get(FileModel, file_id)
            if not f:
                return False
            f.av_scanned = av_scanned
            f.av_clean = av_clean
            return True

    def delete_uploaded_file(self, file_id: int) -> bool:
        with get_db() as session:
            f = session.get(FileModel, file_id)
            if not f:
                return False
            session.delete(f)
            return True
