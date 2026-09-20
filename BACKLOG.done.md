# Backlog — uzavřené

Tickety, které opustily `BACKLOG.md`. Nejnovější nahoře. Nic z toho není práce,
která by čekala na udělání.

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
