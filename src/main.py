"""Main entry point for Watch Number Generator application."""

import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gio
from window import WatchNumberGeneratorWindow


class WatchNumberGeneratorApp(Adw.Application):
    """Main application class."""

    def __init__(self):
        super().__init__(
            application_id="com.example.WatchNumberGenerator",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )

    def do_activate(self):
        """Called when the application is activated."""
        # Get or create the main window
        win = self.props.active_window
        if not win:
            win = WatchNumberGeneratorWindow(application=self)

        win.present()

    def do_startup(self):
        """Called when the application starts."""
        Adw.Application.do_startup(self)

        # Setup application-wide actions
        self._setup_actions()

    def _setup_actions(self):
        """Setup application actions and keyboard shortcuts."""
        # Quit action
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.quit())
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<Ctrl>Q"])

        # About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)

    def _on_about(self, action, param):
        """Show about dialog."""
        about = Adw.AboutWindow(
            transient_for=self.props.active_window,
            application_name="Watch Number Generator",
            application_icon="application-x-executable",
            developer_name="Alberto Franzin",
            version="0.1.0",
            developers=["Alberto Franzin"],
            copyright="© 2025 Alberto Franzin",
            license_type=Gtk.License.GPL_3_0,
            website="https://github.com/yourusername/watch-number-generator",
            issue_url="https://github.com/yourusername/watch-number-generator/issues",
        )
        about.present()


def main():
    """Main function."""
    app = WatchNumberGeneratorApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
