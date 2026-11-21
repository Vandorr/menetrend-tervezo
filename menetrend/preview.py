# -*- coding: utf-8 -*-
"""A PDF első oldalának lerenderelése PNG-be az alkalmazáson belüli előnézethez.

Androidon a beépített android.graphics.pdf.PdfRenderer-t használja (pyjnius),
asztali gépen a `pdftoppm` programot (ha van).
"""
import os
import shutil
import subprocess

from . import storage


def render_png(pdf_path, png_path, width_px=1600):
    """PNG-t készít a PDF első oldalából; visszaadja a (szélesség, magasság) párost."""
    if storage.on_android():
        return _render_android(pdf_path, png_path, width_px)
    return _render_desktop(pdf_path, png_path, width_px)


def _render_android(pdf_path, png_path, width_px):
    from jnius import autoclass

    File = autoclass("java.io.File")
    Pfd = autoclass("android.os.ParcelFileDescriptor")
    PdfRenderer = autoclass("android.graphics.pdf.PdfRenderer")
    Bitmap = autoclass("android.graphics.Bitmap")
    Config = autoclass("android.graphics.Bitmap$Config")
    Fmt = autoclass("android.graphics.Bitmap$CompressFormat")
    Color = autoclass("android.graphics.Color")
    Fos = autoclass("java.io.FileOutputStream")

    pfd = Pfd.open(File(pdf_path), Pfd.MODE_READ_ONLY)
    renderer = PdfRenderer(pfd)
    page = renderer.openPage(0)
    try:
        w = int(width_px)
        h = int(round(w * page.getHeight() / float(page.getWidth())))
        bmp = Bitmap.createBitmap(w, h, Config.ARGB_8888)
        bmp.eraseColor(Color.WHITE)
        page.render(bmp, None, None, 1)             # 1 = RENDER_MODE_FOR_DISPLAY
        out = Fos(png_path)
        bmp.compress(Fmt.PNG, 100, out)
        out.flush()
        out.close()
        bmp.recycle()
        return w, h
    finally:
        page.close()
        renderer.close()
        pfd.close()


def _render_desktop(pdf_path, png_path, width_px):
    exe = shutil.which("pdftoppm")
    if not exe:
        raise RuntimeError("Az előnézethez asztali gépen a pdftoppm program kell (poppler).")
    stem = png_path[:-4] if png_path.endswith(".png") else png_path
    subprocess.check_call([exe, "-png", "-singlefile", "-f", "1", "-l", "1",
                           "-scale-to-x", str(int(width_px)), "-scale-to-y", "-1",
                           pdf_path, stem])
    from PIL import Image                           # a pillow úgyis függőség
    with Image.open(stem + ".png") as im:
        return im.size
