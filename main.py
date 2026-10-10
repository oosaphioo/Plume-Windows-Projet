import base64
import re
import sys
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QStandardPaths, QSettings, QSizeF, QMarginsF, QSize, QByteArray
from PySide6.QtGui import (QAction, QKeySequence, QFont, QTextCharFormat, QColor,
                          QTextCursor, QTextListFormat, QTextTableFormat, QTextImageFormat,
                          QImage, QPageSize, QPageLayout, QTextDocument, QIcon, QPixmap, QPainter, QPalette)
from PySide6.QtWidgets import (QApplication, QMainWindow, QTextEdit, QFileDialog,
    QMessageBox, QToolBar, QFontComboBox, QComboBox, QSpinBox, QColorDialog,
    QDockWidget, QListWidget, QInputDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QDialog, QDialogButtonBox, QToolButton, QSizePolicy, QGraphicsDropShadowEffect)
from PySide6.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
from storage import save_project, load_project, import_docx, export_docx, atomic_write

APP = 'Plume'

# Small local vector icons; no image downloads or icon font needed.
ICON_PATHS = {
    'feather': '<path d="M20 3c-7-2-15 3-14 11l4 3c8 0 12-7 10-14Z"/><path d="M3 21 16 8M7 17h5M11 13h5"/>',
    'folder': '<path d="M3 6h6l2 2h10v12H3Z"/>',
    'save': '<path d="M4 3h13l3 3v15H4Z"/><path d="M8 3v6h8V3M8 21v-8h8v8"/>',
    'export': '<path d="M12 3v12m-4-4 4 4 4-4M4 16v5h16v-5"/>',
    'moon': '<path d="M20 14A9 9 0 0 1 10 3a9 9 0 1 0 10 11Z"/>',
    'focus': '<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/>',
    'plus': '<path d="M12 5v14M5 12h14"/>',
    'up': '<path d="m6 14 6-6 6 6"/>',
    'down': '<path d="m6 10 6 6 6-6"/>',
    'left': '<path d="M4 5h16M4 10h10M4 15h16M4 20h10"/>',
    'center': '<path d="M4 5h16M7 10h10M4 15h16M7 20h10"/>',
    'right': '<path d="M4 5h16M10 10h10M4 15h16M10 20h10"/>',
    'justify': '<path d="M4 5h16M4 10h16M4 15h16M4 20h16"/>',
    'bullets': '<path d="M9 6h12M9 12h12M9 18h12"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/>',
    'numbers': '<path d="M10 6h11M10 12h11M10 18h11M3 4h2v5M3 13q3-3 3 0l-3 4h3"/>',
    'image': '<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8" cy="8" r="2"/><path d="m4 19 6-7 4 4 3-4 4 5"/>',
    'table': '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18M15 3v18"/>',
    'link': '<path d="m9 15 6-6M8 16l-2 2a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0M16 8l2-2a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0" transform="translate(1 0) scale(.9)"/>',
    'color': '<path d="m5 17 7-14 7 14M8 12h8M4 21h16"/>',
}

def vector_icon(name, color='#6856b3'):
    from PySide6.QtSvg import QSvgRenderer
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><g fill="none" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{ICON_PATHS[name]}</g></svg>'
    pix = QPixmap(48,48); pix.fill(Qt.transparent)
    painter = QPainter(pix); QSvgRenderer(QByteArray(svg.encode())).render(painter); painter.end()
    return QIcon(pix)



