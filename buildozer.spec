[app]
title = Menetrend tervező
package.name = menetrendtervezo
package.domain = hu.menetrend
source.dir = .
source.include_exts = py,png,ttf,json
source.exclude_dirs = tests,bin,.github,.buildozer
version = 0.1.0
requirements = python3,kivy==2.3.0,pillow,reportlab,charset-normalizer,pyjnius
orientation = landscape
fullscreen = 0

# Android
android.api = 33
android.minapi = 29
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = True
# Engedély nem kell: a PDF a MediaStore-on át kerül a Letöltések mappába (Android 10+).

[buildozer]
log_level = 2
warn_on_root = 1
