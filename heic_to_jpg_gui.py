import os
import threading
from pathlib import Path
from tkinter import Tk, filedialog, messagebox, StringVar, BOTH, END, Text
from tkinter import ttk

from PIL import Image
import pillow_heif

pillow_heif.register_heif_opener()

QUALITY = 92


def open_folder(path: Path):
    try:
        os.startfile(str(path))
    except Exception:
        pass


def convert_one(src: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = im.convert("RGB")
        dst = out_dir / (src.stem + ".jpg")
        i = 1
        while dst.exists():
            dst = out_dir / f"{src.stem}_{i}.jpg"
            i += 1
        im.save(dst, "JPEG", quality=QUALITY, optimize=True)
    return dst


def collect_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        pp = Path(p)
        if pp.is_file() and pp.suffix.lower() in (".heic", ".heif"):
            files.append(pp)
        elif pp.is_dir():
            for f in pp.rglob("*"):
                if f.is_file() and f.suffix.lower() in (".heic", ".heif"):
                    files.append(f)
    return files


class App:
    def __init__(self, root: Tk):
        self.root = root
        root.title("HEIC / HEIF 批量转换 JPG")
        root.geometry("760x500")

        self.status = StringVar(value="请选择 HEIC/HEIF 文件或文件夹")
        self.out_dir: Path | None = None

        top = ttk.Frame(root, padding=10)
        top.pack(fill="x")

        self.btn_start = ttk.Button(top, text="选择并开始转换", command=self.start)
        self.btn_start.pack(side="left")

        self.btn_open = ttk.Button(top, text="打开输出文件夹", state="disabled", command=self.open_out)
        self.btn_open.pack(side="left", padx=10)

        ttk.Label(root, textvariable=self.status, padding=(10, 0)).pack(anchor="w")

        self.progress = ttk.Progressbar(root, mode="determinate")
        self.progress.pack(fill="x", padx=10, pady=(6, 0))

        # ✅ 注意：Text 是 tkinter 的，不是 ttk
        self.logbox = Text(root, height=18)
        self.logbox.pack(fill=BOTH, expand=True, padx=10, pady=10)

        self.footer = StringVar(value=f"JPG 质量：{QUALITY} | 成功：0 | 失败：0")
        ttk.Label(root, textvariable=self.footer, padding=(10, 0)).pack(anchor="w")

    def log(self, msg: str):
        self.logbox.insert(END, msg + "\n")
        self.logbox.see(END)

    def open_out(self):
        if self.out_dir:
            open_folder(self.out_dir)

    def start(self):
        use_files = messagebox.askyesno("选择方式", "【是】多选文件\n【否】选择文件夹（递归扫描子文件夹）")

        if use_files:
            selected = filedialog.askopenfilenames(
                title="选择 HEIC/HEIF 图片（可多选）",
                filetypes=[("HEIC/HEIF", "*.heic *.heif"), ("All files", "*.*")]
            )
            if not selected:
                return
            input_paths = list(selected)
            default_out = Path(input_paths[0]).parent / "JPG_Output"
        else:
            folder = filedialog.askdirectory(title="选择包含 HEIC 的文件夹（递归扫描）")
            if not folder:
                return
            input_paths = [folder]
            default_out = Path(folder) / "JPG_Output"

        out_dir_str = filedialog.askdirectory(title="选择输出文件夹（取消=默认 JPG_Output）")
        self.out_dir = Path(out_dir_str) if out_dir_str else default_out

        self.logbox.delete("1.0", END)
        self.status.set("正在扫描 HEIC/HEIF 文件…")
        self.root.update_idletasks()

        files = collect_files(input_paths)
        if not files:
            self.status.set("没有找到 HEIC/HEIF 文件。")
            messagebox.showinfo("提示", "没有找到 HEIC/HEIF 文件。")
            return

        self.progress["value"] = 0
        self.progress["maximum"] = len(files)
        self.btn_start.config(state="disabled")
        self.btn_open.config(state="disabled")

        self.log(f"找到 {len(files)} 个 HEIC/HEIF 文件")
        self.log(f"输出目录：{self.out_dir}")
        self.log("开始转换…\n")

        threading.Thread(target=self.run, args=(files,), daemon=True).start()

    def run(self, files: list[Path]):
        ok = 0
        fail = 0
        total = len(files)

        for i, f in enumerate(files, start=1):
            try:
                self.root.after(0, self.status.set, f"({i}/{total}) 转换中：{f.name}")
                convert_one(f, self.out_dir)  # type: ignore[arg-type]
                ok += 1
                self.root.after(0, self.log, f"✅ {f.name}")
            except Exception as e:
                fail += 1
                self.root.after(0, self.log, f"❌ {f.name} → {e}")

            self.root.after(0, self.progress.step, 1)
            self.root.after(0, self.footer.set, f"JPG 质量：{QUALITY} | 成功：{ok} | 失败：{fail}")

        def done():
            self.status.set("转换完成。")
            self.btn_start.config(state="normal")
            self.btn_open.config(state="normal")
            messagebox.showinfo("完成", f"转换完成！\n成功：{ok}\n失败：{fail}\n输出目录：\n{self.out_dir}")
            if self.out_dir:
                open_folder(self.out_dir)

        self.root.after(0, done)


def main():
    root = Tk()
    try:
        ttk.Style().theme_use("clam")
    except Exception:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        r = Tk()
        r.withdraw()
        messagebox.showerror("程序启动失败", f"{type(e).__name__}: {e}")
        raise
