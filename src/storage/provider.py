"""
HC-XCDSS Persistent Storage Provider Abstraction
Supports:
- LocalStorageProvider: Stores artifacts under local outputs/ directory (Default, local development)
- CloudinaryStorageProvider: Stores artifacts persistently on Cloudinary (Production/Render)
"""

import os
import shutil
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union, Dict, Any

logger = logging.getLogger("HC-XCDSS-Storage")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIRECTORY = PROJECT_ROOT / "outputs"
ANALYSIS_DIRECTORY = OUTPUT_DIRECTORY / "analyses"
VERIFICATION_DOCUMENTS_DIR = OUTPUT_DIRECTORY / "verification_documents"


class StorageProvider(ABC):
    """
    Abstract interface for storing and deleting medical artifacts.
    """

    @abstractmethod
    def save_analysis_artifact(
        self,
        analysis_id: str,
        file_path_or_bytes: Union[str, Path, bytes],
        filename: str
    ) -> str:
        """
        Saves an analysis artifact (X-ray image, Grad-CAM heatmap, JSON) and returns
        either a relative endpoint URL (local) or absolute secure HTTPS URL (cloud).
        """
        pass

    @abstractmethod
    def save_verification_document(
        self,
        user_id: str,
        doc_type: str,
        file_bytes: bytes,
        filename: str
    ) -> str:
        """
        Saves a professional verification document (PDF, PNG, JPG) and returns
        either a local filesystem path (local) or secure HTTPS URL (cloud).
        """
        pass

    @abstractmethod
    def delete_analysis_artifacts(self, analysis_id: str) -> bool:
        """
        Deletes all stored artifacts associated with the given analysis ID.
        """
        pass

    @abstractmethod
    def delete_all_analysis_artifacts(self) -> bool:
        """
        Deletes all stored analysis artifacts.
        """
        pass


class LocalStorageProvider(StorageProvider):
    """
    Local filesystem storage provider preserving outputs/ folder hierarchy.
    """

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or OUTPUT_DIRECTORY
        self.analysis_dir = self.base_dir / "analyses"
        self.doc_dir = self.base_dir / "verification_documents"
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        self.doc_dir.mkdir(parents=True, exist_ok=True)

    def save_analysis_artifact(
        self,
        analysis_id: str,
        file_path_or_bytes: Union[str, Path, bytes],
        filename: str
    ) -> str:
        target_dir = self.analysis_dir / analysis_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / filename

        if isinstance(file_path_or_bytes, (str, Path)):
            src_path = Path(file_path_or_bytes)
            if src_path != target_file and src_path.exists():
                shutil.copy2(src_path, target_file)
        elif isinstance(file_path_or_bytes, bytes):
            target_file.write_bytes(file_path_or_bytes)
        else:
            raise TypeError("Unsupported file data type for artifact storage")

        return f"/outputs/analyses/{analysis_id}/{filename}"

    def save_verification_document(
        self,
        user_id: str,
        doc_type: str,
        file_bytes: bytes,
        filename: str
    ) -> str:
        user_dir = self.doc_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        safe_filename = f"{doc_type}_{Path(filename).name}"
        target_file = user_dir / safe_filename
        target_file.write_bytes(file_bytes)
        return str(target_file)

    def delete_analysis_artifacts(self, analysis_id: str) -> bool:
        target_dir = self.analysis_dir / analysis_id
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
            return True
        return False

    def delete_all_analysis_artifacts(self) -> bool:
        if self.analysis_dir.exists():
            for item in self.analysis_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                elif item.is_file():
                    try:
                        item.unlink()
                    except OSError:
                        pass
            return True
        return False


