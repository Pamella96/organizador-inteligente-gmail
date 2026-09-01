"""Gerador de relatório PDF para o organizador de e-mails Gmail."""

import os
from datetime import datetime
from fpdf import FPDF

_FONTS_DIR = r"C:\Windows\Fonts"
_FONT_R  = os.path.join(_FONTS_DIR, "arial.ttf")
_FONT_B  = os.path.join(_FONTS_DIR, "arialbd.ttf")
_FONT_I  = os.path.join(_FONTS_DIR, "ariali.ttf")


def _s(text, maxlen=None):
    """Limpa chars que fontes TTF do sistema podem não ter (emojis raros)."""
    text = str(text or "")
    text = text.encode("utf-16", "surrogatepass").decode("utf-16")
    if maxlen:
        text = text[:maxlen] + ("..." if len(text) > maxlen else "")
    return text

# ---------------------------------------------------------------------------
# Paleta de cores
# ---------------------------------------------------------------------------

_CORES = {
    "TRABALHO":   (37,  99,  235),   # azul
    "FINANCEIRO": (220, 38,  38),    # vermelho
    "PESSOAL":    (22,  163, 74),    # verde
    "ACADEMICO":  (124, 58,  237),   # roxo
    "NEWSLETTER": (107, 114, 128),   # cinza
    "SPAM":       (107, 114, 128),   # cinza
    "?":          (107, 114, 128),
}

_BG_CORES = {
    "TRABALHO":   (239, 246, 255),
    "FINANCEIRO": (254, 242, 242),
    "PESSOAL":    (240, 253, 244),
    "ACADEMICO":  (245, 243, 255),
    "NEWSLETTER": (249, 250, 251),
    "SPAM":       (249, 250, 251),
    "?":          (249, 250, 251),
}

_URGENCIA_COR = {
    1: (156, 163, 175),
    2: (156, 163, 175),
    3: (251, 146, 60),
    4: (239, 68,  68),
    5: (185, 28,  28),
}

_URGENCIA_LABEL = {
    1: "Irrelevante",
    2: "Baixa",
    3: "Media",
    4: "Alta",
    5: "CRITICO",
}


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

