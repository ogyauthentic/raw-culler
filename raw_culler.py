"""
RAW Photo Culler for Windows 10
================================
Fast RAW preview & culling tool
Supports: .raf, .arw, .cr3, .nef, .dng, .orf, .rw2, .pef

Install dependencies:
    pip install rawpy imageio Pillow

Keyboard shortcuts:
    → / ←     : Navigate photos
    K         : Keep (green)
    X / Del   : Reject (red)
    F         : Flag / Pick (blue)
    U         : Unflag / Clear status
    Ctrl+S    : Export all Keep photos
    Ctrl+O    : Open folder
"""

import os
import io
import shutil
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import rawpy
from PIL import Image, ImageTk

# ── Constants ──────────────────────────────────────────────────────────────────
SUPPORTED_EXT = ('.raf', '.arw', '.cr3', '.nef', '.dng', '.orf', '.rw2', '.pef')
THUMB_SIZE    = (200, 133)
PREVIEW_BG    = "#1a1a1a"

STATUS_COLOR = {
    "keep":   "#27ae60",
    "reject": "#e74c3c",
    "flag":   "#2980b9",
    None:     "#2c2c2c",
}
STATUS_LABEL = {
    "keep":   "✓ KEEP",
    "reject": "✗ REJECT",
    "flag":   "⚑ FLAGGED",
    None:     "",
}

# ── Helper: fast thumbnail extraction ─────────────────────────────────────────

def extract_thumbnail(raw_path: str) -> Image.Image | None:
    """Extract the camera-embedded JPEG thumbnail (very fast, no full RAW render)."""
    try:
        with rawpy.imread(raw_path) as raw:
            try:
                thumb = raw.extract_thumb()
            except rawpy.LibRawNoThumbnailError:
                return _render_fallback(raw)

            if thumb.format == rawpy.ThumbFormat.JPEG:
                img = Image.open(io.BytesIO(thumb.data))
                img = _fix_orientation(img)
                return img
            elif thumb.format == rawpy.ThumbFormat.BITMAP:
                return Image.fromarray(thumb.data)
    except Exception:
        pass
    return None


def _render_fallback(raw) -> Image.Image | None:
    """Render RAW at low quality as a fallback when no thumbnail is embedded."""
    try:
        rgb = raw.postprocess(
            use_camera_wb=True,
            half_size=True,
            no_auto_bright=False,
            output_bps=8,
        )
        return Image.fromarray(rgb)
    except Exception:
        return None


def _fix_orientation(img: Image.Image) -> Image.Image:
    """Rotate image according to EXIF orientation tag."""
    try:
        exif = img._getexif()
        if exif:
            orientation = exif.get(274)
            rotate_map = {3: 180, 6: 270, 8: 90}
            if orientation in rotate_map:
                img = img.rotate(rotate_map[orientation], expand=True)
    except Exception:
        pass
    return img


# ── Main Application ───────────────────────────────────────────────────────────

