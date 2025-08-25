# Imports
import array
import dialogmgr
import mactypes
import qd
import resourcemgr
import uctypes

# Globals
_initialized = False
_resources = None


def pstr(s):
    """
    Converts a Python string into a Pascal string
    """
    b = mactypes.Str255()
    b[0] = len(s)
    for i in range(len(s)):
        b[i + 1] = ord(s[i])
    return uctypes.struct(b, mactypes.ConstStringPtr)


def initialize():
    """
    Opens the resource file containing the dialogs and tells the resource
    manager to use it.
    """
    global _initialized, _resources

    if _initialized:
        return

    # Open resource file and tell the resource manager to use it
    _resources = resourcemgr.OpenResFile(pstr("EasyDialogs.rsrc"))
    resourcemgr.UseResFile(_resources)
    _initialized = True


def close():
    """
    Closes the resource file containing the dialogs.
    """

    global _initialized, _resources

    if not _initialized:
        return

    # Close resource file
    resourcemgr.CloseResFile(_resources)
    _resources = None
    _initialized = False


def Message(msg, id=256, ok=None):
    """
    Displays a MESSAGE string. Returns when the user clicks the OK button or
    presses the Return key. The MESSAGE string can be at most 255 characters
    long.
    """
    initialize()

    try:
        # Load the dialog from the resource file
        d = dialogmgr.GetNewDialog(
            id,
            uctypes.struct(0, qd.GrafPort),
            uctypes.struct(-1, qd.GrafPort)
        )    

        # Set the dialog string
        tp = array.array("h", [0])
        h = uctypes.struct(0, mactypes.Handle)
        rect = mactypes.Rect(0,0,0,0)
        dialogmgr.GetDialogItem(d, 2, tp, h, rect)
        dialogmgr.SetDialogItemText(h, pstr(msg))

        # Set the ok button string
        # TODO: this will not work until the control manager is implemented
        # TODO: also we need a way to convert the Handle returned by GetDialogItem
        #  into a ControlHandle expected by the control manager
        if ok is not None:
            tp = array.array("h", [0])
            h = uctypes.struct(0, mactypes.Handle)
            rect = mactypes.Rect(0,0,0,0)
            dialogmgr.GetDialogItem(d, 1, tp, h, rect)
            #controlmgr.SetControlTitle(h, pstr(ok))

        # Make the OK button the default
        # FIXME?: This seems to have no effect, and I have no idea why.
        #  This might actually be working fine, but the dialog isn't
        #  being redrawn after setting the default item (since we're
        #  immediately hitting an exception due to ModalDialog not working)
        dialogmgr.SetDialogDefaultItem(d, dialogmgr.OK)

        # show the modal dialog
        itemHit = array.array("h", [0])
        while True:
            dialogmgr.ModalDialog(
                uctypes.struct(None, dialogmgr.ModalFilterUPP),  # FIXME: not working
                itemHit
            )
            if itemHit[0] == 1:
                return
    finally:
        close()


def AskString(prompt, default="", id=257, ok=None, cancel=None):
    """
    Displays a PROMPT string and a text entry field with a DEFAULT string.

    Returns the contents of the text entry field when the user clicks the OK
    button or presses Return. Returns None when the user clicks the Cancel
    button.

    If omitted, DEFAULT is empty.

    The PROMPT and DEFAULT strings, as well as the return value, can be at
    most 255 characters long.
    """
    initialize()

    try:
        raise NotImplementedError
    finally:
        close()


def AskPassword(prompt, default="", id=257):
    """
    Display a prompt and a text entry field with a DEFAULT string. The string
    is displayed as bullets only.

    Returns the contents of the text entry field when the user clicks the OK
    button or presses Return. Returns None when the user clicks the Cancel
    button.

    If omitted, DEFAULT is empty.

    The PROMPT and DEFAULT strings, as well as the return value, can be at
    most 255 characters long.
    """
    initialize()

    try:
        raise NotImplementedError
    finally:
        close()


def AskYesNoCancel(question, default=0, yes=None, no=None, cancel=None, id=258):
    """
    Display a QUESTION string which can be answered with Yes or No.

    Returns 1 when the user clicks the Yes button.
    Returns 0 when the user clicks the No button.
    Returns -1 when the user clicks the Cancel button.

    When the user presses Return, the DEFAULT value is returned. If omitted,
    this is 0 (No).

    The QUESTION string can be at most 255 characters.
    """
    initialize()

    try:
        raise NotImplementedError
    finally:
        close()


def test():
    """
    Some functionality to test/demo the EasyDialogs library.
    """
    Message("Testing EasyDialogs.")


if __name__ == '__main__':
    """
    If we're running EasyDialogs by double-clicking it (as opposed to importing it)
    then start running the test/demo immediately.
    """
    test()
