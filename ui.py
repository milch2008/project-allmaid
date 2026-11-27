"""Janela flutuante do Project Allmaid (CustomTkinter): balão creme com fallback em bolinha."""
import queue
import threading
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image, ImageDraw

from paths import PASTA_APP

COR_TRANSPARENTE = "#010203"
ASSETS = PASTA_APP / "assets"


def limpar_transparencia(img: Image.Image) -> Image.Image:
    """Remove pixels semi-transparentes que causam bordas escuras no Tkinter do Windows."""
    r, g, b, a = img.split()
    a = a.point(lambda p: 255 if p > 200 else 0)
    return Image.merge("RGBA", (r, g, b, a))


def desenhar_bolinha_padrao(expr: str) -> Image.Image:
    """Desenha um orbe/bolinha minimalista com olhinhos quando não há sprite na pasta assets."""
    img = Image.new("RGBA", (180, 230), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Sombra suave na base
    d.ellipse((45, 202, 135, 218), fill=(40, 35, 32, 255))

    # Corpo da bolinha (cor muda sutilmente conforme a expressão)
    if expr == "pensando":
        cor_corpo = (138, 123, 184, 255)   # Lavanda suave (modo análise)
    elif expr == "feliz":
        cor_corpo = (108, 168, 178, 255)   # Ciano suave
    else:
        cor_corpo = (125, 110, 99, 255)    # Marrom elegante combinando com o balão

    # Círculo principal com borda clara
    d.ellipse((25, 65, 155, 195), fill=cor_corpo, outline=(249, 243, 227, 255), width=4)

    # Olhinhos minimalistas dentro da bolinha
    if expr == "pensando":
        d.ellipse((62, 118, 74, 130), fill=(249, 243, 227, 255))
        d.ellipse((106, 118, 118, 130), fill=(249, 243, 227, 255))
    elif expr == "feliz":
        d.arc((58, 115, 78, 133), start=180, end=360, fill=(249, 243, 227, 255), width=4)
        d.arc((102, 115, 122, 133), start=180, end=360, fill=(249, 243, 227, 255), width=4)
    else:
        d.rounded_rectangle((64, 112, 74, 134), radius=4, fill=(249, 243, 227, 255))
        d.rounded_rectangle((106, 112, 116, 134), radius=4, fill=(249, 243, 227, 255))

    return img


class MaidWindow(ctk.CTk):
    def __init__(self, on_submit, avatar_altura: int = 230):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.on_submit = on_submit
        self.q: queue.Queue = queue.Queue()
        self._pendente = ""
        self._imgs: dict = {}
        self._altura = avatar_altura

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color=COR_TRANSPARENTE)
        self.attributes("-transparentcolor", COR_TRANSPARENTE)

        # Container principal alinhado pela base
        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.pack(padx=0, pady=0)

        # 1. Avatar da Allmaid (Esquerda)
        self.avatar = ctk.CTkLabel(topo, text="", fg_color="transparent")
        self.avatar.pack(side="left", anchor="s", padx=0, pady=0)
        self._set_avatar("neutra")

        # Container da direita (Triângulo + Balão + Status)
        lado_direito = ctk.CTkFrame(topo, fg_color="transparent")
        lado_direito.pack(side="left", anchor="center", padx=0, pady=(0, 12))

        # Container horizontal que une o triângulo na esquerda com o balão na direita
        conjunto_balao = ctk.CTkFrame(lado_direito, fg_color="transparent")
        conjunto_balao.pack()

        # 2. Balão creme com borda marrom responsivo
        self.balao_box = ctk.CTkFrame(
            conjunto_balao,
            fg_color="#f9f3e3",
            border_color="#7d6e63",
            border_width=3,
            corner_radius=24
        )
        self.balao_box.pack(side="left", padx=(19, 0))

        # Desenha o triângulo usando CTkCanvas nativo
        w_p, h_p = 22, 34
        self.ponta_canvas = ctk.CTkCanvas(
            conjunto_balao,
            width=w_p,
            height=h_p,
            bg=COR_TRANSPARENTE,
            highlightthickness=0,
            bd=0
        )
        self.ponta_canvas.create_polygon(
            w_p, 0,
            2, h_p // 2,
            w_p, h_p,
            fill="#f9f3e3",
            outline="#7d6e63",
            width=3
        )
        self.ponta_canvas.create_line(
            w_p, 3,
            w_p, h_p - 3,
            fill="#f9f3e3",
            width=5
        )
        self.ponta_canvas.place(x=0, rely=0.5, anchor="w")

        # Área de texto dentro do balão
        self.balao = ctk.CTkTextbox(
            self.balao_box,
            width=220,
            height=115,
            corner_radius=0,
            fg_color="transparent",
            text_color="#5a4a3f",
            border_width=0,
            wrap="word",
            font=("Comic Sans MS", 16)
        )
        self.balao.pack(padx=14, pady=(12, 4))
        self.balao.configure(state="disabled")
        # Linha divisória sutil dentro do balão
        divisor = ctk.CTkFrame(self.balao_box, height=2, fg_color="#d6cbb8")
        divisor.pack(fill="x", padx=14, pady=4)

        # Container inferior interno para digitar + botão enviar
        linha_input = ctk.CTkFrame(self.balao_box, fg_color="transparent")
        linha_input.pack(fill="x", padx=12, pady=(2, 12))

        self.entry = ctk.CTkEntry(
            linha_input,
            placeholder_text="Escreva aqui...",
            width=180,
            height=30,
            fg_color="#f2ead5",
            border_width=0,
            corner_radius=8,
            text_color="#5a4a3f",
            placeholder_text_color="#9e8e7e",
            font=("Comic Sans MS", 13)
        )
        self.entry.pack(side="left", padx=(0, 6))
        self.entry.bind("<Return>", self._enviar)
        self.entry.bind("<Button-1>", lambda e: self.focus_force())

        ctk.CTkButton(
            linha_input,
            text="➤",
            width=32,
            height=30,
            corner_radius=8,
            fg_color="#7d6e63",
            hover_color="#5a4a3f",
            text_color="#f9f3e3",
            font=("Segoe UI", 12, "bold"),
            command=self._enviar
        ).pack(side="left")

        # Status discreto (pensando...) logo abaixo do balão
        self.status_lbl = ctk.CTkLabel(
            lado_direito,
            text="",
            text_color="#7d6e63",
            fg_color="transparent",
            font=("Comic Sans MS", 11, "bold")
        )
        self.status_lbl.pack(pady=(2, 0))

        # Arrastar pela personagem ou pela moldura do balão / fechar com botão direito
        for w in (self.avatar, self.status_lbl, self.balao_box, self.ponta_canvas):
            w.bind("<ButtonPress-1>", self._ini_arrasto)
            w.bind("<B1-Motion>", self._arrastar)
            w.bind("<Button-3>", lambda e: self.destroy())

        self.update_idletasks()
        x = self.winfo_screenwidth() - self.winfo_reqwidth() - 20
        y = self.winfo_screenheight() - self.winfo_reqheight() - 40
        self.geometry(f"+{x}+{y}")
        self.after(200, self.entry.focus)
        self.after(50, self._poll)
        self.after(25, self._tick)

    # ------------------------------------------------ API thread-safe
    def say(self, texto: str):       self.q.put(("say", texto))
    def status(self, texto: str):    self.q.put(("status", texto))
    def expressao(self, nome: str):  self.q.put(("expr", nome))

    def confirm(self, texto: str) -> bool:
        ev, box = threading.Event(), {}
        self.q.put(("confirm", texto, ev, box))
        ev.wait()
        return box.get("ok", False)

    # ------------------------------------------------ internos
    def _carregar(self, caminho: Path, expr: str) -> ctk.CTkImage:
        if caminho.exists():
            img = Image.open(caminho).convert("RGBA")
            bbox = img.getbbox()
            if bbox:
                img = img.crop(bbox)
        else:
            img = desenhar_bolinha_padrao(expr)

        img = limpar_transparencia(img)
        r = self._altura / img.height
        return ctk.CTkImage(light_image=img, dark_image=img, size=(int(img.width * r), self._altura))

    def _set_avatar(self, expr: str):
        if expr not in self._imgs:
            caminho = ASSETS / f"maid_chan_{expr}.png"
            if not caminho.exists():
                caminho = ASSETS / "maid_chan.png"
            self._imgs[expr] = self._carregar(caminho, expr)
        self.avatar.configure(image=self._imgs[expr])

    def _limpar_balao(self):
        self._pendente = ""
        self.balao.configure(state="normal")
        self.balao.delete("1.0", "end")
        self.balao.configure(state="disabled")

    def _tick(self):
        if self._pendente:
            pedaco, self._pendente = self._pendente[:2], self._pendente[2:]
            self.balao.configure(state="normal")
            self.balao.insert("end", pedaco)
            self.balao.see("end")
            self.balao.configure(state="disabled")
        self.after(25, self._tick)

    def _poll(self):
        try:
            while True:
                item = self.q.get_nowait()
                tipo, *dados = item
                if tipo == "say":
                    texto_say, = dados
                    self._pendente += texto_say + "\n\n"
                elif tipo == "status":
                    texto_st, = dados
                    self.status_lbl.configure(text=texto_st)
                elif tipo == "expr":
                    nome_ex, = dados
                    self._set_avatar(nome_ex)
                elif tipo == "confirm":
                    texto, ev, box = dados
                    box["ok"] = messagebox.askyesno("Project Allmaid", texto, parent=self)
                    ev.set()
                elif tipo == "idle":
                    self.entry.configure(state="normal")
                    self.entry.focus()
        except queue.Empty:
            pass
        self.after(50, self._poll)

    def _enviar(self, _=None):
        texto = self.entry.get().strip()
        if not texto:
            return
        self.entry.delete(0, "end")
        self.entry.configure(state="disabled")
        self._limpar_balao()
        threading.Thread(target=self._worker, args=(texto,), daemon=True).start()

    def _worker(self, texto: str):
        try:
            self.on_submit(texto, self)
        except Exception as e:
            self.say(f"Erro inesperado: {e}")
        finally:
            self.q.put(("idle",))

    def _ini_arrasto(self, e):
        self._dx, self._dy = e.x_root - self.winfo_x(), e.y_root - self.winfo_y()

    def _arrastar(self, e):
        self.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")
