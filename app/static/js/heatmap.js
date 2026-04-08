/**
 * renderHeatmap — GitHub-style contribution heatmap
 * @param {string} containerId  - ID of the DOM element to render into
 * @param {object} data         - { "YYYY-MM-DD": minutes, ... }
 */
function renderHeatmap(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';

    const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const endDate = new Date(today);
    const startDate = new Date(today);
    startDate.setDate(startDate.getDate() - 364);

    // Align grid start to the nearest past Sunday
    const gridStart = new Date(startDate);
    gridStart.setDate(gridStart.getDate() - gridStart.getDay());

    function toISO(d) {
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${y}-${m}-${day}`;
    }

    function cellColor(mins) {
        if (!mins || mins === 0) return '#161b22';
        if (mins <= 30)  return '#0e4429';
        if (mins <= 60)  return '#006d32';
        if (mins <= 120) return '#26a641';
        return '#39d353';
    }

    // Build week columns
    const weeks = [];
    const cur = new Date(gridStart);
    while (cur <= endDate) {
        const week = [];
        for (let d = 0; d < 7; d++) {
            week.push(new Date(cur));
            cur.setDate(cur.getDate() + 1);
        }
        weeks.push(week);
    }

    // Outer wrapper
    const outer = document.createElement('div');
    outer.style.cssText = 'display:inline-flex; flex-direction:column; gap:4px; max-width:100%;';

    // Month label row
    const monthRow = document.createElement('div');
    monthRow.style.cssText = 'display:flex; gap:3px;';
    let lastMonth = -1;

    weeks.forEach(week => {
        const labelDiv = document.createElement('div');
        labelDiv.style.cssText = 'width:11px; flex-shrink:0; font-size:9px; color:#6b7280; overflow:visible; white-space:nowrap;';
        const firstInRange = week.find(d => d >= startDate && d <= endDate);
        if (firstInRange) {
            const m = firstInRange.getMonth();
            if (m !== lastMonth) {
                labelDiv.textContent = MONTHS[m];
                lastMonth = m;
            }
        }
        monthRow.appendChild(labelDiv);
    });

    // Grid row
    const gridRow = document.createElement('div');
    gridRow.style.cssText = 'display:flex; gap:3px;';

    weeks.forEach(week => {
        const col = document.createElement('div');
        col.style.cssText = 'display:flex; flex-direction:column; gap:3px; flex-shrink:0;';

        week.forEach(day => {
            const cell = document.createElement('div');
            const inRange = day >= startDate && day <= endDate;
            const dateStr = toISO(day);
            const raw = inRange ? data[dateStr] : undefined;
            let mins = 0;
            let activityOnly = false;
            if (typeof raw === 'number') {
                mins = raw;
                activityOnly = false;
            } else if (raw && typeof raw === 'object') {
                mins = raw.m != null ? raw.m : 0;
                activityOnly = !!raw.a;
            }
            const levelMins = activityOnly && mins === 0 ? 1 : mins;

            cell.style.cssText = [
                'width:11px', 'height:11px', 'border-radius:2px', 'flex-shrink:0',
                `background:${inRange ? cellColor(levelMins) : 'transparent'}`,
                inRange ? 'cursor:pointer' : ''
            ].join(';');

            if (inRange) {
                const h = Math.floor(mins / 60);
                const m = mins % 60;
                let timeStr;
                if (activityOnly && mins === 0) {
                    timeStr = 'Activity (check-in / done)';
                } else if (mins > 0) {
                    timeStr = h > 0 ? `${h}h ${m}m` : `${m}m`;
                } else {
                    timeStr = 'No activity';
                }
                cell.title = `${dateStr}: ${timeStr}`;
            }

            col.appendChild(cell);
        });

        gridRow.appendChild(col);
    });

    outer.appendChild(monthRow);
    outer.appendChild(gridRow);
    container.appendChild(outer);
}
