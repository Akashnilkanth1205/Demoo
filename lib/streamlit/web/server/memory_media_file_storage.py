# Copyright 2018-2022 Streamlit Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""MediaFileStorage implementation that stores files in memory."""

import contextlib
import hashlib
import mimetypes
from typing import Union, NamedTuple, Dict, Optional, List

from streamlit.logger import get_logger
from streamlit.runtime.media_file_storage import MediaFileStorage, MediaFileStorageError
from streamlit.runtime.stats import CacheStatsProvider, CacheStat

LOGGER = get_logger(__name__)

PREFERRED_MIMETYPE_EXTENSION_MAP = {
    "image/jpeg": ".jpeg",
    "audio/wav": ".wav",
}


def _calculate_file_id(
    data: bytes, mimetype: str, filename: Optional[str] = None
) -> str:
    """Hash data, mimetype, and an optional filename to generate a stable file ID.

    Parameters
    ----------
    data
        Content of in-memory file in bytes. Other types will throw TypeError.
    mimetype
        Any string. Will be converted to bytes and used to compute a hash.
    filename
        Any string. Will be converted to bytes and used to compute a hash.
    """
    filehash = hashlib.new("sha224")
    filehash.update(data)
    filehash.update(bytes(mimetype.encode()))

    if filename is not None:
        filehash.update(bytes(filename.encode()))

    return filehash.hexdigest()


def _get_extension_for_mimetype(mimetype: str) -> str:
    # Python mimetypes preference was changed in Python versions, so we specify
    # a preference first and let Python's mimetypes library guess the rest.
    # See https://bugs.python.org/issue4963
    #
    # Note: Removing Python 3.6 support would likely eliminate this code
    if mimetype in PREFERRED_MIMETYPE_EXTENSION_MAP:
        return PREFERRED_MIMETYPE_EXTENSION_MAP[mimetype]

    extension = mimetypes.guess_extension(mimetype)
    if extension is None:
        return ""

    return extension


class MemoryFile(NamedTuple):
    content: bytes
    mimetype: str
    filename: Optional[str]


class MemoryMediaFileStorage(MediaFileStorage, CacheStatsProvider):
    def __init__(self, media_endpoint: str):
        self._files_by_id: Dict[str, MemoryFile] = {}
        self._media_endpoint = media_endpoint

    def load_and_get_id(
        self,
        path_or_data: Union[str, bytes],
        mimetype: str,
        filename: Optional[str] = None,
    ) -> str:
        """Add a file to the manager and return its ID."""
        file_data: bytes
        if isinstance(path_or_data, str):
            file_data = self._read_file(path_or_data)
        else:
            file_data = path_or_data

        # Because our file_ids are stable, if we already have a file with the
        # given ID, we don't need to create a new one.
        file_id = _calculate_file_id(file_data, mimetype, filename)
        media_file = self._files_by_id.get(file_id)
        if media_file is None:
            LOGGER.debug("Adding media file %s", file_id)
            media_file = MemoryFile(
                content=file_data, mimetype=mimetype, filename=filename
            )
            self._files_by_id[file_id] = media_file

        return file_id

    def get_file(self, file_id: str) -> MemoryFile:
        """Return the MemoryFile with the given ID. Raise KeyError if not found."""
        return self._files_by_id[file_id]

    def get_url(self, file_id: str) -> str:
        """Get a URL for a given media file. Raise a MediaFileStorageError if
        no such file exists.
        """
        try:
            media_file = self._files_by_id[file_id]
        except KeyError as e:
            raise MediaFileStorageError(f"No media file with id '{file_id}'") from e

        extension = _get_extension_for_mimetype(media_file.mimetype)
        return f"{self._media_endpoint}/{file_id}{extension}"

    def delete_file(self, file_id: str) -> None:
        """Delete the file with the given ID."""
        # We swallow KeyErrors here - it's not an error to delete a file
        # that doesn't exist.
        with contextlib.suppress(KeyError):
            del self._files_by_id[file_id]

    def _read_file(self, filename: str) -> bytes:
        """Read a file into memory. Raise MediaFileStorageError if we can't."""
        try:
            with open(filename, "rb") as f:
                return f.read()
        except BaseException as e:
            raise MediaFileStorageError(f"Error opening '{filename}'") from e

    def get_stats(self) -> List[CacheStat]:
        # We operate on a copy of our dict, to avoid race conditions
        # with other threads that may be manipulating the cache.
        files_by_id = self._files_by_id.copy()

        stats: List[CacheStat] = []
        for file_id, file in files_by_id.items():
            stats.append(
                CacheStat(
                    category_name="st_media_file_manager",
                    cache_name="",
                    byte_length=len(file.content),
                )
            )
        return stats
