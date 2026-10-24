"""Publish Excalidraw scenes to excalidraw.com share backend using client-side AES-GCM encryption."""

import base64
import json
import os
import zlib
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import httpx

from excalidraw_mcp.errors import SceneError

EXCALIDRAW_POST_ENDPOINT = "https://json.excalidraw.com/api/v2/post/"
EXCALIDRAW_SHARE_BASE = "https://excalidraw.com/#json="


def export_to_excalidraw_url(
    document: dict[str, Any],
    timeout: float = 12.0,
    endpoint: str = EXCALIDRAW_POST_ENDPOINT,
) -> dict[str, str]:
    """Publish an Excalidraw document to excalidraw.com with client-side encryption.

    Flow:
    1. Serialize scene document to UTF-8 JSON.
    2. Compress byte stream using zlib.
    3. Generate a random 128-bit AES key and a 12-byte IV.
    4. Encrypt with AES-GCM.
    5. Post IV + ciphertext to excalidraw backend.
    6. Return excalidraw.com shareable link with decryption key in hash fragment.
    """
    if not isinstance(document, dict):
        raise SceneError("Document must be a valid scene dictionary")

    try:
        json_bytes = json.dumps(document, ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError) as err:
        raise SceneError(f"Cannot serialize document to JSON: {err}") from err

    try:
        compressed_data = zlib.compress(json_bytes)
        aes_key = AESGCM.generate_key(bit_length=128)
        iv = os.urandom(12)
        aesgcm = AESGCM(aes_key)
        ciphertext = aesgcm.encrypt(iv, compressed_data, None)
        payload = iv + ciphertext
    except Exception as err:
        raise SceneError(f"Encryption failed: {err}") from err

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                endpoint,
                content=payload,
                headers={"Content-Type": "application/octet-stream"},
            )
            resp.raise_for_status()
            data = resp.json()
            doc_id = data.get("id")
            if not doc_id:
                raise SceneError("Server did not return a valid document ID")
    except httpx.TimeoutException as err:
        raise SceneError(f"Excalidraw share server timed out after {timeout}s") from err
    except httpx.HTTPStatusError as err:
        raise SceneError(
            f"Excalidraw share server returned HTTP {err.response.status_code}: {err.response.text}"
        ) from err
    except httpx.RequestError as err:
        raise SceneError(f"Network error while connecting to Excalidraw server: {err}") from err
    except Exception as err:
        raise SceneError(f"Upload to Excalidraw failed: {err}") from err

    key_b64 = base64.urlsafe_b64encode(aes_key).rstrip(b"=").decode("utf-8")
    shareable_url = f"{EXCALIDRAW_SHARE_BASE}{doc_id},{key_b64}"

    return {
        "status": "published",
        "url": shareable_url,
        "id": doc_id,
    }
