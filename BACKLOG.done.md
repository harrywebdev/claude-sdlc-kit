# Backlog — uzavřené

Tickety, které opustily `BACKLOG.md`. Nejnovější nahoře. Nic z toho není práce,
která by čekala na udělání.

### BL-3 — Refresh stránky vždy zahodí rozdělaný pohled
**Closed:** 2026-09-20 · done · main
**Oblast:** UX · plugins/claude-monitor/tools/claude_monitor.py

Který view je vykreslený, drží obyčejná proměnná `let view = "sessions"` a vybraný projekt
s tiketem `let blProj = null, blSel = null`. V celém souboru není ani jeden zápis do
`localStorage` nebo do URL, takže každé F5 — i to, které si vynutí sám dashboard po restartu
serveru — hodí člověka zpátky na sessions a v backlogu na první projekt a první tiket.
Kdo board používá, musí po každém refreshi znovu naklikat tab, projekt a tiket, který právě četl.

Stejnou vadu mají i ostatní volby v hlavičce: `ivIdx` (interval auto-refreshe) a fold KPI
se resetují úplně stejně.

**Pozor:** stav nesmí skončit v DOMu — board i grid se překreslují celým `innerHTML` při
každém ticku. Patří vedle `blProj`/`blSel` a do `localStorage`, ať to funguje stejně jako
přepínač režimu v BL-1. Obnovený `blProj` navíc nemusí odpovídat žádnému otevřenému
projektu (session mezitím skončila) a `blSel` žádnému existujícímu tiketu — `board()` už
dnes umí spadnout zpátky na první položku, ale ten fallback musí zabrat i pro hodnotu
načtenou z úložiště, ne jen pro `null`.

**Hotovo když:** po refreshi zůstane otevřený stejný view, a v backlogu i stejný projekt
a tiket; neplatný uložený projekt nebo tiket dashboard tiše přepne na první existující místo
toho, aby zůstal prázdný

**Řešení:** dvojice pomocníků `load()`/`save()` nad `localStorage` pod prefixem
`claude-monitor:`; přes ně jdou `view`, `ivIdx`, `kpisAll` a `blProj`/`blSel`. Projekt
a ticket se zapisují přes `setProj()`/`setSel()`, takže korekci, kterou dnes dělá `board()`
u neplatné hodnoty, uloží taky — načtený mrtvý projekt nebo zavřený ticket tichounce spadne
na první existující. Načtené hodnoty se validují (`view` jen sessions/backlog, `ivIdx` proti
délce `INTERVALS`), zápis i čtení jsou v `try`/`catch`, aby zakázané úložiště stránku
nezastavilo. Boot volá `setView(view)` místo `tick()`, protože markup se rodí se sessions.

### BL-2 — Z backlog boardu nejde ticket rovnou rozjet
**Closed:** 2026-09-20 · done · feature/BL-2-start-from-board
**Oblast:** UX · plugins/claude-monitor/tools/claude_monitor.py
**Branch:** feature/BL-2-start-from-board

Board v dashboardu ticket jen ukazuje. Kdo ho chce vzít, musí přepnout do terminálu,
trefit správné okno se správným projektem a ručně opsat `/feature:start BL-<n>` —
číslo je na druhé obrazovce, takže právě u něj se dělá překlep. Čtení a spuštění
jsou přitom dva kroky téže věci.

Z cest, které ticket zvažoval, padlo rozhodnutí na **tlačítko „copy“** v detailu ticketu —
`navigator.clipboard.writeText()`, dashboard běží na `127.0.0.1`, což je secure context,
takže API je dostupné. Vložení do terminálu zůstává na člověku.

Zahozené cesty a proč: **vložení příkazu do běžící session** přes keystroke chce
Accessibility oprávnění a je to rychlá cesta ke ztracenému promptu; **spuštění nové session**
z `osascript` by z dashboardu udělalo první místo, kde server spouští proces, ne jen čte
soubory — a monitor má zůstat read-only.

**Pozor:** board se překresluje celým `innerHTML` při každém ticku, takže stav tlačítka
(„zkopírováno“) v DOMu nepřežije — musí ven vedle `blProj`/`blSel`, stejně jako výběr
ticketu.

**Hotovo když:** z otevřeného ticketu v boardu jde příkaz `/feature:start BL-<n>` dostat do
schránky jedním klikem bez ručního opisování ID, zvolená cesta je popsaná v README
claude-monitoru a nic se nezapíše do běžící session bez toho, aby to člověk viděl
