# -*- coding: utf-8 -*-

"""
Classes for drawing maps.

"""

from __future__ import (absolute_import, division, print_function)

import json

from collections import OrderedDict

from branca.element import CssLink, Element, Figure, Html, JavascriptLink, MacroElement  # noqa

from folium.utilities import _validate_coordinates, get_bounds

from jinja2 import Template

from six import binary_type, text_type


class Layer(MacroElement):
    """An abstract class for everything that is a Layer on the map.
    It will be used to define whether an object will be included in
    LayerControls.

    Parameters
    ----------
    name : string, default None
        The name of the Layer, as it will appear in LayerControls
    overlay : bool, default False
        Adds the layer as an optional overlay (True) or the base layer (False).
    control : bool, default True
        Whether the Layer will be included in LayerControls.
    """
    def __init__(self, name=None, overlay=False, control=True):
        super(Layer, self).__init__()
        self.layer_name = name if name is not None else self.get_name()
        self.overlay = overlay
        self.control = control


class FeatureGroup(Layer):
    """
    Create a FeatureGroup layer ; you can put things in it and handle them
    as a single layer.  For example, you can add a LayerControl to
    tick/untick the whole group.

    Parameters
    ----------
    name : str, default None
        The name of the featureGroup layer.
        It will be displayed in the LayerControl.
        If None get_name() will be called to get the technical (ugly) name.
    overlay : bool, default True
        Whether your layer will be an overlay (ticked with a check box in
        LayerControls) or a base layer (ticked with a radio button).
    """
    def __init__(self, name=None, overlay=True, control=True):
        super(FeatureGroup, self).__init__(overlay=overlay, control=control, name=name)  # noqa
        self._name = 'FeatureGroup'

        self.tile_name = name if name is not None else self.get_name()

        self._template = Template(u"""
        {% macro script(this, kwargs) %}
            var {{this.get_name()}} = L.featureGroup(
                ).addTo({{this._parent.get_name()}});
        {% endmacro %}
        """)


class LayerControl(MacroElement):
    """
    Creates a LayerControl object to be added on a folium map.

    Parameters
    ----------
    position : str
          The position of the control (one of the map corners), can be
          'topleft', 'topright', 'bottomleft' or 'bottomright'
          default: 'topright'
    collapsed : boolean
          If true the control will be collapsed into an icon and expanded on
          mouse hover or touch.
          default: True
    autoZIndex : boolean
          If true the control assigns zIndexes in increasing order to all of
          its layers so that the order is preserved when switching them on/off.
          default: True
    """
    def __init__(self, position='topright', collapsed=True, autoZIndex=True):
        super(LayerControl, self).__init__()
        self._name = 'LayerControl'
        self.position = position
        self.collapsed = str(collapsed).lower()
        self.autoZIndex = str(autoZIndex).lower()
        self.base_layers = OrderedDict()
        self.overlays = OrderedDict()

        self._template = Template("""
        {% macro script(this,kwargs) %}
            var {{this.get_name()}} = {
                base_layers : { {% for key,val in this.base_layers.items() %}"{{key}}" : {{val}},{% endfor %} },
                overlays : { {% for key,val in this.overlays.items() %}"{{key}}" : {{val}},{% endfor %} }
                };
            L.control.layers(
                {{this.get_name()}}.base_layers,
                {{this.get_name()}}.overlays,
                {position: '{{this.position}}',
                 collapsed: {{this.collapsed}},
                 autoZIndex: {{this.autoZIndex}}
                }).addTo({{this._parent.get_name()}});
        {% endmacro %}
        """)  # noqa

    def render(self, **kwargs):
        """Renders the HTML representation of the element."""
        # We select all Layers for which (control and not overlay).
        self.base_layers = OrderedDict(
            [(val.layer_name, val.get_name()) for key, val in
             self._parent._children.items() if isinstance(val, Layer) and
             (not hasattr(val, 'overlay') or not val.overlay) and
             (not hasattr(val, 'control') or val.control)])
        # We select all Layers for which (control and overlay).
        self.overlays = OrderedDict(
            [(val.layer_name, val.get_name()) for key, val in
             self._parent._children.items() if isinstance(val, Layer) and
             (hasattr(val, 'overlay') and val.overlay) and
             (not hasattr(val, 'control') or val.control)])
        super(LayerControl, self).render()


class Icon(MacroElement):
    """
    Creates an Icon object that will be rendered
    using Leaflet.awesome-markers.

    Parameters
    ----------
    color : str, default 'blue'
        The color of the marker. You can use:

            ['red', 'blue', 'green', 'purple', 'orange', 'darkred',
             'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue',
             'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen',
             'gray', 'black', 'lightgray']

    icon_color : str, default 'white'
        The color of the drawing on the marker. You can use colors above,
        or an html color code.
    icon : str, default 'info-sign'
        The name of the marker sign.
        See Font-Awesome website to choose yours.
        Warning : depending on the icon you choose you may need to adapt
        the `prefix` as well.
    angle : int, default 0
        The icon will be rotated by this amount of degrees.
    prefix : str, default 'glyphicon'
        The prefix states the source of the icon. 'fa' for font-awesome or
        'glyphicon' for bootstrap 3.

    For more details see:
    https://github.com/lvoogdt/Leaflet.awesome-markers
    """
    def __init__(self, color='blue', icon_color='white', icon='info-sign',
                 angle=0, prefix='glyphicon'):
        super(Icon, self).__init__()
        self._name = 'Icon'
        self.color = color
        self.icon = icon
        self.icon_color = icon_color
        self.angle = angle
        self.prefix = prefix

        self._template = Template(u"""
            {% macro script(this, kwargs) %}

                var {{this.get_name()}} = L.AwesomeMarkers.icon({
                    icon: '{{this.icon}}',
                    iconColor: '{{this.icon_color}}',
                    markerColor: '{{this.color}}',
                    prefix: '{{this.prefix}}',
                    extraClasses: 'fa-rotate-{{this.angle}}'
                    });
                {{this._parent.get_name()}}.setIcon({{this.get_name()}});
            {% endmacro %}
            """)


