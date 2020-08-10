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
from streamlit.proto.DataFrame_pb2 import Datetime as DatetimeProto
from datetime import datetime
from pandas import Timestamp


class DatetimeMixin:
    def datetime(dg, dt):
        """Draw celebratory balloons.

        Example
        -------
        >>> st.datetime()

        ...then watch your app and get ready for a celebration!

        """
        datetime_proto = make_datetime_proto(dt)
        return dg._enqueue("datetime", datetime_proto)  # type: ignore


def make_datetime_proto(dt):
    datetime_proto = DatetimeProto()
    if isinstance(dt, Timestamp):
        datetime_proto.datetime = dt.value
        datetime_proto.timezone = dt.tz.zone if dt.tz else ""
    else:
        datetime_proto.datetime = int(dt.timestamp() * 1e9)
        datetime_proto.timezone = dt.tzinfo or ""
    return datetime_proto
