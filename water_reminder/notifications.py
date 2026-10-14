from collections.abc import Callable

from windows_toasts import (
    InteractableWindowsToaster,
    Toast,
    ToastActivatedEventArgs,
    ToastButton,
)
from windows_toasts.toast_document import ToastDocument
from winrt.windows.data.xml.dom import XmlDocument
from winrt.windows.ui.notifications import (
    NotificationSetting,
    ToastFailedEventArgs,
    ToastNotification,
)

from .paths import APP_ID, APP_NAME
from .reminders import Action, Reminder


def build_document(toast: Toast) -> XmlDocument:
    document = ToastDocument(toast)
    document.SetAttribute(document.bindingNode, "template", "ToastGeneric")
    document.SetAttribute(document.GetElementByTagName("toast"), "launch", toast.tag)
    for index, text in enumerate(toast.text_fields):
        document.SetTextFieldStatic(index, text or "")
    for action in toast.actions:
        document.AddAction(action)
    return document.xmlDocument


class Notifications:
    def __init__(
        self,
        activated: Callable[[str, Action], None],
        failed: Callable[[str, str], None],
        open_settings: Callable[[], None],
        app_id: str = APP_ID,
    ) -> None:
        self.activated = activated
        self.failed = failed
        self.open_settings = open_settings
        self.toaster = InteractableWindowsToaster(APP_NAME, notifierAUMID=app_id)
        self.current: Toast | None = None
        self.native: ToastNotification | None = None
        self.clear()

    def show(self, reminder: Reminder, message: str) -> None:
        self.clear()
        toast = Toast(["Petite pause hydratation", message])
        toast.AddAction(ToastButton("J'ai bu !", "drink"))
        toast.AddAction(ToastButton("Rappeler dans 10 min", "snooze"))

        def on_activated(event: ToastActivatedEventArgs) -> None:
            if event.arguments == "drink":
                self.activated(reminder.token, "drink")
            elif event.arguments == "snooze":
                self.activated(reminder.token, "snooze")
            else:
                self.open_settings()

        def on_failed(event: ToastFailedEventArgs) -> None:
            self.failed(reminder.token, f"Windows n'a pas affiché le rappel : {event.error_code}")

        toast.on_activated = on_activated
        toast.on_failed = on_failed
        self.current = toast
        # Keep the SDK object so clear() can hide the banner as well as its history entry.
        native = ToastNotification(build_document(toast))
        native.tag = toast.tag
        native.group = "hydration"
        native.add_activated(
            lambda _, event: on_activated(ToastActivatedEventArgs.fromWinRt(event))
        )
        native.add_failed(lambda _, event: on_failed(event))
        self.native = native
        self.toaster.toastNotifier.show(native)
        # Windows creates notification settings for a new AUMID on its first delivery.
        setting = self.toaster.toastNotifier.setting
        if setting != NotificationSetting.ENABLED:
            self.clear()
            raise RuntimeError(
                f"Les notifications Windows sont désactivées ({setting.name}). "
                "Activez-les dans Paramètres Windows > Système > Notifications."
            )

    def clear(self) -> None:
        if self.native is not None:
            self.toaster.toastNotifier.hide(self.native)
            self.native = None
        self.current = None
        self.toaster.clear_toasts()
