# PastaMonitor

Monitor de arquivos com interface gráfica, checkpoint e rollback.

## Instalação

```bash
pip install watchdog pystray Pillow
```

## Uso

```bash
python main.py
```

## Funcionalidades

### Monitoramento
- Monitora uma pasta e todas as subpastas recursivamente
- Lista todos os arquivos modificados, criados, deletados ou movidos
- Atualização em tempo real

### Ignorar arquivos/pastas
Crie um arquivo `.pastamonitor_ignore` na raiz da pasta monitorada com um padrão por linha (estilo gitignore básico). Consulte `.pastamonitor_ignore.example` para exemplos.

Padrões padrão ignorados: `.git`, `__pycache__`, `node_modules`, `*.pyc`, etc.

### Checkpoint
1. Clique em **"Criar Checkpoint"** para salvar o estado atual da pasta
2. Continue trabalhando — a lista mostra apenas arquivos modificados **após** o checkpoint
3. **Rollback**: restaura todos os arquivos para o estado do checkpoint
4. **Cancelar Checkpoint**: descarta o backup, volta a mostrar todos os modificados desde o início

### System Tray
- Fechar a janela minimiza para a bandeja do sistema
- Menu da bandeja: Adicionar Pasta, lista de pastas monitoradas, Monitor, Fechar
- Clicar em uma pasta no menu abre a interface já com ela selecionada

## Estrutura do Projeto

```
PastaMonitor/
├── main.py      # Ponto de entrada
├── app.py       # Orquestrador da aplicação
├── monitor.py   # Lógica de monitoramento (watchdog)
├── config.py    # Configuração persistente (~/.pastamonitor/config.json)
├── ui.py        # Interface gráfica (tkinter)
├── tray.py      # Ícone na bandeja (pystray)
└── requirements.txt
```

## Configuração

As pastas monitoradas são salvas em `~/.pastamonitor/config.json` e restauradas automaticamente ao reabrir o app.