class RawCuller(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RAW Culler — Fast Photo Selection")
        self.geometry("1400x860")
        self.minsize(900, 600)
        self.configure(bg="#111111")

        # State
        self.folder_path   = None
        self.photo_list    = []          # list of str (full paths)
        self.current_index = 0
        self.statuses      = {}          # path → "keep"|"reject"|"flag"|None
        self.thumb_cache   = {}          # path → ImageTk.PhotoImage (small)
        self.preview_img   = None        # ImageTk reference for large preview
        self._loading      = False
        self._load_thread  = None

        self._build_ui()
        self._bind_keys()

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Top toolbar
        toolbar = tk.Frame(self, bg="#1e1e1e", height=52)
        toolbar.pack(fill="x", side="top")
        toolbar.pack_propagate(False)

        btn_cfg = dict(bg="#2e2e2e", fg="#e0e0e0", relief="flat",
                       activebackground="#404040", activeforeground="white",
                       font=("Segoe UI", 9), padx=12, pady=6, cursor="hand2")

        tk.Button(toolbar, text="📂  Open Folder",
                  command=self.open_folder, **btn_cfg).pack(side="left", padx=(10, 4), pady=8)
        tk.Button(toolbar, text="💾  Export Keep",
                  command=self.export_keep, **btn_cfg).pack(side="left", padx=4, pady=8)

        self.lbl_folder = tk.Label(toolbar, text="No folder selected",
                                   bg="#1e1e1e", fg="#777", font=("Segoe UI", 9))
        self.lbl_folder.pack(side="left", padx=16)

        # Stats: keep / reject / flag counters
        self.lbl_stats = tk.Label(toolbar, text="",
                                  bg="#1e1e1e", fg="#aaa", font=("Segoe UI", 9))
        self.lbl_stats.pack(side="right", padx=16)

        # ── Main splitter
        paned = tk.PanedWindow(self, orient="horizontal",
                               bg="#111", sashwidth=6, sashrelief="flat")
        paned.pack(fill="both", expand=True)

        # ── Left panel: thumbnail strip
        left = tk.Frame(paned, bg="#161616", width=230)
        left.pack_propagate(False)
        paned.add(left, minsize=180)

        tk.Label(left, text="PHOTOS", bg="#161616", fg="#555",
                 font=("Segoe UI", 8, "bold")).pack(pady=(10, 4))

        self.thumb_canvas = tk.Canvas(left, bg="#161616",
                                      highlightthickness=0, width=220)
        vsb = tk.Scrollbar(left, orient="vertical",
                           command=self.thumb_canvas.yview)
        self.thumb_canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.thumb_canvas.pack(side="left", fill="both", expand=True)

        self.thumb_frame = tk.Frame(self.thumb_canvas, bg="#161616")
        self.thumb_canvas.create_window((0, 0), window=self.thumb_frame, anchor="nw")
        self.thumb_frame.bind("<Configure>",
                              lambda e: self.thumb_canvas.configure(
                                  scrollregion=self.thumb_canvas.bbox("all")))
        self.thumb_canvas.bind("<MouseWheel>",
                               lambda e: self.thumb_canvas.yview_scroll(
                                   int(-1 * (e.delta / 120)), "units"))

        # ── Center panel: large preview
        center = tk.Frame(paned, bg=PREVIEW_BG)
        paned.add(center, minsize=400)

        self.canvas_preview = tk.Canvas(center, bg=PREVIEW_BG,
                                        highlightthickness=0)
        self.canvas_preview.pack(fill="both", expand=True)
        self.canvas_preview.bind("<Configure>", self._on_preview_resize)

        # Status overlay on top of preview
        self.lbl_status_overlay = tk.Label(center, text="",
                                           bg="#1a1a1a", fg="white",
                                           font=("Segoe UI", 13, "bold"),
                                           padx=14, pady=5)
        self.lbl_status_overlay.place(x=16, y=16)

        # Filename label at the bottom
        self.lbl_filename = tk.Label(center, text="",
                                     bg="#0d0d0d", fg="#ccc",
                                     font=("Segoe UI", 10))
        self.lbl_filename.place(relx=0.5, rely=1.0, anchor="s",
                                y=-4, x=0, relwidth=1.0)

        # ── Right panel: info & controls
        right = tk.Frame(paned, bg="#161616", width=220)
        right.pack_propagate(False)
        paned.add(right, minsize=180)

        self._build_right_panel(right)

        # ── Bottom status bar
        self.status_bar = tk.Label(self, text="Ready. Open a folder to get started.",
                                   bg="#0d0d0d", fg="#666",
                                   font=("Segoe UI", 8), anchor="w", padx=12)
        self.status_bar.pack(fill="x", side="bottom", ipady=4)

        # Progress bar (shown during thumbnail loading)
        self.progress = ttk.Progressbar(self, mode="indeterminate", length=400)

    def _build_right_panel(self, parent):
        pad = dict(padx=16, pady=6, fill="x")

        tk.Label(parent, text="CONTROLS", bg="#161616", fg="#555",
                 font=("Segoe UI", 8, "bold")).pack(pady=(16, 8))

        def btn(text, cmd, color, hover_color):
            b = tk.Button(parent, text=text, command=cmd,
                          bg=color, fg="white", relief="flat",
                          activebackground=hover_color, activeforeground="white",
                          font=("Segoe UI", 10, "bold"),
                          padx=10, pady=9, cursor="hand2", anchor="w")
            b.pack(**pad)

        btn("✓  Keep  (K)",   self.mark_keep,   "#1e6b3e", "#27ae60")
        btn("✗  Reject  (X)", self.mark_reject, "#7d2020", "#e74c3c")
        btn("⚑  Flag  (F)",   self.mark_flag,   "#1a4a72", "#2980b9")
        btn("○  Clear  (U)",  self.mark_clear,  "#333",    "#555")

        tk.Frame(parent, bg="#2a2a2a", height=1).pack(fill="x", padx=16, pady=14)

        tk.Label(parent, text="NAVIGATE", bg="#161616", fg="#555",
                 font=("Segoe UI", 8, "bold")).pack(pady=(0, 8))

        nav_frame = tk.Frame(parent, bg="#161616")
        nav_frame.pack(fill="x", padx=16)
        nav_cfg = dict(bg="#2e2e2e", fg="#ddd", relief="flat",
                       activebackground="#444", activeforeground="white",
                       font=("Segoe UI", 14), padx=16, pady=6, cursor="hand2")
        tk.Button(nav_frame, text="◀", command=self.prev_photo,
                  **nav_cfg).pack(side="left", expand=True, fill="x", padx=(0, 2))
        tk.Button(nav_frame, text="▶", command=self.next_photo,
                  **nav_cfg).pack(side="left", expand=True, fill="x", padx=(2, 0))

        tk.Frame(parent, bg="#2a2a2a", height=1).pack(fill="x", padx=16, pady=14)

        self.lbl_counter = tk.Label(parent, text="0 / 0",
                                    bg="#161616", fg="#aaa",
                                    font=("Segoe UI", 11, "bold"))
        self.lbl_counter.pack()

        self.lbl_cur_status = tk.Label(parent, text="",
                                       bg="#161616", fg="#888",
                                       font=("Segoe UI", 9))
        self.lbl_cur_status.pack(pady=4)

        tk.Frame(parent, bg="#2a2a2a", height=1).pack(fill="x", padx=16, pady=14)

        tk.Label(parent, text="SHORTCUTS", bg="#161616", fg="#555",
                 font=("Segoe UI", 8, "bold")).pack()

        shortcuts = [
            ("← →",    "Navigate"),
            ("K",       "Keep"),
            ("X / Del", "Reject"),
            ("F",       "Flag"),
            ("U",       "Clear"),
            ("Ctrl+O",  "Open folder"),
            ("Ctrl+S",  "Export Keep"),
        ]
        for key, desc in shortcuts:
            row = tk.Frame(parent, bg="#161616")
            row.pack(fill="x", padx=16, pady=1)
            tk.Label(row, text=key, bg="#252525", fg="#b0b0b0",
                     font=("Consolas", 8), width=8).pack(side="left")
            tk.Label(row, text=desc, bg="#161616", fg="#777",
                     font=("Segoe UI", 8)).pack(side="left", padx=6)

    # ── Key bindings ───────────────────────────────────────────────────────────

    def _bind_keys(self):
        self.bind("<Right>",     lambda e: self.next_photo())
        self.bind("<Left>",      lambda e: self.prev_photo())
        self.bind("k",           lambda e: self.mark_keep())
        self.bind("K",           lambda e: self.mark_keep())
        self.bind("x",           lambda e: self.mark_reject())
        self.bind("X",           lambda e: self.mark_reject())
        self.bind("<Delete>",    lambda e: self.mark_reject())
        self.bind("f",           lambda e: self.mark_flag())
        self.bind("F",           lambda e: self.mark_flag())
        self.bind("u",           lambda e: self.mark_clear())
        self.bind("U",           lambda e: self.mark_clear())
        self.bind("<Control-o>", lambda e: self.open_folder())
        self.bind("<Control-s>", lambda e: self.export_keep())

    # ── Folder & loading ───────────────────────────────────────────────────────

    def open_folder(self):
        folder = filedialog.askdirectory(title="Select RAW photo folder")
        if not folder:
            return
        self.folder_path = folder
        self.photo_list  = sorted(
            str(p) for p in Path(folder).iterdir()
            if p.suffix.lower() in SUPPORTED_EXT
        )
        self.statuses      = {p: None for p in self.photo_list}
        self.thumb_cache   = {}
        self.current_index = 0

        short = folder if len(folder) < 55 else "…" + folder[-52:]
        self.lbl_folder.config(text=short)
        self._set_status(f"Found {len(self.photo_list)} RAW files.")

        self._clear_thumbs()
        self._show_current()
        self._load_thumbs_async()

    def _clear_thumbs(self):
        for w in self.thumb_frame.winfo_children():
            w.destroy()

    def _load_thumbs_async(self):
        """Load thumbnails in a background thread to keep the UI responsive."""
        if self._load_thread and self._load_thread.is_alive():
            return
        self._load_thread = threading.Thread(target=self._load_all_thumbs, daemon=True)
        self._load_thread.start()

    def _load_all_thumbs(self):
        self.progress.pack(fill="x", side="bottom")
        self.progress.start(10)
        for i, path in enumerate(self.photo_list):
            img = extract_thumbnail(path)
            if img:
                img.thumbnail(THUMB_SIZE, Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.thumb_cache[path] = photo
            self.after(0, self._add_thumb_widget, i, path)
        self.progress.stop()
        self.progress.pack_forget()
        self.after(0, lambda: self._set_status("All thumbnails loaded."))

    def _add_thumb_widget(self, index: int, path: str):
        status = self.statuses.get(path)
        bg     = STATUS_COLOR.get(status, "#2c2c2c")
        photo  = self.thumb_cache.get(path)
        name   = os.path.basename(path)

        frame = tk.Frame(self.thumb_frame, bg=bg, cursor="hand2")
        frame.pack(fill="x", pady=2, padx=4)

        if photo:
            lbl_img = tk.Label(frame, image=photo, bg=bg)
            lbl_img.image = photo
            lbl_img.pack()
            lbl_img.bind("<Button-1>", lambda e, idx=index: self._jump_to(idx))

        lbl_name = tk.Label(frame, text=name[:22] + ("…" if len(name) > 22 else ""),
                            bg=bg, fg="#ccc", font=("Segoe UI", 7))
        lbl_name.pack()

        for w in (frame, lbl_name):
            w.bind("<Button-1>", lambda e, idx=index: self._jump_to(idx))

        # Store references for highlight updates
        frame._raw_index = index
        frame._path      = path

    def _jump_to(self, index: int):
        self.current_index = index
        self._show_current()

    # ── Preview ────────────────────────────────────────────────────────────────

    def _show_current(self):
        if not self.photo_list:
            return
        path = self.photo_list[self.current_index]
        self.lbl_counter.config(text=f"{self.current_index + 1} / {len(self.photo_list)}")
        self.lbl_filename.config(text=os.path.basename(path))
        self._update_status_labels(path)
        self._update_stats()
        self._scroll_thumb_into_view()
        self._load_preview(path)

    def _load_preview(self, path: str):
        self._set_status(f"Loading: {os.path.basename(path)} …")
        threading.Thread(
            target=lambda: self.after(0, self._display_preview,
                                      extract_thumbnail(path), path),
            daemon=True
        ).start()

    def _display_preview(self, img: Image.Image | None, path: str):
        if not img:
            self.canvas_preview.delete("all")
            self._set_status("Failed to load preview.")
            return

        w = self.canvas_preview.winfo_width()  or 800
        h = self.canvas_preview.winfo_height() or 600
        img.thumbnail((w - 10, h - 30), Image.LANCZOS)

        photo = ImageTk.PhotoImage(img)
        self.preview_img = photo  # Keep reference to prevent garbage collection

        self.canvas_preview.delete("all")
        self.canvas_preview.create_image(w // 2, (h - 24) // 2,
                                         anchor="center", image=photo)
        self._set_status(
            f"{os.path.basename(path)}  |  "
            f"{img.width}×{img.height}px  |  "
            f"{os.path.getsize(path) / 1_048_576:.1f} MB"
        )

    def _on_preview_resize(self, event):
        """Re-render preview when the window is resized."""
        if self.photo_list and not self._loading:
            self._show_current()

    # ── Culling actions ────────────────────────────────────────────────────────

    def _set_photo_status(self, status: str | None):
        if not self.photo_list:
            return
        path = self.photo_list[self.current_index]
        self.statuses[path] = status
        self._update_status_labels(path)
        self._update_thumb_color(path)
        self._update_stats()

    def mark_keep(self):
        self._set_photo_status("keep")
        self.next_photo()

    def mark_reject(self):
        self._set_photo_status("reject")
        self.next_photo()

    def mark_flag(self):
        self._set_photo_status("flag")
        self.next_photo()

    def mark_clear(self):
        self._set_photo_status(None)

    def _update_status_labels(self, path: str):
        status = self.statuses.get(path)
        color  = STATUS_COLOR.get(status, "#2c2c2c")
        label  = STATUS_LABEL.get(status, "")
        self.lbl_status_overlay.config(
            text=label,
            bg=color if status else "#1a1a1a",
            fg="white",
        )
        self.lbl_cur_status.config(text=label, fg=color if status else "#888")

    def _update_thumb_color(self, path: str):
        status = self.statuses.get(path)
        color  = STATUS_COLOR.get(status, "#2c2c2c")
        for w in self.thumb_frame.winfo_children():
            if getattr(w, "_path", None) == path:
                w.config(bg=color)
                for child in w.winfo_children():
                    child.config(bg=color)

    def _update_stats(self):
        counts = {"keep": 0, "reject": 0, "flag": 0, None: 0}
        for v in self.statuses.values():
            counts[v] = counts.get(v, 0) + 1
        self.lbl_stats.config(
            text=f"✓ {counts['keep']}  ✗ {counts['reject']}  ⚑ {counts['flag']}  ○ {counts[None]}"
        )

    def _scroll_thumb_into_view(self):
        n = len(self.photo_list)
        if n:
            self.thumb_canvas.yview_moveto(max(0, self.current_index / n - 0.1))

    # ── Navigation ─────────────────────────────────────────────────────────────

    def next_photo(self):
        if self.photo_list and self.current_index < len(self.photo_list) - 1:
            self.current_index += 1
            self._show_current()

    def prev_photo(self):
        if self.photo_list and self.current_index > 0:
            self.current_index -= 1
            self._show_current()

    # ── Export ─────────────────────────────────────────────────────────────────

    def export_keep(self):
        keep_paths = [p for p, s in self.statuses.items() if s == "keep"]
        if not keep_paths:
            messagebox.showinfo("Export", "No photos have been marked as Keep.")
            return

        dest = filedialog.askdirectory(title="Select export destination folder")
        if not dest:
            return

        done, errors = 0, []
        for path in keep_paths:
            try:
                shutil.copy2(path, os.path.join(dest, os.path.basename(path)))
                done += 1
            except Exception as e:
                errors.append(f"{os.path.basename(path)}: {e}")

        msg = f"{done} file(s) exported to:\n{dest}"
        if errors:
            msg += f"\n\n{len(errors)} failed:\n" + "\n".join(errors[:5])
        messagebox.showinfo("Export Complete", msg)

    # ── Utility ────────────────────────────────────────────────────────────────

    def _set_status(self, text: str):
        self.status_bar.config(text=text)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = RawCuller()
    app.mainloop()
