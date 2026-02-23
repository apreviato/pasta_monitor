# PastaMonitor

Monitor de arquivos em tempo real com interface dark moderna, checkpoint e rollback por pasta.

---

## Funcionalidades

### Monitoramento
- Monitora múltiplas pastas simultaneamente, com recursão em subpastas
- Detecta arquivos **modificados**, **criados**, **deletados** e **movidos**
- Atualização em tempo real via watchdog
- Barra de busca para filtrar arquivos por nome
- Filtros rápidos por tipo de alteração na barra lateral

### Checkpoint & Rollback
- **Criar Checkpoint** — salva o estado atual de uma pasta (snapshot completo)
- A lista passa a exibir apenas alterações feitas *após* o checkpoint
- **Reverter arquivo** — restaura um único arquivo ao estado do checkpoint
- **Rollback Completo** — restaura todos os arquivos alterados da pasta
- **Cancelar Checkpoint** — descarta o snapshot sem alterar arquivos; retorna à lista completa

### Interface
- Tema escuro com efeito acrílico (Windows 10/11)
- Janela sem bordas, arrastável pelo cabeçalho (bloqueado quando maximizado)
- Duplo clique ou botão **Diff** abre visualizador lado a lado de diferenças
- Menu de contexto por arquivo (diff, reverter, copiar caminho)
- Menu de contexto por pasta (abrir no Explorador, checkpoint, rollback, remover)

### System Tray
- Fechar a janela minimiza para a bandeja do sistema
- Menu de tray com acesso rápido às pastas monitoradas
- Monitoramento continua ativo com a janela fechada

### Ignorar arquivos
Crie `.pastamonitor_ignore` na raiz da pasta monitorada — um padrão por linha (estilo fnmatch).

Padrões ignorados por padrão: `.git`, `__pycache__`, `node_modules`, `*.pyc`, arquivos de sistema, etc.

---

## Instalação

**Pré-requisitos:** Python 3.10+

```bash
pip install -r requirements.txt
```

**Dependências:**
| Pacote | Versão mínima | Uso |
|--------|--------------|-----|
| `watchdog` | 3.0.0 | Monitoramento do sistema de arquivos |
| `PyQt6` | 6.4.0 | Interface gráfica |

---

## Uso

```bash
python main.py
```

---

## Estrutura do Projeto

```
PastaMonitor/
├── main.py              # Ponto de entrada, bootstrap Qt
├── app.py               # Orquestrador (conecta monitor ↔ UI)
├── monitor.py           # FolderMonitor — watchdog + checkpoint/rollback
├── config.py            # ConfigManager (~/.pastamonitor/config.json)
├── ui/
│   ├── __init__.py
│   ├── main_window.py   # MainWindow, TopBar, ConfirmDialog
│   ├── sidebar_widget.py# Sidebar com filtros e lista de pastas
│   ├── changes_widget.py# Cards de alterações
│   ├── diff_view.py     # Painel de diff lado a lado
│   ├── styles.py        # Paleta de cores e stylesheet global
│   └── win_blur.py      # Efeito acrílico Win32
└── requirements.txt
```

---

## Configuração

As pastas monitoradas são salvas automaticamente em `~/.pastamonitor/config.json` e restauradas ao reabrir o app.
