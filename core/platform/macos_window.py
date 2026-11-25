"""
macOS foreground-window and idle-time backend via Quartz / AppKit ctypes.

Uses CoreGraphics for idle time and window titles, and NSWorkspace for the
frontmost application. Window titles may be empty without Accessibility
permission; app name + PID still work without it.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional

import ctypes
import ctypes.util

logger = logging.getLogger(__name__)

# CGEventSourceStateID / CGEventType constants
kCGEventSourceStateCombinedSessionState = 0
kCGAnyInputEventType = 0xFFFFFFFF  # ~0 as UInt32

# CGWindowList option bits
kCGWindowListOptionOnScreenOnly = 1 << 0
kCGWindowListExcludeDesktopElements = 1 << 4

_accessibility_hint_logged = False


def _load_framework(name: str) -> ctypes.CDLL:
    path = ctypes.util.find_library(name)
    if not path:
        # Fallback to absolute framework paths on modern macOS
        path = f"/System/Library/Frameworks/{name}.framework/{name}"
    return ctypes.CDLL(path)


class MacOSWindowBackend:
    """Probes frontmost app via NSWorkspace and idle via CoreGraphics."""

    def __init__(self) -> None:
        self._cg = None
        self._cf = None
        self._objc = None
        self._ns_string_utf8 = None
        self._ready = False
        try:
            self._cg = _load_framework("CoreGraphics")
            self._cf = _load_framework("CoreFoundation")
            self._objc = _load_framework("objc")
            self._setup_objc()
            self._setup_cg()
            self._ready = True
        except Exception as e:
            logger.warning(f"macOS window backend init failed: {e}")

    def _setup_objc(self) -> None:
        objc = self._objc
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        objc.objc_msgSend.restype = ctypes.c_void_p
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

        # Ensure AppKit is loaded so NSWorkspace is available
        try:
            _load_framework("AppKit")
        except Exception:
            pass

    def _setup_cg(self) -> None:
        cg = self._cg
        cg.CGEventSourceSecondsSinceLastEventType.restype = ctypes.c_double
        cg.CGEventSourceSecondsSinceLastEventType.argtypes = [
            ctypes.c_uint32,
            ctypes.c_uint32,
        ]
        cg.CGWindowListCopyWindowInfo.restype = ctypes.c_void_p
        cg.CGWindowListCopyWindowInfo.argtypes = [ctypes.c_uint32, ctypes.c_uint32]

        cf = self._cf
        cf.CFArrayGetCount.restype = ctypes.c_long
        cf.CFArrayGetCount.argtypes = [ctypes.c_void_p]
        cf.CFArrayGetValueAtIndex.restype = ctypes.c_void_p
        cf.CFArrayGetValueAtIndex.argtypes = [ctypes.c_void_p, ctypes.c_long]
        cf.CFDictionaryGetValue.restype = ctypes.c_void_p
        cf.CFDictionaryGetValue.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        cf.CFStringGetCStringPtr.restype = ctypes.c_char_p
        cf.CFStringGetCStringPtr.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        cf.CFStringGetCString.restype = ctypes.c_bool
        cf.CFStringGetCString.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_long,
            ctypes.c_uint32,
        ]
        cf.CFNumberGetValue.restype = ctypes.c_bool
        cf.CFNumberGetValue.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        cf.CFRelease.argtypes = [ctypes.c_void_p]

        # kCFStringEncodingUTF8 = 0x08000100
        self._utf8 = 0x08000100
        # kCFNumberIntType = 9
        self._cf_number_int = 9

        # Cache CFSTR keys via objc NSString
        self._key_owner_pid = self._ns_string("kCGWindowOwnerPID")
        self._key_name = self._ns_string("kCGWindowName")
        self._key_layer = self._ns_string("kCGWindowLayer")
        # Prefer constant pointers when available
        try:
            # CoreGraphics exports these as CFStringRef globals
            self._key_owner_pid = ctypes.c_void_p.in_dll(cg, "kCGWindowOwnerPID")
            self._key_name = ctypes.c_void_p.in_dll(cg, "kCGWindowName")
            self._key_layer = ctypes.c_void_p.in_dll(cg, "kCGWindowLayer")
        except Exception:
            pass

    def _sel(self, name: str) -> ctypes.c_void_p:
        return self._objc.sel_registerName(name.encode("utf-8"))

    def _cls(self, name: str) -> ctypes.c_void_p:
        return self._objc.objc_getClass(name.encode("utf-8"))

    def _msg(self, obj: ctypes.c_void_p, sel_name: str) -> ctypes.c_void_p:
        return self._objc.objc_msgSend(obj, self._sel(sel_name))

    def _ns_string(self, text: str) -> ctypes.c_void_p:
        """Create an autoreleased NSString from a Python str."""
        NSString = self._cls("NSString")
        sel = self._sel("stringWithUTF8String:")
        # objc_msgSend with extra arg
        objc_msgSend = self._objc.objc_msgSend
        objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p]
        result = objc_msgSend(NSString, sel, text.encode("utf-8"))
        # restore default argtypes
        objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        return result

    def _cf_string_to_str(self, cf_str: ctypes.c_void_p) -> str:
        if not cf_str:
            return ""
        ptr = self._cf.CFStringGetCStringPtr(cf_str, self._utf8)
        if ptr:
            return ptr.decode("utf-8", errors="replace")
        buf = ctypes.create_string_buffer(4096)
        if self._cf.CFStringGetCString(cf_str, buf, 4096, self._utf8):
            return buf.value.decode("utf-8", errors="replace")
        return ""

    def _cf_number_to_int(self, cf_num: ctypes.c_void_p) -> int:
        if not cf_num:
            return 0
        value = ctypes.c_int(0)
        if self._cf.CFNumberGetValue(cf_num, self._cf_number_int, ctypes.byref(value)):
            return int(value.value)
        return 0

    def get_idle_seconds(self) -> float:
        if not self._ready:
            return 0.0
        try:
            seconds = self._cg.CGEventSourceSecondsSinceLastEventType(
                kCGEventSourceStateCombinedSessionState,
                kCGAnyInputEventType,
            )
            return max(0.0, float(seconds))
        except Exception as e:
            logger.debug(f"Error querying macOS idle info: {e}")
            return 0.0

    def _frontmost_app(self) -> Dict[str, Any]:
        app_name = "Unknown"
        pid = 0
        try:
            NSWorkspace = self._cls("NSWorkspace")
            workspace = self._msg(NSWorkspace, "sharedWorkspace")
            app = self._msg(workspace, "frontmostApplication")
            if not app:
                return {"app_name": app_name, "pid": pid}

            # localizedName
            name_obj = self._msg(app, "localizedName")
            if name_obj:
                # UTF8String
                objc_msgSend = self._objc.objc_msgSend
                objc_msgSend.restype = ctypes.c_char_p
                objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
                c_str = objc_msgSend(name_obj, self._sel("UTF8String"))
                objc_msgSend.restype = ctypes.c_void_p
                objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
                if c_str:
                    app_name = c_str.decode("utf-8", errors="replace")

            # processIdentifier (returns int / pid_t)
            objc_msgSend = self._objc.objc_msgSend
            # Use objc_msgSend with restype c_int for scalar return
            try:
                msg_int = ctypes.CFUNCTYPE(
                    ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p
                )(("objc_msgSend", self._objc))
                pid = int(msg_int(app, self._sel("processIdentifier")))
            except Exception:
                # Fallback via psutil not needed if PID fails
                pid = 0
        except Exception as e:
            logger.debug(f"Error querying frontmost app: {e}")
        return {"app_name": app_name or "Unknown", "pid": pid}

    def _window_title_for_pid(self, pid: int) -> str:
        if not self._ready or pid <= 0:
            return ""
        window_list = None
        try:
            options = kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements
            window_list = self._cg.CGWindowListCopyWindowInfo(options, 0)
            if not window_list:
                return ""

            count = self._cf.CFArrayGetCount(window_list)
            best_title = ""
            for i in range(count):
                entry = self._cf.CFArrayGetValueAtIndex(window_list, i)
                if not entry:
                    continue
                owner = self._cf.CFDictionaryGetValue(entry, self._key_owner_pid)
                owner_pid = self._cf_number_to_int(owner)
                if owner_pid != pid:
                    continue
                layer_ref = self._cf.CFDictionaryGetValue(entry, self._key_layer)
                layer = self._cf_number_to_int(layer_ref)
                # Normal app windows are layer 0
                if layer != 0:
                    continue
                name_ref = self._cf.CFDictionaryGetValue(entry, self._key_name)
                title = self._cf_string_to_str(name_ref).strip()
                if title:
                    return title
            return best_title
        except Exception as e:
            logger.debug(f"Error reading CGWindowList: {e}")
            return ""
        finally:
            if window_list:
                try:
                    self._cf.CFRelease(window_list)
                except Exception:
                    pass

    def get_foreground(self) -> Dict[str, Any]:
        global _accessibility_hint_logged

        if not self._ready:
            return {
                "app_name": "Unknown",
                "window_title": "Desktop / Idle",
                "pid": 0,
            }

        front = self._frontmost_app()
        app_name = front.get("app_name") or "Unknown"
        pid = int(front.get("pid") or 0)
        window_title = self._window_title_for_pid(pid)

        if not window_title:
            window_title = app_name if app_name != "Unknown" else "Desktop / Idle"
            if not _accessibility_hint_logged and app_name != "Unknown":
                _accessibility_hint_logged = True
                logger.info(
                    "macOS window titles are empty or unavailable. "
                    "Grant Screen Recording to the app that launches Minion "
                    "(Terminal, iTerm, or Cursor) in System Settings → "
                    "Privacy & Security → Screen & System Audio Recording, "
                    "then quit and relaunch Minion."
                )

        return {
            "app_name": app_name,
            "window_title": window_title,
            "pid": pid,
        }
