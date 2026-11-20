"""Windows toast notifications and text-to-speech, using only what ships with Windows (PowerShell 5.1).
Text is passed through environment variables so nothing needs quoting. Fire-and-forget; failures are ignored."""
import os
import subprocess
import sys

_PS = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "WindowsPowerShell", "v1.0",
                   "powershell.exe")
_NO_WINDOW = 0x08000000  # CREATE_NO_WINDOW

_TOAST = r"""
$m=[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime]
$x=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$t=$x.GetElementsByTagName('text')
$t.Item(0).AppendChild($x.CreateTextNode($env:ARC_TITLE)) | Out-Null
$t.Item(1).AppendChild($x.CreateTextNode($env:ARC_BODY)) | Out-Null
$n=[Windows.UI.Notifications.ToastNotification]::new($x)
$n.ExpirationTime=[DateTimeOffset]::Now.AddSeconds(20)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe').Show($n)
"""
_SPEAK = r"""
Add-Type -AssemblyName System.Speech
$s=New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.Rate=1
$s.Speak($env:ARC_BODY)
"""


def _run(script: str, title: str, body: str) -> None:
    if sys.platform != "win32" or not os.path.exists(_PS):
        return
    env = dict(os.environ, ARC_TITLE=title[:120], ARC_BODY=body[:300])
    try:
        subprocess.Popen([_PS, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
                         env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=_NO_WINDOW)
    except OSError:
        pass


def toast(title: str, body: str) -> None:
    _run(_TOAST, title, body)


def speak(text: str) -> None:
    _run(_SPEAK, "", text)
