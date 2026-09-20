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

## Nízká priorita

<!-- last-id: BL-10 -->