class Marker(MacroElement):
    """
    Create a simple stock Leaflet marker on the map, with optional
    popup text or Vincent visualization.

    Parameters
    ----------
    location: tuple or list, default None
        Latitude and Longitude of Marker (Northing, Easting)
    popup: string or folium.Popup, default None
        Input text or visualization for object.
    icon: Icon plugin
        the Icon plugin to use to render the marker.

    Returns
    -------
    Marker names and HTML in obj.template_vars

    Examples
    --------
    >>> Marker(location=[45.5, -122.3], popup='Portland, OR')
    >>> Marker(location=[45.5, -122.3], popup=folium.Popup('Portland, OR'))

    """
    def __init__(self, location, popup=None, tooltip=None, icon=None):
        super(Marker, self).__init__()
        self._name = 'Marker'
        self.tooltip = tooltip
        self.location = _validate_coordinates(location)
        if icon is not None:
            self.add_child(icon)
        if isinstance(popup, text_type) or isinstance(popup, binary_type):
            self.add_child(Popup(popup))
        elif popup is not None:
            self.add_child(popup)

        self._template = Template(u"""
            {% macro script(this, kwargs) %}

            var {{this.get_name()}} = L.marker(
                [{{this.location[0]}}, {{this.location[1]}}],
                {
                    icon: new L.Icon.Default()
                    }
                )
                {% if this.tooltip %}.bindTooltip("{{this.tooltip.__str__()}}"){% endif %}
                .addTo({{this._parent.get_name()}});
            {% endmacro %}
            """)

    def _get_self_bounds(self):
        """
        Computes the bounds of the object itself (not including it's children)
        in the form [[lat_min, lon_min], [lat_max, lon_max]].

        """
        return get_bounds(self.location)


class Popup(Element):
    """Create a Popup instance that can be linked to a Layer.

    Parameters
    ----------
    html: string or Element
        Content of the Popup.
    parse_html: bool, default False
        True if the popup is a template that needs to the rendered first.
    max_width: int, default 300
        The maximal width of the popup.
    """
    def __init__(self, html=None, parse_html=False, max_width=300):
        super(Popup, self).__init__()
        self._name = 'Popup'
        self.header = Element()
        self.html = Element()
        self.script = Element()

        self.header._parent = self
        self.html._parent = self
        self.script._parent = self

        script = not parse_html

        if isinstance(html, Element):
            self.html.add_child(html)
        elif isinstance(html, text_type) or isinstance(html, binary_type):
            self.html.add_child(Html(text_type(html), script=script))

        self.max_width = max_width

        self._template = Template(u"""
            var {{this.get_name()}} = L.popup({maxWidth: '{{this.max_width}}'});

            {% for name, element in this.html._children.items() %}
                var {{name}} = $('{{element.render(**kwargs).replace('\\n',' ')}}')[0];
                {{this.get_name()}}.setContent({{name}});
            {% endfor %}

            {{this._parent.get_name()}}.bindPopup({{this.get_name()}});

            {% for name, element in this.script._children.items() %}
                {{element.render()}}
            {% endfor %}
        """)  # noqa

    def render(self, **kwargs):
        """Renders the HTML representation of the element."""
        for name, child in self._children.items():
            child.render(**kwargs)

        figure = self.get_root()
        assert isinstance(figure, Figure), ('You cannot render this Element '
                                            'if it is not in a Figure.')

        figure.script.add_child(Element(
            self._template.render(this=self, kwargs=kwargs)),
            name=self.get_name())


class FitBounds(MacroElement):
    """Fit the map to contain a bounding box with the
    maximum zoom level possible.

    Parameters
    ----------
    bounds: list of (latitude, longitude) points
        Bounding box specified as two points [southwest, northeast]
    padding_top_left: (x, y) point, default None
        Padding in the top left corner. Useful if some elements in
        the corner, such as controls, might obscure objects you're zooming
        to.
    padding_bottom_right: (x, y) point, default None
        Padding in the bottom right corner.
    padding: (x, y) point, default None
        Equivalent to setting both top left and bottom right padding to
        the same value.
    max_zoom: int, default None
        Maximum zoom to be used.
    """
    def __init__(self, bounds, padding_top_left=None,
                 padding_bottom_right=None, padding=None, max_zoom=None):
        super(FitBounds, self).__init__()
        self._name = 'FitBounds'
        self.bounds = json.loads(json.dumps(bounds))
        options = {
            'maxZoom': max_zoom,
            'paddingTopLeft': padding_top_left,
            'paddingBottomRight': padding_bottom_right,
            'padding': padding,
        }
        self.fit_bounds_options = json.dumps({key: val for key, val in
                                              options.items() if val},
                                             sort_keys=True)

        self._template = Template(u"""
            {% macro script(this, kwargs) %}
                {% if this.autobounds %}
                    var autobounds = L.featureGroup({{ this.features }}).getBounds()
                {% endif %}

                {{this._parent.get_name()}}.fitBounds(
                    {% if this.bounds %}{{ this.bounds }}{% else %}"autobounds"{% endif %},
                    {{ this.fit_bounds_options }}
                    );
            {% endmacro %}
            """)  # noqa