class RelatorioPDF(FPDF):
    def __init__(self, titulo, data_str):
        super().__init__()
        self.titulo = titulo
        self.data_str = data_str
        self.add_font("Arial",  "",  _FONT_R)
        self.add_font("Arial",  "B", _FONT_B)
        self.add_font("ArialI", "",  _FONT_I)
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(18, 18, 18)

    def header(self):
        # Barra superior
        self.set_fill_color(15, 23, 42)
        self.rect(0, 0, 210, 14, "F")
        self.set_font("Arial", "B", 9)
        self.set_text_color(148, 163, 184)
        self.set_xy(0, 3)
        self.cell(0, 8, "ORGANIZADOR DE E-MAILS  |  Gmail + Gemini", align="C")
        self.ln(16)

    def footer(self):
        self.set_y(-12)
        self.set_font("Arial", "", 7)
        self.set_text_color(156, 163, 175)
        self.cell(0, 6, f"Gerado em {self.data_str}   |   Pag. {self.page_no()}", align="C")

    def titulo_secao(self, texto):
        self.ln(4)
        self.set_font("Arial", "B", 13)
        self.set_text_color(15, 23, 42)
        self.cell(0, 8, texto, ln=True)
        # linha decorativa
        self.set_draw_color(203, 213, 225)
        self.set_line_width(0.4)
        self.line(self.get_x(), self.get_y(), self.get_x() + 174, self.get_y())
        self.ln(4)

    def card_email(self, frm, assunto, resumo, categoria, urgencia):
        cor = _CORES.get(categoria, _CORES["?"])
        bg  = _BG_CORES.get(categoria, _BG_CORES["?"])
        ucor = _URGENCIA_COR.get(urgencia, _URGENCIA_COR[1])
        ulabel = _URGENCIA_LABEL.get(urgencia, "")

        x0 = self.get_x()
        y0 = self.get_y()
        w  = 174

        # Estima altura do card
        frm     = _s(frm, 80)
        assunto = _s(assunto, 100)
        resumo  = _s(resumo, 300)

        self.set_font("Arial", "", 8)
        resumo_linhas = self.multi_cell(w - 28, 4.5, resumo, dry_run=True, output="LINES")
        altura = 6 + 5 + 5 + len(resumo_linhas) * 4.5 + 5

        # Garante que cabe na página
        if y0 + altura > self.h - 22:
            self.add_page()
            y0 = self.get_y()

        # Fundo do card
        self.set_fill_color(*bg)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.3)
        self.rect(x0, y0, w, altura, "FD")

        # Borda lateral colorida
        self.set_fill_color(*cor)
        self.rect(x0, y0, 3, altura, "F")

        # Badge categoria
        self.set_xy(x0 + 6, y0 + 3)
        self.set_font("Arial", "B", 7)
        self.set_text_color(*cor)
        apagado = categoria in ("NEWSLETTER", "SPAM")
        cat_txt = f"[APAGADO]  {categoria}" if apagado else categoria
        self.cell(60, 5, cat_txt)

        # Badge urgência (direita)
        self.set_xy(x0 + w - 36, y0 + 3)
        self.set_fill_color(*ucor)
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", "B", 6.5)
        self.cell(30, 5, f"  {urgencia}/5  {ulabel}  ", align="C", fill=True)

        # De
        self.set_xy(x0 + 6, y0 + 9)
        self.set_font("Arial", "", 7.5)
        self.set_text_color(100, 116, 139)
        self.cell(w - 12, 5, f"De: {frm}")

        # Assunto
        self.set_xy(x0 + 6, y0 + 14)
        self.set_font("Arial", "B", 8.5)
        self.set_text_color(15, 23, 42)
        self.cell(w - 12, 5, assunto)

        # Resumo
        self.set_xy(x0 + 6, y0 + 19)
        self.set_font("Arial", "", 7.8)
        self.set_text_color(71, 85, 105)
        self.multi_cell(w - 12, 4.5, resumo)

        self.set_xy(x0, y0 + altura + 2)

    def resumo_table(self, contagem, urgentes):
        self.titulo_secao("RESUMO POR CATEGORIA")

        ordem = ["TRABALHO", "FINANCEIRO", "ACADEMICO", "PESSOAL", "NEWSLETTER", "SPAM"]
        total = sum(contagem.values())

        for cat in ordem:
            n = contagem.get(cat, 0)
            if not n:
                continue
            cor = _CORES.get(cat, _CORES["?"])
            pct = n / total * 100

            # Label
            self.set_font("Arial", "B", 9)
            self.set_text_color(*cor)
            self.cell(36, 7, cat)

            # Barra de progresso
            bx = self.get_x()
            by = self.get_y() + 2
            bar_w = 90
            self.set_fill_color(226, 232, 240)
            self.rect(bx, by, bar_w, 3.5, "F")
            self.set_fill_color(*cor)
            self.rect(bx, by, max(1, bar_w * pct / 100), 3.5, "F")

            # Contagem
            self.set_xy(bx + bar_w + 4, self.get_y())
            self.set_font("Arial", "", 9)
            self.set_text_color(51, 65, 85)
            sufixo = " > lixeira" if cat in ("NEWSLETTER", "SPAM") else ""
            self.cell(0, 7, f"{n} e-mails{sufixo}", ln=True)

        if urgentes:
            self.ln(4)
            self.titulo_secao("REQUER ATENCAO")
            for assunto, frm, resumo, urg in urgentes:
                assunto = _s(assunto, 80)
                frm     = _s(frm, 75)
                resumo  = _s(resumo, 200)
                ucor = _URGENCIA_COR.get(urg, _URGENCIA_COR[4])
                self.set_fill_color(*ucor)
                self.set_text_color(255, 255, 255)
                self.set_font("Arial", "B", 8)
                self.cell(10, 6, f" {urg}/5 ", fill=True)
                self.set_text_color(15, 23, 42)
                self.set_font("Arial", "B", 8.5)
                self.cell(0, 6, f"  {assunto[:75]}", ln=True)
                self.set_font("Arial", "", 7.5)
                self.set_text_color(100, 116, 139)
                self.cell(10)
                self.cell(0, 5, f"  {frm[:70]}", ln=True)
                if resumo:
                    self.cell(10)
                    self.set_text_color(71, 85, 105)
                    self.multi_cell(0, 4.5, f"  {resumo}")
                self.ln(2)


# ---------------------------------------------------------------------------
# Função pública
# ---------------------------------------------------------------------------

def gerar_pdf(emails_resultado, caminho_saida=None):
    """
    emails_resultado: list de (mid, categoria, urgencia, resumo, frm, assunto)
    caminho_saida: path do PDF (opcional, gera nome automático se None)
    """
    now = datetime.now()
    data_str = now.strftime("%d/%m/%Y %H:%M")
    nome_arquivo = caminho_saida or now.strftime("relatorio_%Y%m%d_%H%M%S.pdf")

    pdf = RelatorioPDF(titulo="Relatório de E-mails", data_str=data_str)
    pdf.add_page()

    # Cabeçalho do relatório
    pdf.set_font("Arial", "B", 20)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 10, "Relatório de E-mails", ln=True)
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(100, 116, 139)
    total = len(emails_resultado)
    pdf.cell(0, 6, f"{total} e-mails processados em {data_str}", ln=True)
    pdf.ln(4)

    contagem = {}
    urgentes = []

    pdf.titulo_secao("E-MAILS CLASSIFICADOS")

    for mid, categoria, urgencia, resumo, frm, assunto in emails_resultado:
        contagem[categoria] = contagem.get(categoria, 0) + 1
        pdf.card_email(frm, assunto, resumo or "(sem resumo)", categoria, urgencia)
        if urgencia >= 4:
            urgentes.append((assunto, frm, resumo, urgencia))

    pdf.add_page()
    pdf.resumo_table(contagem, urgentes)

    pdf.output(nome_arquivo)
    return nome_arquivo
