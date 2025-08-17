"""
Splash Screen / Import Hook demo
originally written for MacPython IDE by Just van Rossum
Ported to Micropython m68k by Scott Small

INSTRUCTIONS FOR USE:
1. Decompress the "splashscreen_imphook.rsrc.hqx" file with Stuffit Expander,
   into the same folder as "splashscreen_imphook.py". This will create a
   "splashscreen_imphook.rsrc" file.
2. Increase the memory allocation of the micropython application to 4096kb.
3. Double click on "splashscreen_imphook.py" to run the demo. Click to exit when the
   loading bar has reached the end.
"""

# Imports
# These are needed to display the splash screen
# so they have to load before our import hook
import dialogmgr
import fontmgr
import machine
import mactypes
import qd
import resourcemgr
import sys
import textedit
import time
import toolboxutil
import uctypes


# Globals
_real__import__ = None
_progress = 0


def install_importhook():
    """
    Overrides Python's import function with our own
    """
    global _real__import__
    import builtins
    if _real__import__ is None:
        _real__import__ = builtins.__import__
        builtins.__import__ = my__import__


def uninstall_importhook():
    """
    Restores Python's original import function
    """
    global _real__import__
    import builtins
    if _real__import__ is not None:
        builtins.__import__ = _real__import__
        _real__import__ = None


def importing(module):
    """
    Updates the progress bar in the splash screen with the name of the
    module that is getting imported, and advances the bar.
    
    Note: this is very manual and only works with exactly 7 imports
    right now, if you want more/less you will need to do math and update
    the rect sizes manually
    """
    global _progress, splash
    
    qd.SetPort(splash)
    qd.TextFont(fontmgr.kFontIDGeneva)
    qd.TextSize(9)
    rect = mactypes.Rect(270, 85, 286, 413)
    qd.ForeColor(qd.whiteColor)
    if module:
        text = bytearray(b"Importing: " + module)
        textedit.TETextBox(text, len(text), rect, 0)
        if not _progress:
            qd.FrameRect(mactypes.Rect(286, 85, 294, 413))
        _progress = _progress + 59
        qd.PaintRect(mactypes.Rect(287, 86, 293, _progress))
    qd.ForeColor(qd.blackColor)
    time.sleep(1)  # only for the demo, so you can see progress advancing


def my__import__(name, globals=None, locals=None, fromlist=(), level=0):
    """
    Replacement for the Python built-in import function. Calls importing()
    with the name of the module to import, which will update the splash
    screen, and then calls the built-in import function to actually import
    the module.
    """
    try:
        return sys.modules[name]
    except KeyError:
        try:
            importing(name)
        except:
            try:
                rv = _real__import__(name, globals, locals, fromlist, level)
            finally:
                uninstall_importhook()
            return rv
        return _real__import__(name, globals, locals, fromlist, level)


def pstr(s):
    """
    Converts a Python string into a Pascal string
    """
    b = mactypes.Str255()
    b[0] = len(s)
    for i in range(len(s)):
        b[i + 1] = ord(s[i])
    return uctypes.struct(b, mactypes.ConstStringPtr)


def getText():
    """
    Gets the text that will be shown in the splash screen
    """
    text = b"\r".join([
        b"Splash Screen / Import Hook Demo",
        b"originally written for MacPython IDE by Just van Rossum",
        b"updated for Micropython m68k by Scott Small",
        b"",
        b"Built with Python %s" % sys.version
    ])
    return bytearray(text)


def drawSplashText(dialog):
    """
    Draws the text of the splash screen into the dialog
    """
    qd.SetPort(dialog)
    qd.TextSize(9)
    qd.TextFont(fontmgr.kFontIDGeneva)
    qd.ForeColor(qd.whiteColor)
    textRect = mactypes.Rect(195, 10, 270, 487)
    text = getText()
    textedit.TETextBox(text, len(text), textRect, textedit.teJustCenter)
    qd.ForeColor(qd.blackColor)


# Hide the Micropython console window
machine.HideConsole()

# Install the import hook
install_importhook()

# Open resource file and tell the resource manager to use it
rf = resourcemgr.OpenResFile(pstr("splashscreen_imphook.rsrc"))
resourcemgr.UseResFile(rf)

# Load the splash screen dialog from the resource file
splash = dialogmgr.GetNewDialog(
    468,
    uctypes.struct(0, qd.GrafPort),
    uctypes.struct(-1, qd.GrafPort)
)

# Draw the splash screen dialog, and render the text into it
dialogmgr.DrawDialog(splash)
drawSplashText(splash)

# Here's some imports that we're not actually using
# (well, except for deskmgr & toolboxevent) that will
# be picked up by our import hook and trigger the
# progress bar in the splash screen
import array
import deskmgr
import eventmgr
import io
import menumgr
import toolboxevent
import windowmgr

# Click to exit (after all imports are done)
while not toolboxevent.Button():
    deskmgr.SystemTask()

# Close resource file
resourcemgr.CloseResFile(rf)
