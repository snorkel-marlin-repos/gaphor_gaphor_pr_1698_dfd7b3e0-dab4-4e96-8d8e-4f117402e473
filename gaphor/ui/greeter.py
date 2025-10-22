import importlib.resources
from pathlib import Path
from typing import NamedTuple

from gi.repository import GLib, Gtk

from gaphor.abc import ActionProvider, Service
from gaphor.action import action
from gaphor.babel import translate_model
from gaphor.core import event_handler
from gaphor.diagram.hoversupport import flowbox_add_hover_support
from gaphor.event import ActiveSessionChanged, SessionCreated
from gaphor.i18n import gettext, translated_ui_string
from gaphor.ui import APPLICATION_ID


class ModelTemplate(NamedTuple):
    name: str
    icon: str
    lang: str
    filename: str


TEMPLATES = [
    ModelTemplate(gettext("Generic"), "org.gaphor.Gaphor", "UML", "blank.gaphor"),
    ModelTemplate(gettext("UML"), "UML", "UML", "uml.gaphor"),
    ModelTemplate(gettext("SysML"), "SysML", "SysML", "sysml.gaphor"),
    ModelTemplate(gettext("RAAML"), "RAAML", "RAAML", "raaml.gaphor"),
    ModelTemplate(gettext("C4 Model"), "C4Model", "C4Model", "c4model.gaphor"),
]


def new_builder(ui_file):
    builder = Gtk.Builder()
    ui_file = f"{ui_file}.glade" if Gtk.get_major_version() == 3 else f"{ui_file}.ui"
    builder.add_from_string(translated_ui_string("gaphor.ui", ui_file))
    return builder


class Greeter(Service, ActionProvider):
    def __init__(self, application, event_manager, recent_manager=None):
        self.templates = None
        self.application = application
        self.event_manager = event_manager
        self.recent_manager = recent_manager or Gtk.RecentManager.get_default()
        self.greeter: Gtk.Window = None
        self.stack: Gtk.Stack = None
        self.action_bar: Gtk.ActionBar = None
        self.back_button: Gtk.Button = None
        self.gtk_app: Gtk.Application = None
        event_manager.subscribe(self.on_session_created)

    def init(self, gtk_app):
        self.gtk_app = gtk_app

    def shutdown(self):
        self.event_manager.unsubscribe(self.on_session_created)
        if self.greeter:
            self.greeter.destroy()
        self.gtk_app = None

    def open(self, stack_name=None) -> None:
        if self.greeter and self.stack:
            self.stack.set_visible_child_name(stack_name)
            self.greeter.present()
            return

        if not stack_name:
            stack_name = (
                "recent-files" if any(self.create_recent_files()) else "new-model"
            )

        builder = new_builder("greeter")

        listbox = builder.get_object("greeter-recent-files")
        listbox.connect("row-activated", self._on_recent_file_activated)
        for widget in self.create_recent_files():
            listbox.insert(widget, -1)

        self.action_bar = builder.get_object("action-bar")
        self.back_button = builder.get_object("back-button")

        templates = builder.get_object("templates")
        templates.connect("child-activated", self._on_template_activated)
        for widget in self.create_templates():
            templates.insert(widget, -1)

        if Gtk.get_major_version() == 3:
            flowbox_add_hover_support(templates)
        self.templates = templates

        self.stack = builder.get_object("stack")
        self.stack.set_visible_child_name(stack_name)
        self.stack.connect("notify::visible-child", self._on_stack_changed)

        self.greeter = builder.get_object("greeter")
        self.greeter.set_application(self.gtk_app)
        if Gtk.get_major_version() == 3:
            self.greeter.connect("delete-event", self._on_window_close_request)
        else:
            self.greeter.connect("close-request", self._on_window_close_request)

        self.set_widgets_visible()
        self.greeter.show()
        templates.unselect_all()

    def close(self):
        if self.greeter:
            self.greeter.destroy()
            self.greeter = None
            self.stack = None

    @action(name="app.recent-files", shortcut="<Primary>n")
    def recent_files(self):
        self.open("recent-files" if any(self.create_recent_files()) else "new-model")

    @action(name="app.new-model")
    def new_model(self):
        self.open("new-model")

    def create_recent_files(self):
        for item in self.recent_manager.get_items():
            if APPLICATION_ID in item.get_applications() and item.exists():
                builder = new_builder("greeter-recent-file")
                filename, _host = GLib.filename_from_uri(item.get_uri())
                builder.get_object("name").set_text(str(Path(filename).stem))
                builder.get_object("filename").set_text(
                    item.get_uri_display().replace(str(Path.home()), "~")
                )
                row = builder.get_object("greeter-recent-file")
                row.filename = filename
                yield row

    def create_templates(self):
        for template in TEMPLATES:
            builder = new_builder("greeter-model-template")
            builder.get_object("template-name").set_text(template.name)
            if Gtk.get_major_version() == 3:
                builder.get_object("template-icon").set_from_icon_name(
                    template.icon, Gtk.IconSize.DIALOG
                )
            else:
                builder.get_object("template-icon").set_from_icon_name(template.icon)
            child = builder.get_object("model-template")
            child.filename = template.filename
            child.lang = template.lang
            yield child

    @event_handler(SessionCreated, ActiveSessionChanged)
    def on_session_created(self, _event=None):
        self.close()

    def _on_stack_changed(self, stack: Gtk.Stack, gparam_object):
        self.set_widgets_visible()

    def set_widgets_visible(self):
        visible = self.stack.get_visible_child_name()
        if visible == "new-model":
            self.action_bar.set_visible(False)
            if any(self.create_recent_files()):
                self.back_button.set_visible(True)
            else:
                self.back_button.set_visible(False)
            self.greeter.set_title(gettext("Create a New Model"))
        else:
            self.action_bar.set_visible(True)
            self.back_button.set_visible(False)
            self.greeter.set_title(gettext("Open a Recent Model"))

    def _on_recent_file_activated(self, _listbox, row):
        filename = row.filename
        self.application.new_session(filename=filename)
        self.close()

    def _on_template_activated(self, _flowbox, child):
        filename: Path = (
            importlib.resources.files("gaphor") / "templates" / child.filename
        )
        translated_model = translate_model(filename)
        session = self.application.new_session(template=translated_model)
        session.get_service("properties").set("modeling-language", child.lang)
        self.close()

    def _on_window_close_request(self, window, event=None):
        self.close()
        return False