class Editor(QTextEdit):
    # Pasted images are embedded; documents never depend on an external image path.
    def insertFromMimeData(self, source):
        if source.hasImage():
            image = QImage(source.imageData())
            if not image.isNull():
                from PySide6.QtCore import QBuffer, QByteArray, QIODevice
                data = QByteArray(); buffer = QBuffer(data); buffer.open(QIODevice.WriteOnly)
                image.save(buffer, 'PNG')
                self.embed(bytes(data), min(image.width(), 560))
                return
        if source.hasHtml():
            # Keep text styles, disallow file/network references in pasted HTML.
            html = re.sub(r'<img\b[^>]*>', '', source.html(), flags=re.I)
            self.insertHtml(html)
            return
        super().insertFromMimeData(source)

    def embed(self, blob, width):
        fmt = QTextImageFormat()
        fmt.setName('data:image/png;base64,' + base64.b64encode(blob).decode())
        img = QImage.fromData(blob)
        if img.isNull(): raise ValueError('Cette image n’est pas lisible.')
        fmt.setWidth(width); fmt.setHeight(width * img.height() / img.width())
        self.textCursor().insertImage(fmt)


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1250, 850)
        self.settings = QSettings(APP, APP)
        self.path = None; self.dirty = False; self.switching = False; self.active = 0
        self.chapters = [{'title':'Document', 'html':'<p></p>'}]
        self.editor = Editor(); self.editor.setAcceptRichText(True)
        self.editor.setFont(QFont('Calibri', 12))
        self.editor.document().setDocumentMargin(54)
        self.editor.setObjectName('paper')
        self.editor.setLineWrapMode(QTextEdit.WidgetWidth)
        self.editor.setMaximumWidth(820)
        self.editor.setMinimumWidth(380)
        self.canvas = QWidget(); self.canvas.setObjectName('canvas')
        canvas_layout = QVBoxLayout(self.canvas); canvas_layout.setContentsMargins(28, 22, 28, 28); canvas_layout.setSpacing(16)
        self.breadcrumb = QLabel('DOCUMENT  /  Document'); self.breadcrumb.setObjectName('breadcrumb')
        canvas_layout.addWidget(self.breadcrumb)
        paper_row = QHBoxLayout(); paper_row.setSpacing(0); paper_row.addStretch(1); paper_row.addWidget(self.editor, 10); paper_row.addStretch(1)
        canvas_layout.addLayout(paper_row, 1)
        shadow = QGraphicsDropShadowEffect(self.editor); shadow.setBlurRadius(28); shadow.setOffset(0,6); shadow.setColor(QColor(30,25,55,24)); self.editor.setGraphicsEffect(shadow)
        self.setCentralWidget(self.canvas)
        self.editor.textChanged.connect(self.changed)
        self.editor.cursorPositionChanged.connect(self.sync_format)
        self.build_chapters(); self.build_toolbar(); self.build_menus(); self.apply_theme()
        self.refresh_chapters()
        self.timer = QTimer(self); self.timer.timeout.connect(self.autosave); self.timer.start(15000)
        self.recovery = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / 'recovery.plume'
        self.recovery.parent.mkdir(parents=True, exist_ok=True)
        self.update_status()
        QTimer.singleShot(0, self.offer_recovery)

    def action(self, label, fn, shortcut=None, check=False):
        a = QAction(label, self); a.setCheckable(check)
        if shortcut: a.setShortcut(QKeySequence(shortcut))
        a.triggered.connect(fn)
        return a

    def build_menus(self):
        file = self.menuBar().addMenu('Fichier')
        for label, fn, key in [('Nouveau', self.new, 'Ctrl+N'), ('Ouvrir…', self.open, 'Ctrl+O'), ('Enregistrer', self.save, 'Ctrl+S'), ('Enregistrer sous…', lambda:self.save(True), 'Ctrl+Shift+S'), ('Exporter en PDF…', self.pdf, None), ('Exporter en Word (.docx)…', self.word, None), ('Exporter en texte…', self.text_export, None), ('Aperçu avant impression', self.preview, None), ('Imprimer…', self.print_doc, 'Ctrl+P')]:
            file.addAction(self.action(label, fn, key))
        edit = self.menuBar().addMenu('Édition')
        for label, fn, key in [('Annuler', self.editor.undo, 'Ctrl+Z'), ('Rétablir', self.editor.redo, 'Ctrl+Y'), ('Couper', self.editor.cut, 'Ctrl+X'), ('Copier', self.editor.copy, 'Ctrl+C'), ('Coller', self.editor.paste, 'Ctrl+V'), ('Tout sélectionner', self.editor.selectAll, 'Ctrl+A'), ('Rechercher / remplacer…', self.find_dialog, 'Ctrl+F')]:
            edit.addAction(self.action(label, fn, key))
        view = self.menuBar().addMenu('Affichage')
        view.addAction(self.dock.toggleViewAction())
        self.concentration.setShortcut(QKeySequence('F11')); view.addAction(self.concentration)
        view.addAction(self.action('Thème clair / sombre', self.toggle_theme))
        view.addAction(self.action('Agrandir le texte', lambda:self.editor.zoomIn(1), 'Ctrl++'))
        view.addAction(self.action('Réduire le texte', lambda:self.editor.zoomOut(1), 'Ctrl+-'))
        help_menu = self.menuBar().addMenu('Aide')
        help_menu.addAction(self.action('À propos de Plume', lambda:QMessageBox.information(self, APP,
            'Plume 0.2 — Écrire à son rythme.\n\nEnregistrez en .plume pour conserver les chapitres et images.\nWord : import/export simplifiés, sans fidélité garantie.\nPDF et impression : pages A4, marges de 20 mm.\nÉditeur continu : utilisez l’aperçu pour voir les pages.\nPas encore de correcteur orthographique ni d’en-têtes/pieds de page.\nSauvegarde de secours locale toutes les 15 secondes.')))

    def tool_button(self, action, icon=None, primary=False, text=True):
        button = QToolButton(); button.setDefaultAction(action)
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon if text else Qt.ToolButtonIconOnly)
        button.setIconSize(QSize(18,18)); button.setFocusPolicy(Qt.NoFocus)
        if icon:
            action.setProperty('iconName',icon); action.setProperty('primaryIcon',primary)
            action.setIcon(vector_icon(icon, '#ffffff' if primary else '#6856b3'))
        if primary: button.setProperty('primary', True)
        if not text: button.setObjectName('iconButton'); button.setFixedSize(34,34)
        return button

    @staticmethod
    def divider():
        line = QWidget(); line.setObjectName('divider'); line.setFixedWidth(1); line.setFixedHeight(26)
        return line

    def build_toolbar(self):
        self.tools = QToolBar('Document'); self.tools.setObjectName('header'); self.tools.setMovable(False)
        self.addToolBar(self.tools)
        header = QWidget(); header.setObjectName('headerContent'); row = QHBoxLayout(header); row.setContentsMargins(18,6,18,6); row.setSpacing(10)
        logo = QLabel(); logo.setPixmap(vector_icon('feather').pixmap(30,30)); row.addWidget(logo)
        brand = QLabel('plume'); brand.setObjectName('brand'); row.addWidget(brand)
        tagline = QLabel('L’espace de vos mots'); tagline.setObjectName('muted'); row.addWidget(tagline)
        row.addStretch()
        for label, fn, icon in [('Ouvrir',self.open,'folder'), ('Enregistrer',self.save,'save'), ('Exporter PDF',self.pdf,'export')]:
            row.addWidget(self.tool_button(self.action(label,fn), icon, primary=label=='Enregistrer'))
        row.addWidget(self.divider())
        row.addWidget(self.tool_button(self.action('Changer de thème', self.toggle_theme), 'moon', text=False))
        self.concentration = self.action('Mode concentration', self.focus_mode, check=True)
        row.addWidget(self.tool_button(self.concentration, 'focus', text=False))
        header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred); self.tools.addWidget(header)
        self.addToolBarBreak()
        self.insert_tools = QToolBar('Mise en forme'); self.insert_tools.setObjectName('ribbon'); self.insert_tools.setMovable(False); self.addToolBar(self.insert_tools)
        ribbon = QWidget(); layout = QVBoxLayout(ribbon); layout.setContentsMargins(20,8,20,10); layout.setSpacing(6)
        first = QHBoxLayout(); first.setSpacing(8)
        caption = QLabel('TEXTE'); caption.setObjectName('sectionLabel'); first.addWidget(caption)
        self.styles = QComboBox(); self.styles.addItems(['Texte','Titre 1','Titre 2','Titre 3']); self.styles.setFixedWidth(110)
        self.styles.setAccessibleName('Style de paragraphe'); self.styles.activated.connect(self.heading); first.addWidget(self.styles)
        self.fonts = QFontComboBox(); self.fonts.setFixedWidth(185); self.fonts.setAccessibleName('Police')
        self.fonts.currentFontChanged.connect(lambda f:self.format(font=f.family())); first.addWidget(self.fonts)
        self.size = QSpinBox(); self.size.setRange(6,96); self.size.setValue(12); self.size.setFixedWidth(64); self.size.setAccessibleName('Taille de police')
        self.size.valueChanged.connect(lambda n:self.format(size=n)); first.addWidget(self.size)
        first.addWidget(self.divider())
        self.bold = self.action('B', lambda checked:self.format(bold=checked), 'Ctrl+B', True); self.bold.setToolTip('Gras · Ctrl+B')
        self.italic = self.action('I', lambda checked:self.format(italic=checked), 'Ctrl+I', True); self.italic.setToolTip('Italique · Ctrl+I')
        self.underline = self.action('U', lambda checked:self.format(underline=checked), 'Ctrl+U', True); self.underline.setToolTip('Souligné · Ctrl+U')
        for action, style in [(self.bold,'font-weight:700'),(self.italic,'font-style:italic'),(self.underline,'text-decoration:underline')]:
            button = self.tool_button(action); button.setFixedSize(34,34); button.setStyleSheet(style); first.addWidget(button)
        first.addWidget(self.tool_button(self.action('Couleur du texte',self.color),'color',text=False)); first.addStretch()
        second = QHBoxLayout(); second.setSpacing(8)
        caption = QLabel('PARAGRAPHE'); caption.setObjectName('sectionLabel'); second.addWidget(caption)
        for label, alignment, icon in [('Aligner à gauche',Qt.AlignLeft,'left'),('Centrer',Qt.AlignHCenter,'center'),('Aligner à droite',Qt.AlignRight,'right'),('Justifier',Qt.AlignJustify,'justify')]:
            second.addWidget(self.tool_button(self.action(label,lambda checked=False,a=alignment:self.editor.setAlignment(a)),icon,text=False))
        second.addWidget(self.divider())
        for label, fn, icon in [('Liste à puces',lambda:self.list_style(False),'bullets'),('Liste numérotée',lambda:self.list_style(True),'numbers')]:
            second.addWidget(self.tool_button(self.action(label,fn),icon,text=False))
        second.addWidget(self.divider())
        for label, fn, icon in [('Image',self.image,'image'),('Tableau',self.table,'table'),('Lien',self.link,'link')]:
            second.addWidget(self.tool_button(self.action(label,fn),icon))
        second.addStretch(); layout.addLayout(first); layout.addLayout(second)
        ribbon.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Preferred); self.insert_tools.addWidget(ribbon)

    def build_chapters(self):
        self.dock = QDockWidget('Chapitres', self); self.dock.setObjectName('sidebarDock')
        self.dock.setFeatures(QDockWidget.NoDockWidgetFeatures); self.dock.setTitleBarWidget(QWidget())
        self.dock.setMinimumWidth(240); self.dock.setMaximumWidth(290)
        box = QWidget(); box.setObjectName('sidebar'); layout = QVBoxLayout(box); layout.setContentsMargins(18,24,18,18); layout.setSpacing(14)
        label = QLabel('Votre document'); label.setObjectName('sidebarTitle'); layout.addWidget(label)
        caption = QLabel('CHAPITRES'); caption.setObjectName('sectionLabel'); layout.addWidget(caption)
        self.chapter_list = QListWidget(); self.chapter_list.setObjectName('chapters'); self.chapter_list.currentRowChanged.connect(self.switch_chapter); layout.addWidget(self.chapter_list,1)
        button = QPushButton('Ajouter un chapitre'); button.setIcon(vector_icon('plus')); button.setProperty('soft',True); button.clicked.connect(self.add_chapter); layout.addWidget(button)
        controls = QHBoxLayout(); controls.setSpacing(6)
        rename = QPushButton('Renommer'); rename.clicked.connect(self.rename_chapter); controls.addWidget(rename,1)
        for label, delta, icon in [('Monter le chapitre',-1,'up'),('Descendre le chapitre',1,'down')]:
            button = self.tool_button(self.action(label,lambda checked=False,d=delta:self.move_chapter(d)),icon,text=False); controls.addWidget(button)
        layout.addLayout(controls)
        delete = QPushButton('Supprimer le chapitre'); delete.setObjectName('deleteChapter'); delete.clicked.connect(self.delete_chapter); layout.addWidget(delete)
        hint = QLabel('À votre rythme.\n\nCtrl+S  Enregistrer\nCtrl+F  Rechercher\nF11       Concentration'); hint.setObjectName('sidebarHint'); layout.addWidget(hint)
        self.dock.setWidget(box); self.addDockWidget(Qt.LeftDockWidgetArea,self.dock)

    def format(self, **kw):
        fmt = QTextCharFormat()
        if 'font' in kw: fmt.setFontFamilies([kw['font']])
        if 'size' in kw: fmt.setFontPointSize(kw['size'])
        if 'bold' in kw: fmt.setFontWeight(QFont.Bold if kw['bold'] else QFont.Normal)
        if 'italic' in kw: fmt.setFontItalic(kw['italic'])
        if 'underline' in kw: fmt.setFontUnderline(kw['underline'])
        self.editor.mergeCurrentCharFormat(fmt); self.editor.setFocus()

    def sync_format(self):
        fmt = self.editor.currentCharFormat()
        for control in [self.bold, self.italic, self.underline, self.fonts, self.size, self.styles]: control.blockSignals(True)
        self.bold.setChecked(fmt.fontWeight() >= QFont.Bold); self.italic.setChecked(fmt.fontItalic()); self.underline.setChecked(fmt.fontUnderline())
        self.fonts.setCurrentFont(fmt.font()); self.size.setValue(round(fmt.fontPointSize() or 12))
        self.styles.setCurrentIndex(min(3, self.editor.textCursor().blockFormat().headingLevel()))
        for control in [self.bold, self.italic, self.underline, self.fonts, self.size, self.styles]: control.blockSignals(False)

    def heading(self, level):
        cursor = self.editor.textCursor(); bf = cursor.blockFormat(); bf.setHeadingLevel(level); cursor.setBlockFormat(bf)
        self.format(size=[12, 26, 20, 16][level], bold=bool(level))

    def color(self):
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            fmt = QTextCharFormat(); fmt.setForeground(color); self.editor.mergeCurrentCharFormat(fmt)

    def list_style(self, numbered):
        fmt = QTextListFormat(); fmt.setStyle(QTextListFormat.ListDecimal if numbered else QTextListFormat.ListDisc)
        self.editor.textCursor().createList(fmt)

    def image(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Ajouter une image', '', 'Images (*.png *.jpg *.jpeg *.webp *.bmp)')
        if path: self.run_io(lambda:self.editor.embed(Path(path).read_bytes(), 420))

    def table(self):
        rows, ok = QInputDialog.getInt(self, 'Tableau', 'Nombre de lignes', 3, 1, 100)
        if not ok: return
        cols, ok = QInputDialog.getInt(self, 'Tableau', 'Nombre de colonnes', 3, 1, 12)
        if ok:
            fmt = QTextTableFormat(); fmt.setBorder(1); fmt.setCellPadding(7); fmt.setCellSpacing(0)
            self.editor.textCursor().insertTable(rows, cols, fmt)

    def link(self):
        url, ok = QInputDialog.getText(self, 'Lien', 'Adresse https://…')
        if ok and url.startswith(('https://', 'http://', 'mailto:')):
            cursor = self.editor.textCursor(); fmt = QTextCharFormat(); fmt.setAnchor(True); fmt.setAnchorHref(url); fmt.setFontUnderline(True); fmt.setForeground(QColor('#6455b5'))
            if cursor.hasSelection(): cursor.mergeCharFormat(fmt)
            else: cursor.insertText(url, fmt)
            self.editor.setCurrentCharFormat(QTextCharFormat())

    def capture(self):
        self.chapters[self.active]['html'] = self.editor.toHtml()
        return {'version':1, 'chapters':self.chapters}

    def changed(self):
        if self.switching: return
        self.dirty = True; self.update_status()

    def update_status(self):
        current = len(re.findall(r'\S+', self.editor.toPlainText()))
        total = current
        for i, chapter in enumerate(self.chapters):
            if i != self.active:
                doc = QTextDocument(); doc.setHtml(chapter['html']); total += len(re.findall(r'\S+', doc.toPlainText()))
        self.breadcrumb.setText('DOCUMENT  /  ' + self.chapters[self.active]['title'])
        self.statusBar().showMessage(f'{current} mots dans ce chapitre · {total} mots au total · ' + ('Modifications non enregistrées' if self.dirty else 'Document enregistré'))
        self.setWindowTitle(f'{"● " if self.dirty else ""}{self.path.name if self.path else "Sans titre"} — Plume')

    def refresh_chapters(self):
        self.chapter_list.blockSignals(True); self.chapter_list.clear()
        self.chapter_list.addItems([c['title'] for c in self.chapters]); self.chapter_list.setCurrentRow(self.active); self.chapter_list.blockSignals(False)

    def switch_chapter(self, index):
        if index < 0 or index == self.active: return
        self.capture(); self.active = index; self.load_active()

    def load_active(self):
        self.switching = True; self.editor.setHtml(self.chapters[self.active]['html']); self.switching = False; self.update_status()

    def add_chapter(self):
        title, ok = QInputDialog.getText(self, 'Chapitre', 'Titre du chapitre')
        if ok and title.strip():
            self.capture(); self.chapters.append({'title':title.strip(), 'html':'<p></p>'}); self.active = len(self.chapters)-1
            self.refresh_chapters(); self.load_active(); self.changed()

    def rename_chapter(self):
        title, ok = QInputDialog.getText(self, 'Renommer', 'Titre', text=self.chapters[self.active]['title'])
        if ok and title.strip(): self.chapters[self.active]['title'] = title.strip(); self.refresh_chapters(); self.changed()

    def move_chapter(self, delta):
        target = self.active + delta
        if 0 <= target < len(self.chapters):
            self.capture(); self.chapters[self.active], self.chapters[target] = self.chapters[target], self.chapters[self.active]
            self.active = target; self.refresh_chapters(); self.changed()

    def delete_chapter(self):
        if len(self.chapters) == 1: return
        if QMessageBox.question(self, 'Supprimer', 'Supprimer ce chapitre et tout son contenu ?') == QMessageBox.Yes:
            self.chapters.pop(self.active); self.active = min(self.active, len(self.chapters)-1); self.refresh_chapters(); self.load_active(); self.changed()

    def confirm_leave(self):
        if not self.dirty: return True
        answer = QMessageBox.question(self, 'Enregistrer ?', 'Enregistrer les modifications avant de continuer ?', QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        return self.save() if answer == QMessageBox.Save else answer == QMessageBox.Discard

    def new(self):
        if self.confirm_leave():
            self.chapters = [{'title':'Document', 'html':'<p></p>'}]; self.active = 0; self.path = None; self.dirty = False
            self.refresh_chapters(); self.load_active(); self.recovery.unlink(missing_ok=True)

    def run_io(self, fn):
        try: return fn()
        except Exception as exc:
            QMessageBox.warning(self, 'Opération impossible', str(exc)); return None

    def open(self):
        if not self.confirm_leave(): return
        path, _ = QFileDialog.getOpenFileName(self, 'Ouvrir', '', 'Documents (*.plume *.docx *.txt)')
        if not path: return
        def perform():
            p = Path(path)
            if p.suffix.lower() == '.plume': chapters = load_project(p)['chapters']
            elif p.suffix.lower() == '.docx':
                QMessageBox.information(self, 'Import Word', 'Import simplifié : les éléments avancés (en-têtes, commentaires, formes, mise en page complexe) ne sont pas conservés. Le fichier Word original reste intact.')
                chapters = [{'title':p.stem, 'html':import_docx(p)}]
            else:
                from html import escape
                chapters = [{'title':p.stem, 'html':'<p>' + escape(p.read_text(encoding='utf-8-sig')).replace('\n','<br>') + '</p>'}]
            self.chapters = chapters; self.active = 0; self.path = p if p.suffix.lower() == '.plume' else None
            self.dirty = self.path is None; self.refresh_chapters(); self.load_active()
        self.run_io(perform)

    def save(self, save_as=False):
        path = self.path
        if save_as or not path:
            name, _ = QFileDialog.getSaveFileName(self, 'Enregistrer le document', str(path or 'Mon document.plume'), 'Document Plume (*.plume)')
            if not name: return False
            path = Path(name if name.lower().endswith('.plume') else name + '.plume')
        try:
            save_project(path, self.capture()); self.path = path; self.dirty = False
            self.recovery.unlink(missing_ok=True); self.update_status(); return True
        except Exception as exc: QMessageBox.warning(self, 'Enregistrement impossible', str(exc)); return False

    def autosave(self):
        if not self.dirty: return
        try:
            save_project(self.recovery, self.capture())
            self.statusBar().showMessage('Copie de secours actualisée · Ctrl+S pour enregistrer votre fichier', 3500)
        except Exception as exc:
            self.statusBar().showMessage(f'Copie de secours impossible : {exc}')

    def offer_recovery(self):
        if self.recovery.exists():
            if QMessageBox.question(self, 'Reprendre votre écriture', 'Une copie de secours a été trouvée. Voulez-vous la restaurer ?') == QMessageBox.Yes:
                data = self.run_io(lambda:load_project(self.recovery))
                if data:
                    self.chapters = data['chapters']; self.active = 0; self.dirty = True; self.refresh_chapters(); self.load_active()
            else: self.recovery.unlink(missing_ok=True)

    def combined_document(self):
        self.capture(); result = QTextDocument(); result.setDefaultFont(QFont('Calibri',12))
        cursor = QTextCursor(result)
        for index, chapter in enumerate(self.chapters):
            if index:
                cursor.insertBlock(); bf = cursor.blockFormat(); bf.setPageBreakPolicy(bf.PageBreak_AlwaysBefore); cursor.setBlockFormat(bf)
            cursor.insertHtml(chapter['html'])
        return result

    def printer(self, pdf=None):
        p = QPrinter(QPrinter.HighResolution)
        p.setPageLayout(QPageLayout(QPageSize(QPageSize.A4), QPageLayout.Portrait, QMarginsF(20,20,20,20)))
        if pdf: p.setOutputFormat(QPrinter.PdfFormat); p.setOutputFileName(str(pdf))
        return p

    def pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Exporter en PDF', 'Mon document.pdf', 'PDF (*.pdf)')
        if path:
            path = path if path.lower().endswith('.pdf') else path + '.pdf'
            def perform():
                self.combined_document().print_(self.printer(path))
                if not Path(path).exists() or Path(path).stat().st_size == 0: raise OSError('Le PDF n’a pas pu être créé.')
                self.statusBar().showMessage('PDF exporté', 4000)
            self.run_io(perform)

    def word(self):
        QMessageBox.information(self, 'Export Word', 'Export simplifié : texte, styles usuels, images et tableaux simples. Les chapitres deviennent un seul document. Conservez aussi votre fichier .plume.')
        path, _ = QFileDialog.getSaveFileName(self, 'Exporter en Word', 'Mon document.docx', 'Word (*.docx)')
        if path: self.run_io(lambda:export_docx(self.combined_document().toHtml(), path if path.lower().endswith('.docx') else path+'.docx'))

    def text_export(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Exporter en texte', 'Mon document.txt', 'Texte (*.txt)')
        if path: self.run_io(lambda:atomic_write(path if path.lower().endswith('.txt') else path+'.txt', self.combined_document().toPlainText()))

    def preview(self):
        dialog = QPrintPreviewDialog(self.printer(), self)
        doc = self.combined_document(); dialog.paintRequested.connect(doc.print_); dialog.exec()

    def print_doc(self):
        printer = self.printer()
        if QPrintDialog(printer, self).exec() == QDialog.Accepted: self.combined_document().print_(printer)

    def find_dialog(self):
        dialog = QDialog(self); dialog.setWindowTitle('Rechercher dans le chapitre')
        layout = QVBoxLayout(dialog); query = QLineEdit(); query.setPlaceholderText('Texte recherché'); replacement = QLineEdit(); replacement.setPlaceholderText('Remplacer par')
        layout.addWidget(query); layout.addWidget(replacement)
        def find():
            if not query.text(): return False
            if self.editor.find(query.text()): return True
            cursor = self.editor.textCursor(); cursor.movePosition(QTextCursor.Start); self.editor.setTextCursor(cursor)
            found = self.editor.find(query.text())
            if not found: QMessageBox.information(dialog, 'Recherche', 'Aucun résultat dans ce chapitre.')
            return found
        def replace():
            cursor = self.editor.textCursor()
            if query.text() and cursor.selectedText() == query.text(): cursor.insertText(replacement.text())
            find()
        def replace_all():
            if not query.text(): return
            doc = self.editor.document(); cursor = QTextCursor(doc); cursor.beginEditBlock(); start = 0; count = 0
            while True:
                found = doc.find(query.text(), start)
                if found.isNull(): break
                found.insertText(replacement.text()); start = found.position(); count += 1
            cursor.endEditBlock(); QMessageBox.information(dialog, 'Remplacement', f'{count} remplacement(s).')
        for label, fn in [('Suivant', find), ('Remplacer', replace), ('Tout remplacer', replace_all)]:
            button = QPushButton(label); button.clicked.connect(fn); layout.addWidget(button)
        dialog.exec()

    def focus_mode(self, checked):
        self.dock.setVisible(not checked); self.tools.setVisible(not checked); self.insert_tools.setVisible(not checked); self.menuBar().setVisible(not checked)

    def toggle_theme(self):
        self.settings.setValue('dark', not self.settings.value('dark', False, type=bool)); self.apply_theme()
        QTimer.singleShot(0, self.editor.viewport().repaint)

    def apply_theme(self):
        dark = self.settings.value('dark', False, type=bool)
        bg, panel, text, muted, border, hover, soft = ('#171923','#20232f','#eeeef5','#a8adbf','#35394a','#303549','#343050') if dark else ('#ebeef4','#ffffff','#2a3042','#6d768c','#e1e5ef','#f1f3f9','#efebfa')
        for action in self.findChildren(QAction):
            name = action.property('iconName')
            if name: action.setIcon(vector_icon(name, '#ffffff' if action.property('primaryIcon') else '#ac9ae7' if dark else '#6856b3'))
        # Explicit Qt palette fixes native popup text on Windows, including fonts.
        palette = QPalette()
        for role, value in [(QPalette.Window,panel),(QPalette.WindowText,text),(QPalette.Base,panel),(QPalette.AlternateBase,hover),(QPalette.Text,text),(QPalette.Button,panel),(QPalette.ButtonText,text),(QPalette.Highlight,'#7161bb'),(QPalette.HighlightedText,'#ffffff'),(QPalette.ToolTipBase,panel),(QPalette.ToolTipText,text)]:
            palette.setColor(role,QColor(value))
        self.setPalette(palette)
        for combo in (self.styles,self.fonts):
            combo.setPalette(palette); combo.view().setPalette(palette)
        self.setStyleSheet(f'''QMainWindow,QDialog{{background:{bg};color:{text}}}
            QWidget{{font-family:"Segoe UI","Inter","DejaVu Sans";font-size:13px;color:{text}}}
            QMenuBar{{background:{panel};padding:5px 14px;border-bottom:1px solid {border}}}
            QMenuBar::item{{padding:5px 10px;border-radius:5px}} QMenuBar::item:selected{{background:{hover}}}
            QMenu{{background:{panel};color:{text};border:1px solid {border};padding:6px}}
            QMenu::item{{padding:8px 22px}} QMenu::item:selected{{background:{soft}}}
            QToolBar{{background:{panel};border:0;spacing:0;padding:0}}
            QToolBar#header{{border-bottom:1px solid {border}}} QToolBar#ribbon{{border-bottom:1px solid {border}}}
            QWidget#headerContent{{background:{panel}}} QWidget#canvas{{background:{bg}}}
            QLabel#brand{{font-size:25px;font-weight:700;letter-spacing:-1px;padding-right:12px}}
            QLabel#muted{{color:{muted};font-size:12px}}
            QLabel#sectionLabel{{font-size:10px;letter-spacing:1px;color:{muted};font-weight:600;padding-right:7px}}
            QLabel#breadcrumb{{font-size:11px;color:{muted};padding-left:4px}}
            QWidget#divider{{background:{border};margin:0 0}}
            QToolButton,QPushButton{{background:transparent;border:1px solid transparent;border-radius:7px;padding:7px 10px;color:{text};min-height:18px}}
            QToolButton#iconButton{{padding:5px}}
            QToolButton:hover,QPushButton:hover{{background:{hover};border-color:{border}}}
            QToolButton:pressed,QPushButton:pressed,QToolButton:checked{{background:{soft};border-color:#b7a9de}}
            QToolButton[primary="true"]{{background:#7161bb;color:white;padding:8px 14px}}
            QToolButton[primary="true"]:hover{{background:#6251aa}}
            QPushButton[soft="true"]{{background:{soft};border:1px solid {border};padding:9px;color:{text}}}
            QPushButton#deleteChapter{{color:{muted};font-size:11px;text-align:left;padding-left:4px}}
            QComboBox,QSpinBox,QLineEdit{{background:{panel};color:{text};border:1px solid {border};border-radius:6px;padding:6px;min-height:20px;selection-background-color:#7161bb;selection-color:white}}
            QComboBox:focus,QSpinBox:focus,QLineEdit:focus{{border-color:#9583d1}}
            QComboBox QAbstractItemView{{background:{panel};color:{text};border:1px solid {border};selection-background-color:#7161bb;selection-color:white;outline:0}}
            QComboBox QAbstractItemView::item{{padding:5px;min-height:24px}}
            QWidget#sidebar{{background:{panel};border-right:1px solid {border}}}
            QLabel#sidebarTitle{{font-size:17px;font-weight:600;padding-bottom:6px}}
            QLabel#sidebarHint{{font-size:11px;color:{muted};padding-top:18px;border-top:1px solid {border}}}
            QListWidget#chapters{{background:transparent;border:0;outline:0;font-size:13px}}
            QListWidget#chapters::item{{padding:12px 10px;margin-bottom:5px;border-radius:7px;color:{text}}}
            QListWidget#chapters::item:selected{{background:{soft};color:{text};font-weight:600}}
            QListWidget#chapters::item:hover{{background:{hover}}}
            QTextEdit#paper{{font-family:"Calibri","DejaVu Sans";font-size:12pt;background:#ffffff;color:#252938;border:1px solid {'#c6c9d6' if dark else '#dfe3ed'};border-radius:2px;selection-background-color:#ded5ef;selection-color:#222}}
            QStatusBar{{background:{panel};color:{muted};font-size:11px;border-top:1px solid {border};padding:5px 14px}} QStatusBar::item{{border:0}}
            QScrollBar:vertical{{background:transparent;width:10px;margin:4px 1px}} QScrollBar::handle:vertical{{background:{border};border-radius:4px;min-height:30px}}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0}} QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{{background:none}}
            QToolTip{{background:{panel};color:{text};border:1px solid {border};padding:6px}}
        ''')

    def closeEvent(self, event):
        if self.confirm_leave(): self.recovery.unlink(missing_ok=True); event.accept()
        else: event.ignore()


def main():
    app = QApplication(sys.argv); app.setApplicationName(APP); app.setOrganizationName(APP)
    app.setStyle('Fusion')
    if '--smoke-test' in sys.argv:
        QStandardPaths.setTestModeEnabled(True)
        app.setApplicationName('Plume-smoke-test')
        window = Window(); window.show()
        QTimer.singleShot(150, app.quit)
        return app.exec()
    # One instance prevents different sessions overwriting the same recovery file.
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    socket = QLocalSocket(); socket.connectToServer('Plume-local-editor')
    if socket.waitForConnected(200):
        QMessageBox.information(None, APP, 'Plume est déjà ouvert. Retrouvez sa fenêtre dans la barre des tâches.'); return 0
    QLocalServer.removeServer('Plume-local-editor'); server = QLocalServer(); server.listen('Plume-local-editor')
    window = Window(); window.show()
    return app.exec()

if __name__ == '__main__': sys.exit(main())
