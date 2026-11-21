# -*- coding: utf-8 -*-
"""PDF mentése: Androidon a Letöltések mappába (MediaStore, engedély nélkül),
máshol a ~/Downloads mappába."""
import os
import shutil
import subprocess


def on_android():
    return "ANDROID_ARGUMENT" in os.environ


def save_pdf(src_path, display_name):
    """Visszatérés: (szöveg a felhasználónak, megnyitó függvény vagy None)."""
    if on_android():
        return _save_android(src_path, display_name)
    dest_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    if not os.path.isdir(dest_dir):
        dest_dir = os.getcwd()
    dest = os.path.join(dest_dir, display_name)
    shutil.copyfile(src_path, dest)

    def _open():
        try:
            subprocess.Popen(["xdg-open", dest])
        except OSError:
            pass
    return "Mentve: %s" % dest, _open


def _save_android(src_path, display_name):
    from jnius import autoclass

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    activity = PythonActivity.mActivity
    ContentValues = autoclass("android.content.ContentValues")
    Downloads = autoclass("android.provider.MediaStore$Downloads")
    Cols = autoclass("android.provider.MediaStore$MediaColumns")
    Environment = autoclass("android.os.Environment")

    values = ContentValues()
    values.put(Cols.DISPLAY_NAME, display_name)
    values.put(Cols.MIME_TYPE, "application/pdf")
    values.put(Cols.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS)
    resolver = activity.getContentResolver()
    uri = resolver.insert(Downloads.EXTERNAL_CONTENT_URI, values)
    if uri is None:
        raise RuntimeError("A Letöltések mappába nem sikerült írni.")
    out = resolver.openOutputStream(uri)
    with open(src_path, "rb") as f:
        data = f.read()
    try:
        out.write(data, 0, len(data))
    except Exception:                       # régebbi pyjnius: bájtlista kell
        arr = [b - 256 if b > 127 else b for b in data]
        out.write(arr, 0, len(arr))
    out.flush()
    out.close()

    def _open():
        Intent = autoclass("android.content.Intent")
        intent = Intent(Intent.ACTION_VIEW)
        intent.setDataAndType(uri, "application/pdf")
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        activity.startActivity(intent)
    return "Mentve a Letöltések mappába: %s" % display_name, _open
