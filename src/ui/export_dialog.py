"""Export dialog for mesh export with options."""

import gi
import os
from pathlib import Path

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib, Gio


class ExportDialog(Adw.Dialog):
    """Dialog for exporting 3D mesh with various options."""

    def __init__(self, parent_window, mesh_data):
        super().__init__()

        self.parent_window = parent_window
        self.mesh_data = mesh_data
        self.selected_folder = str(Path.home() / "Downloads")

        # Create UI
        self._build_ui()

    def _build_ui(self):
        """Build the dialog UI."""
        # Set dialog properties
        self.set_title("Export Watch Numbers")
        self.set_content_width(500)
        self.set_content_height(600)

        # Main content box
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content.set_margin_start(24)
        content.set_margin_end(24)
        content.set_margin_top(24)
        content.set_margin_bottom(24)

        # Export format section
        format_group = Adw.PreferencesGroup()
        format_group.set_title("Export Format")
        format_group.set_description("Choose how to export the 3D mesh files")

        # Radio buttons for format
        self.format_individual = Gtk.CheckButton(label="Individual STL files (1.stl, 2.stl...)")
        self.format_combined = Gtk.CheckButton(label="Combined STL file (all numbers)")
        self.format_both = Gtk.CheckButton(label="Both (individual + combined)")

        # Group radio buttons
        self.format_combined.set_group(self.format_individual)
        self.format_both.set_group(self.format_individual)

        # Default to "both"
        self.format_both.set_active(True)

        format_group.add(self.format_individual)
        format_group.add(self.format_combined)
        format_group.add(self.format_both)

        content.append(format_group)

        # Destination folder section
        folder_group = Adw.PreferencesGroup()
        folder_group.set_title("Destination")

        # Folder row
        folder_row = Adw.ActionRow()
        folder_row.set_title("Folder")

        # Folder label and button
        folder_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        self.folder_label = Gtk.Label(label=self.selected_folder)
        self.folder_label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        self.folder_label.set_max_width_chars(30)
        self.folder_label.add_css_class("dim-label")

        browse_button = Gtk.Button(label="Browse...")
        browse_button.connect("clicked", self._on_browse_folder)

        folder_box.append(self.folder_label)
        folder_box.append(browse_button)

        folder_row.add_suffix(folder_box)
        folder_group.add(folder_row)

        # Filename row
        filename_row = Adw.EntryRow()
        filename_row.set_title("Base Filename")
        self.filename_entry = filename_row
        self.filename_entry.set_text("watch_numbers")

        folder_group.add(filename_row)

        content.append(folder_group)

        # Options section
        options_group = Adw.PreferencesGroup()
        options_group.set_title("Export Options")

        # Include PNG preview
        self.include_png_row = Adw.SwitchRow()
        self.include_png_row.set_title("Include 2D Preview Image")
        self.include_png_row.set_subtitle("Export PNG render of the dial")
        self.include_png_row.set_active(True)
        options_group.add(self.include_png_row)

        # Include README
        self.include_readme_row = Adw.SwitchRow()
        self.include_readme_row.set_title("Include README File")
        self.include_readme_row.set_subtitle("Export parameters and print settings")
        self.include_readme_row.set_active(True)
        options_group.add(self.include_readme_row)

        # OBJ format option
        self.include_obj_row = Adw.SwitchRow()
        self.include_obj_row.set_title("Also Export OBJ Format")
        self.include_obj_row.set_subtitle("Export mesh in Wavefront OBJ format")
        self.include_obj_row.set_active(False)
        options_group.add(self.include_obj_row)

        content.append(options_group)

        # Mesh info section
        info_group = Adw.PreferencesGroup()
        info_group.set_title("Mesh Information")

        # Extract mesh info
        mesh = self.mesh_data.get("mesh")
        numbers_count = self.mesh_data.get("numbers_count", 0)
        triangles = self.mesh_data.get("triangles", 0)
        dimensions = self.mesh_data.get("dimensions", (0, 0, 0))

        # Create info labels
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        info_box.set_margin_start(12)
        info_box.set_margin_end(12)
        info_box.set_margin_top(8)
        info_box.set_margin_bottom(8)

        info_items = [
            f"Numbers: {numbers_count}",
            f"Triangles: {triangles:,}",
            f"Size: {dimensions[0]:.1f} × {dimensions[1]:.1f} × {dimensions[2]:.1f} mm",
            "Status: ✓ Ready to export"
        ]

        for item in info_items:
            label = Gtk.Label(label=item)
            label.set_xalign(0)
            label.add_css_class("dim-label")
            info_box.append(label)

        info_group.add(info_box)
        content.append(info_group)

        # Action buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.END)
        button_box.set_margin_top(12)

        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.connect("clicked", lambda _: self.close())

        self.export_button = Gtk.Button(label="Export")
        self.export_button.add_css_class("suggested-action")
        self.export_button.connect("clicked", self._on_export)

        button_box.append(cancel_button)
        button_box.append(self.export_button)

        content.append(button_box)

        # Set content
        self.set_child(content)

    def _on_browse_folder(self, button):
        """Handle browse folder button click."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Export Folder")
        dialog.set_modal(True)

        # Set initial folder
        initial_folder = Gio.File.new_for_path(self.selected_folder)
        dialog.set_initial_folder(initial_folder)

        # Show dialog
        dialog.select_folder(self.parent_window, None, self._on_folder_selected)

    def _on_folder_selected(self, dialog, result):
        """Handle folder selection."""
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                self.selected_folder = folder.get_path()
                self.folder_label.set_text(self.selected_folder)
        except Exception as e:
            print(f"Folder selection cancelled or error: {e}")

    def _on_export(self, button):
        """Handle export button click."""
        # Disable button to prevent double-click
        self.export_button.set_sensitive(False)
        self.export_button.set_label("Exporting...")

        # Get export options
        options = {
            "folder": self.selected_folder,
            "base_filename": self.filename_entry.get_text(),
            "format_individual": self.format_individual.get_active(),
            "format_combined": self.format_combined.get_active(),
            "format_both": self.format_both.get_active(),
            "include_png": self.include_png_row.get_active(),
            "include_readme": self.include_readme_row.get_active(),
            "include_obj": self.include_obj_row.get_active(),
        }

        # Validate options
        if not options["base_filename"]:
            self._show_error("Please enter a base filename")
            self.export_button.set_sensitive(True)
            self.export_button.set_label("Export")
            return

        # Emit signal to parent with export options
        # Parent window will handle actual export
        self.emit("export-requested", options)

        # Close dialog
        self.close()

    def _show_error(self, message):
        """Show error message."""
        # Create error dialog
        error_dialog = Adw.AlertDialog()
        error_dialog.set_heading("Export Error")
        error_dialog.set_body(message)
        error_dialog.add_response("ok", "OK")
        error_dialog.set_default_response("ok")
        error_dialog.set_close_response("ok")
        error_dialog.present(self.parent_window)


# Register signal for export-requested
from gi.repository import GObject

GObject.signal_new(
    "export-requested",
    ExportDialog,
    GObject.SignalFlags.RUN_FIRST,
    None,
    (object,)  # Parameter: export options dict
)