class CloudinaryStorageProvider(StorageProvider):
    """
    Cloudinary storage provider uploading medical artifacts to cloud storage
    and returning persistent HTTPS URLs.
    """

    def __init__(
        self,
        cloud_name: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None
    ):
        import cloudinary
        import cloudinary.uploader
        import cloudinary.api

        self.cloud_name = cloud_name or os.getenv("CLOUDINARY_CLOUD_NAME")
        self.api_key = api_key or os.getenv("CLOUDINARY_API_KEY")
        self.api_secret = api_secret or os.getenv("CLOUDINARY_API_SECRET")

        if not all([self.cloud_name, self.api_key, self.api_secret]):
            raise ValueError(
                "Cloudinary configuration missing: CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, "
                "and CLOUDINARY_API_SECRET must all be set."
            )

        cloudinary.config(
            cloud_name=self.cloud_name,
            api_key=self.api_key,
            api_secret=self.api_secret,
            secure=True
        )
        self.uploader = cloudinary.uploader
        self.api = cloudinary.api

    def save_analysis_artifact(
        self,
        analysis_id: str,
        file_path_or_bytes: Union[str, Path, bytes],
        filename: str
    ) -> str:
        stem = Path(filename).stem
        ext = Path(filename).suffix.lower()
        resource_type = "raw" if ext in [".json", ".txt", ".pdf"] else "image"
        folder = f"hc_xcdss/analyses/{analysis_id}"
        public_id = f"{folder}/{stem}"

        upload_payload = file_path_or_bytes
        if isinstance(file_path_or_bytes, Path):
            upload_payload = str(file_path_or_bytes)

        response = self.uploader.upload(
            upload_payload,
            public_id=public_id,
            folder=folder,
            resource_type=resource_type,
            overwrite=True,
            unique_filename=False
        )
        return response.get("secure_url") or response.get("url")

    def save_verification_document(
        self,
        user_id: str,
        doc_type: str,
        file_bytes: bytes,
        filename: str
    ) -> str:
        stem = Path(filename).stem
        ext = Path(filename).suffix.lower()
        resource_type = "raw" if ext in [".pdf"] else "image"
        folder = f"hc_xcdss/verification_documents/{user_id}"
        public_id = f"{folder}/{doc_type}_{stem}"

        response = self.uploader.upload(
            file_bytes,
            public_id=public_id,
            folder=folder,
            resource_type=resource_type,
            overwrite=True,
            unique_filename=False
        )
        return response.get("secure_url") or response.get("url")

    def delete_analysis_artifacts(self, analysis_id: str) -> bool:
        try:
            prefix = f"hc_xcdss/analyses/{analysis_id}/"
            for r_type in ["image", "raw"]:
                try:
                    self.api.delete_resources_by_prefix(prefix, resource_type=r_type)
                except Exception:
                    pass
            try:
                self.api.delete_folder(f"hc_xcdss/analyses/{analysis_id}")
            except Exception:
                pass
            return True
        except Exception as err:
            logger.warning(f"Failed to delete Cloudinary artifacts for analysis {analysis_id}: {err}")
            return False

    def delete_all_analysis_artifacts(self) -> bool:
        try:
            prefix = "hc_xcdss/analyses/"
            for r_type in ["image", "raw"]:
                try:
                    self.api.delete_resources_by_prefix(prefix, resource_type=r_type)
                except Exception:
                    pass
            return True
        except Exception as err:
            logger.warning(f"Failed to delete all Cloudinary analysis artifacts: {err}")
            return False


def get_storage_provider() -> StorageProvider:
    """
    Factory function returning the active StorageProvider based on environment variables.
    Defaults to LocalStorageProvider.
    """
    provider_name = os.getenv("STORAGE_PROVIDER", "local").strip().lower()
    if provider_name == "cloudinary":
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        api_key = os.getenv("CLOUDINARY_API_KEY")
        api_secret = os.getenv("CLOUDINARY_API_SECRET")
        if cloud_name and api_key and api_secret:
            try:
                return CloudinaryStorageProvider(cloud_name, api_key, api_secret)
            except Exception as err:
                logger.warning(
                    f"Failed to initialize CloudinaryStorageProvider ({err}). "
                    "Falling back to LocalStorageProvider."
                )
        else:
            logger.warning(
                "STORAGE_PROVIDER=cloudinary requested, but Cloudinary credentials "
                "are missing. Falling back to LocalStorageProvider."
            )

    return LocalStorageProvider()
