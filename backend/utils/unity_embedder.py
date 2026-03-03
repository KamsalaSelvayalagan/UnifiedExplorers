"""
UnityEmbedder - Embed Unity EXE windows inside PyQt6 widgets

Usage:
    embedder = UnityEmbedder(container_widget, exe_path)
    embedder.start()
    # ... later ...
    embedder.stop()
"""

import os
import subprocess
import ctypes
import time
import threading
from ctypes import wintypes
from PyQt6.QtCore import QTimer, QObject, pyqtSignal


class UnityEmbedder(QObject):
    """Embed a Unity EXE window inside a PyQt6 QWidget"""
    
    # Signals
    started = pyqtSignal()
    stopped = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, container_widget, exe_path: str):
        """
        Initialize the Unity embedder
        
        Args:
            container_widget: PyQt6 QWidget to embed Unity into
            exe_path: Absolute path to the Unity .exe file
        """
        super().__init__()
        
        self.container_widget = container_widget
        self.exe_path = exe_path
        
        # Process and window management
        self.process = None
        self.unity_hwnd = None
        self.is_running = False
        
        # Windows API
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        
        # Resize timer for handling widget size changes
        self.resize_timer = QTimer()
        self.resize_timer.timeout.connect(self._on_resize_timer)
        self.resize_timer.setInterval(200)
    
    def start(self) -> bool:
        """
        Launch and embed the Unity EXE
        
        Returns:
            True if launch successful, False otherwise
        """
        if self.is_running:
            print("UnityEmbedder: Already running")
            return False
        
        if not os.path.exists(self.exe_path):
            error_msg = f"Unity EXE not found: {self.exe_path}"
            print(f"UnityEmbedder: {error_msg}")
            self.error.emit(error_msg)
            return False
        
        try:
            # Launch the Unity application
            self.process = subprocess.Popen(
                [self.exe_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.is_running = True
            print(f"UnityEmbedder: Launched process PID={self.process.pid}")
            
            # Find and embed window on background thread
            thread = threading.Thread(target=self._find_and_embed, daemon=True)
            thread.start()
            
            return True
            
        except Exception as e:
            error_msg = f"Failed to launch Unity EXE: {e}"
            print(f"UnityEmbedder: {error_msg}")
            self.error.emit(error_msg)
            self.is_running = False
            return False
    
    def stop(self):
        """Stop and cleanup the embedded Unity window"""
        if not self.is_running:
            return
        
        try:
            self.resize_timer.stop()
            
            # Terminate process
            if self.process is not None:
                if self.process.poll() is None:  # Still running
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                    print("UnityEmbedder: Process terminated")
                self.process = None
            
            self.unity_hwnd = None
            self.is_running = False
            self.stopped.emit()
            print("UnityEmbedder: Stopped")
            
        except Exception as e:
            print(f"UnityEmbedder: Error during stop: {e}")
    
    # ====== Internal Methods ======
    
    def _find_and_embed(self):
        """Background thread: find Unity window and embed it"""
        if self.process is None:
            return
        
        pid = self.process.pid
        print(f"UnityEmbedder: Searching for window (PID={pid})...")
        
        # Wait up to 15 seconds for window to appear
        hwnd = self._find_window_by_pid(pid, timeout=15.0)
        
        if hwnd:
            print(f"UnityEmbedder: Found window HWND={hwnd}")
            # Switch to main thread for UI operations
            QTimer.singleShot(0, lambda: self._do_embed(hwnd))
        else:
            error_msg = f"Could not find Unity window after 15 seconds"
            print(f"UnityEmbedder: {error_msg}")
            self.error.emit(error_msg)
            self.stop()
    
    def _find_window_by_pid(self, pid: int, timeout: float = 15.0) -> int:
        """Find window handle by process ID"""
        found_hwnd = [None]
        
        def enum_callback(hwnd, lParam):
            # Get process ID of this window
            process_id = wintypes.DWORD()
            self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
            
            # Check if visible window from our process
            if process_id.value == pid and self.user32.IsWindowVisible(hwnd):
                found_hwnd[0] = hwnd
                return False  # Stop enumerating
            return True  # Continue
        
        callback = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_long)(enum_callback)
        start_time = time.time()
        
        # Keep searching until window found or timeout
        while found_hwnd[0] is None and (time.time() - start_time) < timeout:
            self.user32.EnumWindows(callback, 0)
            if found_hwnd[0] is None:
                time.sleep(0.3)
        
        return found_hwnd[0]
    
    def _do_embed(self, hwnd: int):
        """Embed the window into container (MUST be called from main thread)"""
        try:
            if not hwnd or hwnd == 0:
                raise ValueError("Invalid window handle")
            
            print(f"UnityEmbedder: Starting embed process for HWND={hwnd}")
            
            # Get container native window handle - must have one
            container_hwnd = self.container_widget.winId()
            if not container_hwnd or container_hwnd == 0:
                raise ValueError(f"Container has invalid HWND: {container_hwnd}. Widget may not be shown yet.")
            
            container_hwnd = int(container_hwnd)
            rect = self.container_widget.geometry()
            
            print(f"UnityEmbedder: Container HWND={container_hwnd}, Size={rect.width()}x{rect.height()}")
            
            if rect.width() <= 0 or rect.height() <= 0:
                print(f"UnityEmbedder: Warning - Container has invalid size: {rect.width()}x{rect.height()}")
            
            # Remove window borders and style
            print("UnityEmbedder: Removing window borders...")
            self._remove_window_borders(hwnd)
            
            # Set as child of container
            print(f"UnityEmbedder: Setting parent (make {hwnd} child of {container_hwnd})...")
            result = self.user32.SetParent(hwnd, container_hwnd)
            if result == 0:
                print(f"UnityEmbedder: Warning - SetParent returned 0 (could mean failure or old parent was 0)")
            else:
                print(f"UnityEmbedder: SetParent returned {result}")
            
            # Resize to fit container
            print("UnityEmbedder: Resizing window...")
            self._resize_unity_window()
            
            # Show and activate
            print("UnityEmbedder: Showing window...")
            self.user32.ShowWindow(hwnd, 5)  # SW_SHOW
            time.sleep(0.1)
            
            # Try to get window into focus but don't force it
            try:
                self.user32.SetFocus(hwnd)
            except:
                pass
            
            self.unity_hwnd = hwnd
            
            # Start resize monitoring
            self.resize_timer.start()
            
            print(f"UnityEmbedder: Successfully embedded! Unity window {hwnd} is now child of container {container_hwnd}")
            self.started.emit()
            
        except Exception as e:
            error_msg = f"Failed to embed window: {e}"
            print(f"UnityEmbedder: ERROR - {error_msg}")
            import traceback
            traceback.print_exc()
            self.error.emit(error_msg)
            self.stop()
    
    def _remove_window_borders(self, hwnd: int):
        """Remove window borders, title bar, and styling"""
        try:
            print("UnityEmbedder: Modifying window styles...")
            
            # Get current window style
            GWL_STYLE = -16
            GWL_EXSTYLE = -20
            
            # Get current styles first
            current_style = self.user32.GetWindowLongW(hwnd, GWL_STYLE)
            current_exstyle = self.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            print(f"UnityEmbedder: Current style=0x{current_style:08x}, exstyle=0x{current_exstyle:08x}")
            
            # Window style flags
            WS_CAPTION = 0x00C00000       # Title bar
            WS_BORDER = 0x00800000        # Border
            WS_THICKFRAME = 0x00040000    # Resize border
            WS_CHILDWINDOW = 0x40000000   # Child window
            WS_VISIBLE = 0x10000000       # Visible
            WS_POPUP = 0x80000000         # Popup window
            WS_CHILD = 0x40000000         # Child
            
            # Set style: remove caption, border, thick frame; add child and visible
            new_style = (current_style & ~(WS_CAPTION | WS_BORDER | WS_THICKFRAME | WS_POPUP)) | WS_CHILD | WS_VISIBLE
            result = self.user32.SetWindowLongW(hwnd, GWL_STYLE, new_style)
            print(f"UnityEmbedder: SetWindowLongW(style) returned {result}")
            
            # Extended style flags
            WS_EX_CLIENTEDGE = 0x00000200
            WS_EX_WINDOWEDGE = 0x00000100
            WS_EX_DLGMODALFRAME = 0x00000001
            WS_EX_STATICEDGE = 0x00020000
            
            # Remove extended styles
            new_exstyle = current_exstyle & ~(WS_EX_CLIENTEDGE | WS_EX_WINDOWEDGE | WS_EX_DLGMODALFRAME | WS_EX_STATICEDGE)
            result = self.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_exstyle)
            print(f"UnityEmbedder: SetWindowLongW(exstyle) returned {result}")
            
            # Force window to redraw with new style
            self.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0020 | 0x0002)  # SWP_FRAMECHANGED | SWP_NOMOVE
            print("UnityEmbedder: Window styles modified successfully")
            
        except Exception as e:
            print(f"UnityEmbedder: Warning - Could not remove borders: {e}")
            import traceback
            traceback.print_exc()
    
    def _resize_unity_window(self):
        """Resize Unity window to fit container"""
        if not self.unity_hwnd:
            return
        
        try:
            rect = self.container_widget.geometry()
            
            SWP_NOZORDER = 0x0004
            SWP_ASYNCWINDOWPOS = 0x4000
            
            self.user32.SetWindowPos(
                self.unity_hwnd,
                0,  # hwndInsertAfter
                0, 0,  # x, y (relative to parent)
                rect.width(),
                rect.height(),
                SWP_NOZORDER | SWP_ASYNCWINDOWPOS
            )
        except Exception as e:
            print(f"UnityEmbedder: Warning - Resize failed: {e}")
    
    def _on_resize_timer(self):
        """Called periodically to handle container resize"""
        if not self.is_running or not self.unity_hwnd:
            return
        
        self._resize_unity_window()
