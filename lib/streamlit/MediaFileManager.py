# Copyright 2018-2020 Streamlit Inc.
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

"""Provides global MediaFileManager object as `media_file_manager`."""

import time
import typing
import hashlib
import collections
from datetime import datetime

from streamlit.logger import get_logger
from streamlit.ReportThread import get_report_ctx

LOGGER = get_logger(__name__)

STATIC_MEDIA_ENDPOINT = "/media"

# Seconds to keep media files that have been obsoleted by replacement-in-place.
# Without this, files may get scrubbed before browsers have a chance to request them.
KEEP_DELAY = 2


def _get_session_id():
    """Semantic wrapper to retrieve current ReportSession ID."""
    ctx = get_report_ctx()
    if ctx is None:
        # This is only None when running "python myscript.py" rather than
        # "streamlit run myscript.py". In which case the session ID doesn't
        # matter and can just be a constant, as there's only ever "session".
        return "dontcare"
    else:
        return ctx.session_id


def _get_file_id(data, mimetype=None):
    """
    Parameters
    ----------

    data : bytes
        Content of media file in bytes. Other types will throw TypeError.
    mimetype : str
        Any string. Will be converted to bytes and used to compute a hash.
        None will be converted to empty string.  [default: None]
    """

    if mimetype is None:
        mimetype = ""

    # Use .update() to prevent making another copy of the data to compute the hash.
    filehash = hashlib.sha224(data)
    filehash.update(bytes(mimetype.encode("utf-8")))
    return filehash.hexdigest()


class MediaFile(object):
    """Abstraction for audiovisual/image file objects."""

    def __init__(self, file_id=None, content=None, mimetype=None, session_count=1):
        self._file_id = file_id
        self._content = content
        self._mimetype = mimetype
        self.session_count = session_count

        # "Time to Die": a timestamp set slightly ahead in the future
        # so the file will not be scrubbed too quickly when it is replaced.
        # This prevents 404s on browser requests for files that were displayed
        # for a short time.
        self.ttd = KEEP_DELAY + datetime.timestamp(datetime.now())

    @property
    def url(self):
        return "{}/{}.{}".format(
            STATIC_MEDIA_ENDPOINT, self.id, self.mimetype.split("/")[1]
        )

    @property
    def id(self):
        return self._file_id

    @property
    def content(self):
        return self._content

    @property
    def mimetype(self):
        return self._mimetype


class MediaFileManager(object):
    """In-memory file manager for MediaFile objects."""

    def __init__(self):
        self._files = {}
        self._session_id_to_coordinate_map = collections.defaultdict(
            lambda: dict
        )  # type: typing.DefaultDict[str, dict[str]]

    def _scrub(self):
        """ Remove media files that have expired and are session-orphans.
        (A MediaFile is a session-orphan when its session_count < 1.)
        """
        ts = datetime.timestamp(datetime.now())
        for file_id, mf in list(self._files.items()):
            if mf.session_count == 0 and mf.ttd < ts:
                del self._files[file_id]

    def _remove(self, file_id):
        """ Given a file_id, decrements that MediaFile's session_count by one. """
        mf = self.get(file_id)
        mf.session_count -= 1

    def reset_files_for_session(self, session_id=None):
        """Clears all stored files for a given ReportSession id.

        Should be called whenever ScriptRunner completes and when
        a session ends.
        """
        if session_id is None:
            session_id = _get_session_id()

        for coordinates in self._session_id_to_coordinate_map[session_id]:
            file_id = self._session_id_to_coordinate_map[session_id][coordinates]
            self._remove(file_id)

        LOGGER.debug("Reset files for session with ID %s", session_id)
        del self._session_id_to_coordinate_map[session_id]
        LOGGER.debug("Sessions still active: %r", self._session_id_to_coordinate_map)

    def _add_to_session(self, file_id, coordinates):
        """Syntactic sugar around session->coordinate->file_id mapping."""
        # If there already was a media file at these coordinates in this session,
        # remove file from this session and save the older ID.
        old_file_id = self._session_id_to_coordinate_map[_get_session_id()].get(
            coordinates, None
        )
        if old_file_id:
            self._remove(old_file_id)

        self._session_id_to_coordinate_map[_get_session_id()][coordinates] = file_id
        self._scrub()

    def add(self, content, mimetype, coordinates):
        """Adds new MediaFile with given parameters; returns the object.

        If an identical file already exists, returns the existing object
        and increments its session_count by one.

        mimetype must be set, as this string will be used in the
        "Content-Type" header when the file is sent via HTTP GET.

        coordinates are generated for the element in DeltaGenerator.

        Parameters
        ----------
        content : bytes
            Raw data to store in file object.
        mimetype : str
            The mime type for the media file. E.g. "audio/mpeg"
        coordinates : str
            Unique string identifying an element's location.
        """
        file_id = _get_file_id(content, mimetype)

        if not file_id in self._files:
            new = MediaFile(file_id=file_id, content=content, mimetype=mimetype,)
            self._files[file_id] = new
        else:
            self._files[file_id].session_count += 1

        self._add_to_session(file_id, coordinates)
        return self._files[file_id]

    def get(self, mediafile_or_id):
        """Returns MediaFile object for given file_id or MediaFile object.

        Raises KeyError if not found.
        """
        mf = (
            mediafile_or_id
            if type(mediafile_or_id) is MediaFile
            else self._files[mediafile_or_id]
        )
        return mf

    def __contains__(self, mediafile_or_id):
        if type(mediafile_or_id) is MediaFile:
            return mediafile_or_id.id in self._files
        return mediafile_or_id in self._files

    def __len__(self):
        return len(self._files)


media_file_manager = MediaFileManager()
