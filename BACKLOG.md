# Backlog

Práce, která se zrovna nedělá. Priorita je pořadí sekcí; uzavřený ticket se přesouvá do
`BACKLOG.done.md`. Ticket se bere přes `/feature:start BL-<n>`.

## Vysoká priorita

## Střední priorita

### BL-1 — Dashboard umí jen tmavý režim
**Oblast:** UX · plugins/claude-monitor/tools/claude_monitor.py

Paleta je natvrdo tmavá: `:root` drží jedenáct proměnných, ale v `PAGE` je
osmnáct různých hexů, takže sedm barev stojí mimo ně — `.card.idle`
(`#1d1b1a`, `#2b2927`, `#c9c2b8`), `.kpi.max .bar>i` (`#f2776b`),
`.pill.att` (`#191817`), `.att-row` (`#3a2c12`) — plus dvě `rgba()` ve stínu
pulzujícího rámečku. Stránka nezná `prefers-color-scheme` ani žádný přepínač.
Na světlém monitoru za dne se dashboard čte špatně a vedle světlého systému
svítí jako díra v obrazovce.

**Pozor:** samotné prohození `:root` nestačí, dokud těch sedm barev nejsou
proměnné; a volba režimu musí přežít reload, takže patří do `localStorage` —
sám stav v proměnné nestačí, jak to má fold KPI nebo výběr ticketu v backlogu
**Hotovo když:** dashboard respektuje `prefers-color-scheme`, přepínač v hlavičce
umí tmavý/světlý/podle systému, volba přežije reload a ve světlém režimu je
čitelná i oranžová karta `needs you`, plan tiles a stavové pilulky

### BL-2 — Z backlog boardu nejde ticket rovnou rozjet
**Oblast:** UX · plugins/claude-monitor/tools/claude_monitor.py

Board v dashboardu ticket jen ukazuje. Kdo ho chce vzít, musí přepnout do terminálu,
trefit správné okno se správným projektem a ručně opsat `/feature:start BL-<n>` —
číslo je na druhé obrazovce, takže právě u něj se dělá překlep. Čtení a spuštění
jsou přitom dva kroky téže věci.

Cesty, které stojí za prověření (rozhodnout jednu, ne postavit všechny):
1. **Tlačítko „copy“** v detailu ticketu — `navigator.clipboard.writeText()`, dashboard
   běží na `127.0.0.1`, což je secure context, takže API je dostupné. Nejlacinější,
   vložení do terminálu zůstává na člověku.
2. **Focus + vložení do běžící session** — `/api/focus` už umí najít okno i záložku
   terminálu podle tty (`focus()`, `tab_script()`), takže by stačilo doplnit keystroke.
   Jenže to chce Accessibility oprávnění a zapsat příkaz do session, která zrovna něco
   dělá, je rychlá cesta ke ztracenému promptu — bez kontroly `idle`/`needs you` ne.
3. **Nová session v rootu projektu** — `osascript`/`open` otevře terminál v `p.root`
   a spustí `claude "/feature:start BL-<n>"`. Do ničeho běžícího nezasahuje, ale je to
   první místo, kde dashboard spouští proces, ne jen čte soubory.
4. **Mimo UI** — `/feature:backlog-list` a detail ticketu můžou hotový příkaz rovnou
   vypsat jako text k označení; nic nového se nestaví a překlep zmizí taky.

**Pozor:** board se překresluje celým `innerHTML` při každém ticku, takže stav tlačítka
(„zkopírováno“) v DOMu nepřežije — musí ven vedle `blProj`/`blSel`, stejně jako výběr
ticketu. A jakmile se přidá POST, který něco spouští, přestává být server read-only:
`/api/focus` dnes umí jen přepnout okno, kdežto krok 2 a 3 znamenají spuštění příkazu
z HTTP requestu — i na loopbacku to chce vědomé rozhodnutí, ne přílepek k boardu.

**Hotovo když:** z otevřeného ticketu v boardu jde `/feature:start BL-<n>` rozjet jedním
úkonem bez ručního opisování ID, zvolená cesta je popsaná v README claude-monitoru
a nic se nezapíše do běžící session bez toho, aby to člověk viděl

## Nízká priorita

<!-- last-id: BL-2 -->
