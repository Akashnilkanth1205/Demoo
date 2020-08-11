from streamlit.proto.Slider_pb2 import Slider as SliderProto
from streamlit.errors import StreamlitAPIException
from streamlit.js_number import JSNumber
from streamlit.js_number import JSNumberBoundsException
from streamlit.type_util import ensure_iterable
from .utils import _get_widget_ui_value


class SelectSliderMixin:
    def select_slider(
        dg, label, options=[], value=None, format_func=str, key=None,
    ):
        """Display a slider widget on a discrete set of options of any type.

        This also allows you to render a range slider by passing a two-element tuple or list as the `value`.

        Parameters
        ----------
        label : str or None
            A short label explaining to the user what this slider is for.
        options : list, tuple, numpy.ndarray, pandas.Series, or pandas.DataFrame
            Labels for the slider options. All options be cast to str
            internally by default. For pandas.DataFrame, the first column is
            selected.
        value : a supported type or a tuple/list of supported types or None
            The value of the slider when it first renders. If a tuple/list
            of two values is passed here, then a range slider with those lower
            and upper bounds is rendered. For example, if set to `(1, 10)` the
            slider will have a selectable range between 1 and 10.
            Defaults to first option.
        format_func : function
            Function to modify the display of the labels from the options.
            argument. It receives the option as an argument and its output
            will be cast to str.
        key : str
            An optional string to use as the unique key for the widget.
            If this is omitted, a key will be generated for the widget
            based on its content. Multiple widgets of the same type may
            not share the same key.

        Returns
        -------
        any value or tuple of any value
            The current value of the slider widget. The return type will match
            the data type of the value parameter.

        Examples
        --------
        >>> color = st.select_slider(
        ...     'Select a color of the rainbow',
        ...     options=['red', 'orange', 'yellow', 'green', 'blue', 'indigo', 'violet'])
        >>> st.write('My favorite color is', color)

        And here's an example of a range select slider:

        >>> start_color, end_color = st.select_slider(
        ...     'Select a range of color wavelength',
        ...     options=['red', 'orange', 'yellow', 'green', 'blue', 'indigo', 'violet'],
        ...     value=('red', 'blue'))
        >>> st.write('You selected wavelengths between', start_color, 'and', end_color)
        """

        options = ensure_iterable(options)

        if len(options) == 0:
            raise StreamlitAPIException("The `options` argument needs to be non-empty")

        is_range_value = isinstance(value, (list, tuple))
        slider_value = value

        # Convert element to index of the elements
        if is_range_value:
            slider_value = list(map(lambda v: options.index(v), value))
            start, end = slider_value
            if start > end:
                slider_value = [end, start]
        else:
            # Simplify future logic by always making value a list
            try:
                slider_value = [options.index(value)]
            except ValueError:
                if value is not None:
                    raise

                slider_value = [0]

        # Bounds checks. JSNumber produces human-readable exceptions that
        # we simply re-package as StreamlitAPIExceptions.
        # (We check `options` length here, but it's likely a MemoryError will
        # be raised first
        try:
            JSNumber.validate_int_bounds(len(options) - 1, "`max_value`")
        except JSNumberBoundsException as e:
            raise StreamlitAPIException(str(e))

        # It would be great if we could guess the number of decimal places from
        # the `step` argument, but this would only be meaningful if step were a
        # decimal. As a possible improvement we could make this function accept
        # decimals and/or use some heuristics for floats.

        slider_proto = SliderProto()
        slider_proto.label = label
        slider_proto.format = "%s"
        slider_proto.default[:] = slider_value
        slider_proto.min = 0
        slider_proto.max = len(options) - 1
        slider_proto.step = 1  # default for index changes
        slider_proto.data_type = SliderProto.INT
        slider_proto.options[:] = [str(format_func(option)) for option in options]

        ui_value = _get_widget_ui_value("slider", slider_proto, user_key=key)
        if ui_value:
            current_value = getattr(ui_value, "value")
        else:
            # Widget has not been used; fallback to the original value,
            current_value = slider_value

        # The widget always returns a float array, so convert to ints
        current_value = list(map(lambda x: options[int(x)], current_value))

        # If the original value was a list/tuple, so will be the output (and vice versa)
        return_value = tuple(current_value) if is_range_value else current_value[0]
        return dg._enqueue("slider", slider_proto, return_value)  # type: ignore
