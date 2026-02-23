COLORS = {
    "bg_dark": "#111111",
    "bg_content": "#1A1A1A",
    "bg_card": "#242424",
    "bg_card_hover": "#2E2E2E",
    "bg_sidebar": "#161616",
    "bg_sidebar_btn": "transparent",
    "bg_sidebar_btn_hover": "#2A2A2A",
    "bg_sidebar_btn_active": "#2D2D2D",
    "bg_input": "#252525",
    "bg_topbar": "#1A1A1A",

    "accent": "#3498db",
    "accent_hover": "#2980b9",
    "danger": "#e74c3c",
    "danger_hover": "#c0392b",
    "success": "#2ecc71",
    "warning": "#f39c12",

    "text": "#E8E8E8",
    "text_secondary": "#999999",
    "text_muted": "#555555",
    "text_active": "#3498db",

    "border": "#2A2A2A",
    "border_card": "#2E2E2E",
    "border_sidebar": "#1E1E1E",

    "scrollbar": "#333333",
    "scrollbar_handle": "#444444",

    # Change type colours
    "modified": "#3498db",
    "created": "#2ecc71",
    "deleted": "#e74c3c",
    "moved": "#f39c12",
}

STYLESHEET = f"""
/* ─── Global ───────────────────────────────────── */
QWidget {{
    background-color: {COLORS['bg_content']};
    color: {COLORS['text']};
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    border: none;
}}

QMainWindow {{
    background-color: {COLORS['bg_dark']};
}}

/* ─── Scrollbar ─────────────────────────────────── */
QScrollBar:vertical {{
    background: {COLORS['bg_content']};
    width: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {COLORS['scrollbar_handle']};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #666;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

/* ─── Sidebar ────────────────────────────────────── */
#sidebar {{
    background-color: {COLORS['bg_sidebar']};
    border-right: 1px solid {COLORS['border_sidebar']};
}}

#sidebarTitle {{
    color: {COLORS['text']};
    font-size: 17px;
    font-weight: 700;
    letter-spacing: 0.5px;
    padding: 0 0 0 4px;
}}

#sidebarSubtitle {{
    color: {COLORS['text_muted']};
    font-size: 10px;
    letter-spacing: 1px;
    padding: 0 0 0 4px;
}}

QPushButton#navBtn {{
    background: {COLORS['bg_sidebar_btn']};
    color: {COLORS['text_secondary']};
    text-align: left;
    padding: 9px 10px;
    border-radius: 8px;
    font-size: 13px;
    border: none;
}}
QPushButton#navBtn:hover {{
    background: {COLORS['bg_sidebar_btn_hover']};
    color: {COLORS['text']};
}}
QPushButton#navBtn[active="true"] {{
    background: {COLORS['bg_sidebar_btn_active']};
    color: {COLORS['accent']};
    font-weight: 600;
}}

QPushButton#addFolderBtn {{
    background: transparent;
    color: {COLORS['text_muted']};
    text-align: left;
    padding: 7px 10px;
    border-radius: 8px;
    font-size: 12px;
    text-align: center;
    border: none;
}}
QPushButton#addFolderBtn:hover {{
    color: {COLORS['success']};
}}

QPushButton#removeFolderBtn {{
    background: transparent;
    color: {COLORS['text_muted']};
    border-radius: 5px;
    padding: 2px 5px;
    font-size: 11px;
    border: none;
    max-width: 20px;
    max-height: 20px;
}}
QPushButton#removeFolderBtn:hover {{
    background: rgba(231,76,60,0.15);
    color: {COLORS['danger']};
}}

#sectionLabel {{
    color: {COLORS['text_muted']};
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1.2px;
    padding: 2px 14px;
}}

#separator {{
    background-color: {COLORS['border']};
    max-height: 1px;
    margin: 4px 10px;
}}

/* ─── Top Bar ────────────────────────────────────── */
#topBar {{
    background-color: {COLORS['bg_topbar']};
    border-bottom: 1px solid {COLORS['border']};
}}

QPushButton#iconBtn {{
    background: transparent;
    color: {COLORS['text_secondary']};
    border-radius: 6px;
    padding: 6px 8px;
    font-size: 15px;
    border: none;
}}
QPushButton#iconBtn:hover {{
    background: #2E2E2E;
    color: {COLORS['text']};
}}
QPushButton#iconBtnClose {{
    background: transparent;
    color: {COLORS['text_secondary']};
    border-radius: 6px;
    padding: 6px 8px;
    font-size: 15px;
    border: none;
}}
QPushButton#iconBtnClose:hover {{
    background: {COLORS['accent']};
    color: {COLORS['text']};
}}

QPushButton#closeBtn {{
    background: transparent;
    color: {COLORS['text_secondary']};
    border-radius: 6px;
    padding: 6px 8px;
    font-size: 15px;
    border: none;
}}
QPushButton#closeBtn:hover {{
    background: {COLORS['danger']};
    color: white;
}}

/* ─── List Header ───────────────────────────────── */
#listTitle {{
    color: {COLORS['text']};
    font-size: 16px;
    font-weight: 700;
}}
#listCount {{
    color: {COLORS['text_secondary']};
    font-size: 13px;
}}

/* ─── Change Card ────────────────────────────────── */
QFrame#changeCard {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border_card']};
    border-radius: 12px;
}}
QFrame#changeCard:hover {{
    background-color: {COLORS['bg_card_hover']};
    border: 1px solid #383838;
}}

#fileName {{
    color: {COLORS['text']};
    font-size: 13px;
    font-weight: 600;
}}
#filePath {{
    color: {COLORS['text_secondary']};
    font-size: 11px;
}}
#fileFolder {{
    color: {COLORS['text_muted']};
    font-size: 10px;
}}
#fileTime {{
    color: {COLORS['text_muted']};
    font-size: 11px;
}}

/* ─── Type Badges ────────────────────────────────── */
#badgeModified {{
    background: rgba(52,152,219,0.15);
    color: {COLORS['modified']};
    border: 1px solid rgba(52,152,219,0.3);
    border-radius: 9px;
    padding: 1px 8px;
    font-size: 11px;
    font-weight: 700;
}}
#badgeCreated {{
    background: rgba(46,204,113,0.15);
    color: {COLORS['created']};
    border: 1px solid rgba(46,204,113,0.3);
    border-radius: 9px;
    padding: 1px 8px;
    font-size: 11px;
    font-weight: 700;
}}
#badgeDeleted {{
    background: rgba(231,76,60,0.15);
    color: {COLORS['deleted']};
    border: 1px solid rgba(231,76,60,0.3);
    border-radius: 9px;
    padding: 1px 8px;
    font-size: 11px;
    font-weight: 700;
}}
#badgeMoved {{
    background: rgba(243,156,18,0.15);
    color: {COLORS['moved']};
    border: 1px solid rgba(243,156,18,0.3);
    border-radius: 9px;
    padding: 1px 8px;
    font-size: 11px;
    font-weight: 700;
}}

QPushButton#cardActionBtn {{
    background: transparent;
    color: {COLORS['text_muted']};
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 12px;
    border: none;
}}
QPushButton#cardActionBtn:hover {{
    background: {COLORS['bg_card_hover']};
    color: {COLORS['text']};
}}
QPushButton#cardActionBtn[variant="danger"]:hover {{
    background: rgba(231,76,60,0.15);
    color: {COLORS['danger']};
}}

/* ─── Action Bar ─────────────────────────────────── */
#actionBar {{
    background-color: {COLORS['bg_topbar']};
    border-top: 1px solid {COLORS['border']};
}}

QPushButton#accentBtn {{
    background-color: {COLORS['accent']};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton#accentBtn:hover {{
    background-color: {COLORS['accent_hover']};
}}
QPushButton#accentBtn:disabled {{
    background-color: #2A2A2A;
    color: {COLORS['text_muted']};
}}

QPushButton#dangerBtn {{
    background-color: rgba(231,76,60,0.12);
    color: {COLORS['danger']};
    border: 1px solid rgba(231,76,60,0.25);
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton#dangerBtn:hover {{
    background-color: rgba(231,76,60,0.22);
    border-color: {COLORS['danger']};
}}
QPushButton#dangerBtn:disabled {{
    background-color: transparent;
    color: {COLORS['text_muted']};
    border-color: {COLORS['border']};
}}

QPushButton#neutralBtn {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border_card']};
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 13px;
}}
QPushButton#neutralBtn:hover {{
    background-color: {COLORS['bg_card_hover']};
    border-color: #444;
}}
QPushButton#neutralBtn:disabled {{
    color: {COLORS['text_muted']};
    border-color: {COLORS['border']};
}}


#checkpointLabel {{
    color: {COLORS['success']};
    border-radius: 8px;
    padding: 8px 0px;
    font-size: 13px;
    height: 28px;
}}


/* ─── Empty State ────────────────────────────────── */
#emptyIcon {{
    color: {COLORS['text_muted']};
    font-size: 42px;
}}
#emptyText {{
    color: {COLORS['text_muted']};
    font-size: 14px;
}}

/* ─── Diff Panel ─────────────────────────────────── */
#diffPanel {{
    background-color: #1A1A1A;
}}
#diffHeader {{
    background-color: #252526;
    border-bottom: 1px solid {COLORS['border']};
}}
#diffFileName {{
    color: {COLORS['text']};
    font-size: 14px;
    font-weight: 600;
}}
#diffInfoBar {{
    background-color: #2d2d2d;
    border-bottom: 1px solid {COLORS['border']};
}}
#diffInfoText {{
    color: {COLORS['text_secondary']};
    font-size: 11px;
    font-family: "Cascadia Code", Consolas, monospace;
}}
#diffStatusBar {{
    background-color: #007acc;
    color: white;
    font-size: 11px;
    padding: 3px 10px;
}}
#diffText {{
    background-color: #1e1e1e;
    color: #d4d4d4;
    font-family: "Cascadia Code", Consolas, monospace;
    font-size: 11px;
    border: none;
    selection-background-color: #264f78;
}}

/* ─── Dialog ─────────────────────────────────────── */
QLineEdit {{
    background-color: {COLORS['bg_input']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 7px;
    padding: 7px 12px;
    font-size: 13px;
}}
QLineEdit:focus {{
    border-color: {COLORS['accent']};
}}

/* ─── Status / misc ──────────────────────────────── */
#statusText {{
    color: {COLORS['text_muted']};
    font-size: 11px;
}}

/* ─── Context / tray menus ───────────────────────── */
QMenu {{
    background-color: #1C1C1C;
    border: 1px solid {COLORS['border_card']};
    border-radius: 8px;
    padding: 5px;
    color: {COLORS['text']};
    font-size: 12px;
}}
QMenu::item {{
    padding: 7px 18px 7px 12px;
    border-radius: 5px;
}}
QMenu::item:selected {{
    background: #2D2D2D;
    color: {COLORS['text']};
}}
QMenu::item:disabled {{
    color: {COLORS['text_muted']};
}}
QMenu::separator {{
    height: 1px;
    background: {COLORS['border']};
    margin: 4px 6px;
}}

/* ─── List header ────────────────────────────────── */
#listHeader {{
    background-color: {COLORS['bg_content']};
}}
"""
