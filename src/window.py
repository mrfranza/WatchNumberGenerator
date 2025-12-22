"""Main application window."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib
from typing import Optional
from ui.preview_2d import Preview2DWidget


class WatchNumberGeneratorWindow(Adw.ApplicationWindow):
    """Main application window with sidebar and preview area."""

    def __init__(self, application: Adw.Application):
        super().__init__(application=application)

        # Window properties
        self.set_title("Watch Number Generator")
        self.set_default_size(1200, 800)

        # Main layout: OverlaySplitView (sidebar + content)
        self.split_view = Adw.OverlaySplitView()
        self.split_view.set_sidebar_position(Gtk.PackType.START)
        self.split_view.set_min_sidebar_width(320)
        self.split_view.set_max_sidebar_width(400)

        # Sidebar: Controls panel
        self.sidebar = self._create_sidebar()
        self.split_view.set_sidebar(self.sidebar)

        # Content: Preview area
        self.content = self._create_content_area()
        self.split_view.set_content(self.content)

        # Toast overlay for notifications
        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_child(self.split_view)

        # Set main content
        self.set_content(self.toast_overlay)

    def _create_sidebar(self) -> Gtk.Box:
        """Create sidebar with controls."""
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Header bar for sidebar
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        sidebar.append(header)

        # Scrolled window for controls
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # Controls container
        controls_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        controls_box.set_spacing(18)
        controls_box.set_margin_top(12)
        controls_box.set_margin_bottom(12)
        controls_box.set_margin_start(12)
        controls_box.set_margin_end(12)

        # Dimensions group
        dimensions_group = self._create_dimensions_group()
        controls_box.append(dimensions_group)

        # Number style group
        style_group = self._create_style_group()
        controls_box.append(style_group)

        # Mesh parameters group
        mesh_group = self._create_mesh_parameters_group()
        controls_box.append(mesh_group)

        # Distortion filters group
        distortion_group = self._create_distortion_group()
        controls_box.append(distortion_group)

        # Export button
        export_button = Gtk.Button(label="Export STL Files")
        export_button.add_css_class("suggested-action")
        export_button.add_css_class("pill")
        export_button.set_margin_top(12)
        export_button.connect("clicked", self._on_export_clicked)
        controls_box.append(export_button)

        scrolled.set_child(controls_box)
        sidebar.append(scrolled)

        return sidebar

    def _create_dimensions_group(self) -> Adw.PreferencesGroup:
        """Create dimensions controls group."""
        group = Adw.PreferencesGroup()
        group.set_title("Dial Dimensions")
        group.set_description("Outer and inner radius in millimeters")

        # Outer radius
        outer_row = Adw.SpinRow()
        outer_row.set_title("Outer Radius")
        outer_row.set_subtitle("Maximum dial diameter")
        outer_row.set_adjustment(
            Gtk.Adjustment(value=50.0, lower=10.0, upper=500.0, step_increment=1.0)
        )
        outer_row.set_digits(1)
        outer_row.connect("changed", self._on_dimensions_changed)
        self.outer_radius_row = outer_row
        group.add(outer_row)

        # Inner radius
        inner_row = Adw.SpinRow()
        inner_row.set_title("Inner Radius")
        inner_row.set_subtitle("Number placement boundary")
        inner_row.set_adjustment(
            Gtk.Adjustment(value=35.0, lower=5.0, upper=400.0, step_increment=1.0)
        )
        inner_row.set_digits(1)
        inner_row.connect("changed", self._on_dimensions_changed)
        self.inner_radius_row = inner_row
        group.add(inner_row)

        return group

    def _create_style_group(self) -> Adw.PreferencesGroup:
        """Create number style controls group."""
        group = Adw.PreferencesGroup()
        group.set_title("Number Style")

        # Number system (Decimal / Roman)
        number_system_row = Adw.ComboRow()
        number_system_row.set_title("Number System")
        number_system_row.set_model(
            Gtk.StringList.new(["Decimal (1-12)", "Roman (I-XII)"])
        )
        number_system_row.set_selected(0)
        number_system_row.connect("notify::selected", self._on_style_changed)
        self.number_system_row = number_system_row
        group.add(number_system_row)

        # Number set (All / Cardinals only)
        number_set_row = Adw.ComboRow()
        number_set_row.set_title("Numbers to Display")
        number_set_row.set_model(
            Gtk.StringList.new(["All (1-12)", "Cardinals Only (12, 3, 6, 9)"])
        )
        number_set_row.set_selected(0)
        number_set_row.connect("notify::selected", self._on_style_changed)
        self.number_set_row = number_set_row
        group.add(number_set_row)

        # Font selection
        font_row = Adw.ActionRow()
        font_row.set_title("Font Family")
        font_row.set_subtitle("System font for numbers")
        font_button = Gtk.FontButton()
        font_button.set_use_font(True)
        font_button.set_valign(Gtk.Align.CENTER)
        font_button.connect("font-set", self._on_font_changed)
        font_row.add_suffix(font_button)
        self.font_button = font_button
        group.add(font_row)

        return group

    def _create_mesh_parameters_group(self) -> Adw.PreferencesGroup:
        """Create mesh parameters controls group."""
        group = Adw.PreferencesGroup()
        group.set_title("Mesh Parameters")

        # Extrusion depth
        depth_row = Adw.SpinRow()
        depth_row.set_title("Extrusion Depth")
        depth_row.set_subtitle("Thickness of numbers (mm)")
        depth_row.set_adjustment(
            Gtk.Adjustment(value=2.0, lower=0.5, upper=20.0, step_increment=0.5)
        )
        depth_row.set_digits(1)
        depth_row.connect("changed", self._on_mesh_params_changed)
        self.depth_row = depth_row
        group.add(depth_row)

        # Vertical margin
        vmargin_row = Adw.SpinRow()
        vmargin_row.set_title("Vertical Margin")
        vmargin_row.set_subtitle("Top/bottom padding (mm)")
        vmargin_row.set_adjustment(
            Gtk.Adjustment(value=1.0, lower=0.0, upper=20.0, step_increment=0.5)
        )
        vmargin_row.set_digits(1)
        vmargin_row.connect("changed", self._on_mesh_params_changed)
        self.vmargin_row = vmargin_row
        group.add(vmargin_row)

        # Horizontal margin
        hmargin_row = Adw.SpinRow()
        hmargin_row.set_title("Horizontal Margin")
        hmargin_row.set_subtitle("Side padding (mm)")
        hmargin_row.set_adjustment(
            Gtk.Adjustment(value=1.0, lower=0.0, upper=20.0, step_increment=0.5)
        )
        hmargin_row.set_digits(1)
        hmargin_row.connect("changed", self._on_mesh_params_changed)
        self.hmargin_row = hmargin_row
        group.add(hmargin_row)

        return group

    def _create_distortion_group(self) -> Adw.PreferencesGroup:
        """Create distortion filters controls group."""
        group = Adw.PreferencesGroup()
        group.set_title("Distortion Filters")
        group.set_description("Add irregularities for artistic effects")

        # Enable distortion switch
        enable_row = Adw.SwitchRow()
        enable_row.set_title("Enable Distortions")
        enable_row.set_active(False)
        enable_row.connect("notify::active", self._on_distortion_toggled)
        self.distortion_enable_row = enable_row
        group.add(enable_row)

        # Distortion parameters (initially disabled)
        self.distortion_params_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.distortion_params_box.set_sensitive(False)

        # Edge irregularity
        edge_box = self._create_slider_row("Edge Irregularity", 0.0, 0.0, 5.0)
        self.edge_irregularity_scale = edge_box.scale
        self.distortion_params_box.append(edge_box)

        # Surface roughness
        rough_box = self._create_slider_row("Surface Roughness", 0.0, 0.0, 5.0)
        self.surface_roughness_scale = rough_box.scale
        self.distortion_params_box.append(rough_box)

        # Perspective deformation
        persp_box = self._create_slider_row("Perspective Stretch", 0.0, 0.0, 3.0)
        self.perspective_scale = persp_box.scale
        self.distortion_params_box.append(persp_box)

        # Erosion
        erosion_box = self._create_slider_row("Erosion (Vintage)", 0.0, 0.0, 5.0)
        self.erosion_scale = erosion_box.scale
        self.distortion_params_box.append(erosion_box)

        # Random seed
        seed_row = Adw.SpinRow()
        seed_row.set_title("Random Seed")
        seed_row.set_subtitle("For reproducible results")
        seed_row.set_adjustment(
            Gtk.Adjustment(value=42, lower=0, upper=99999, step_increment=1)
        )
        seed_row.set_digits(0)
        seed_row.connect("changed", self._on_distortion_changed)
        self.seed_row = seed_row
        self.distortion_params_box.append(seed_row)

        group.add(self.distortion_params_box)

        return group

    def _create_slider_row(
        self, title: str, default: float, min_val: float, max_val: float
    ) -> Gtk.Box:
        """Create a labeled slider row."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_spacing(6)
        box.set_margin_top(6)
        box.set_margin_bottom(6)

        label = Gtk.Label(label=title)
        label.set_xalign(0)
        label.add_css_class("title-4")
        box.append(label)

        scale = Gtk.Scale()
        scale.set_range(min_val, max_val)
        scale.set_value(default)
        scale.set_draw_value(True)
        scale.set_digits(2)
        scale.set_hexpand(True)
        scale.connect("value-changed", self._on_distortion_changed)
        box.append(scale)

        # Store scale reference in box for easy access
        box.scale = scale

        return box

    def _create_content_area(self) -> Gtk.Box:
        """Create main content area with preview."""
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Header bar for content
        header = Adw.HeaderBar()
        content.append(header)

        # Tabs for 2D/3D preview
        tab_bar = Adw.TabBar()
        tab_view = Adw.TabView()
        tab_bar.set_view(tab_view)
        tab_bar.set_autohide(False)
        content.append(tab_bar)

        # 2D Preview tab
        preview_2d_widget = Preview2DWidget()
        self.preview_2d_widget = preview_2d_widget
        tab_view.append(preview_2d_widget).set_title("2D Preview")

        # 3D Preview tab (placeholder)
        preview_3d_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        preview_3d_box.set_hexpand(True)
        preview_3d_box.set_vexpand(True)
        preview_3d_box.set_spacing(12)
        preview_3d_box.set_margin_top(48)
        preview_3d_box.set_margin_bottom(48)
        preview_3d_box.set_margin_start(48)
        preview_3d_box.set_margin_end(48)
        preview_3d_box.set_valign(Gtk.Align.CENTER)
        preview_3d_box.set_halign(Gtk.Align.CENTER)

        # Title
        title_label = Gtk.Label(label="3D Preview")
        title_label.add_css_class("title-1")
        preview_3d_box.append(title_label)

        # Info message
        info_label = Gtk.Label()
        info_label.set_markup(
            "<span size='large'>Coming Soon</span>\n\n"
            "3D mesh preview will be available in a future update.\n\n"
            "<b>Note:</b> Distortion filters are applied only during export.\n"
            "Use the 2D preview to verify number positioning and sizing."
        )
        info_label.set_justify(Gtk.Justification.CENTER)
        info_label.add_css_class("dim-label")
        preview_3d_box.append(info_label)

        tab_view.append(preview_3d_box).set_title("3D Preview")

        self.tab_view = tab_view

        content.append(tab_view)

        return content

    # Signal handlers
    def _on_dimensions_changed(self, widget):
        """Handle dimension changes."""
        # Validate inner < outer
        outer = self.outer_radius_row.get_value()
        inner = self.inner_radius_row.get_value()

        if inner >= outer - 5:  # Minimum 5mm difference
            # Don't block, just show warning and don't update preview
            self.show_toast("Inner radius must be at least 5mm smaller than outer radius")
            # Still allow the value to be set, just skip preview update
            return

        # Trigger preview update only if valid
        self._update_preview()

    def _on_style_changed(self, widget, param):
        """Handle style changes."""
        self._update_preview()

    def _on_font_changed(self, widget):
        """Handle font selection changes."""
        self._update_preview()

    def _on_mesh_params_changed(self, widget):
        """Handle mesh parameter changes."""
        self._update_preview()

    def _on_distortion_toggled(self, widget, param):
        """Handle distortion enable/disable."""
        enabled = widget.get_active()
        self.distortion_params_box.set_sensitive(enabled)
        self._update_preview()

    def _on_distortion_changed(self, widget):
        """Handle distortion parameter changes."""
        if self.distortion_enable_row.get_active():
            self._update_preview()

    def _on_export_clicked(self, widget):
        """Handle export button click."""
        self.show_toast("Export functionality coming soon!")

    def _update_preview(self):
        """Update the preview display."""
        # Get current parameters
        params = self.get_parameters()

        # Map parameter values to preview widget
        number_style = "roman" if params["number_system"] == 1 else "decimal"
        number_set = "cardinals" if params["number_set"] == 1 else "all"

        # Update the 2D preview widget
        self.preview_2d_widget.update_parameters(
            outer_radius=params["outer_radius"],
            inner_radius=params["inner_radius"],
            vertical_margin=params["vertical_margin"],
            horizontal_margin=params["horizontal_margin"],
            number_style=number_style,
            number_set=number_set,
            font_desc=params["font"],
            edge_irregularity=params["edge_irregularity"],
            surface_roughness=params["surface_roughness"],
            perspective_stretch=params["perspective_stretch"],
            erosion=params["erosion"],
        )

    def show_toast(self, message: str):
        """Show a toast notification."""
        toast = Adw.Toast.new(message)
        toast.set_timeout(3)
        self.toast_overlay.add_toast(toast)

    def get_parameters(self) -> dict:
        """Get current parameter values."""
        return {
            "outer_radius": self.outer_radius_row.get_value(),
            "inner_radius": self.inner_radius_row.get_value(),
            "number_system": self.number_system_row.get_selected(),
            "number_set": self.number_set_row.get_selected(),
            "font": self.font_button.get_font(),
            "extrusion_depth": self.depth_row.get_value(),
            "vertical_margin": self.vmargin_row.get_value(),
            "horizontal_margin": self.hmargin_row.get_value(),
            "distortion_enabled": self.distortion_enable_row.get_active(),
            "edge_irregularity": self.edge_irregularity_scale.get_value(),
            "surface_roughness": self.surface_roughness_scale.get_value(),
            "perspective_stretch": self.perspective_scale.get_value(),
            "erosion": self.erosion_scale.get_value(),
            "random_seed": int(self.seed_row.get_value()),
        }
