/* global d3 */

const DATA_URL = new URL(
  "../../data/processed/api_football/formation_matchup_summary.json",
  window.location.href,
).href;

const DEFAULT_COLORS = {
  missingCellFill: "#f4f4f6",
  axisText: "#1f2937",
  tickText: "#374151",
  bg: "#ffffff",
  gridStroke: "#e5e7eb",
};

function uniqueSorted(arr) {
  return Array.from(new Set(arr)).sort((a, b) => String(a).localeCompare(String(b)));
}

function tooltipHtml(d) {
  const fmtRate = (v) => (typeof v === "number" ? `${v.toFixed(3)}%` : String(v ?? ""));
  const isLowSample = Number(d.matches) < 3;
  return `
    <div class="ttTitle">Formation matchup</div>
    <div class="ttRow"><span class="ttKey">Team formation</span><span class="ttVal">${escapeHtml(d.team_formation)}</span></div>
    <div class="ttRow"><span class="ttKey">Opponent formation</span><span class="ttVal">${escapeHtml(d.opponent_formation)}</span></div>
    <div class="ttDivider"></div>
    <div class="ttRow"><span class="ttKey">Matches</span><span class="ttVal">${d.matches}</span></div>
    ${
      isLowSample
        ? `<div class="ttRow"><span class="ttKey lowSample">Low sample</span><span class="ttVal">${d.matches} matches</span></div>`
        : ""
    }
    <div class="ttRow"><span class="ttKey">Wins</span><span class="ttVal">${d.wins}</span></div>
    <div class="ttRow"><span class="ttKey">Draws</span><span class="ttVal">${d.draws}</span></div>
    <div class="ttRow"><span class="ttKey">Losses</span><span class="ttVal">${d.losses}</span></div>
    <div class="ttRow"><span class="ttKey">Win rate</span><span class="ttVal">${fmtRate(d.win_rate)}</span></div>
    <div class="ttDivider"></div>
    <div class="ttRow"><span class="ttKey">Avg goals for</span><span class="ttVal">${d.average_goals_for.toFixed(3)}</span></div>
    <div class="ttRow"><span class="ttKey">Avg goals against</span><span class="ttVal">${d.average_goals_against.toFixed(3)}</span></div>
  `;
}

function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function createTooltip() {
  const existing = d3.select("body").select("div.tooltip");
  if (!existing.empty()) return existing;

  return d3
    .select("body")
    .append("div")
    .attr("class", "tooltip")
    .style("opacity", 0);
}

function computeDomainStats(data, domainKey) {
  // domainKey is either "team_formation" (rows) or "opponent_formation" (columns).
  const map = new Map();
  for (const d of data) {
    const key = d[domainKey];
    if (!map.has(key)) {
      map.set(key, { totalMatches: 0, weightedWinRateSum: 0 });
    }
    const s = map.get(key);
    const matches = Number(d.matches) || 0;
    s.totalMatches += matches;
    s.weightedWinRateSum += (Number(d.win_rate) || 0) * matches;
  }
  const stats = new Map();
  for (const [key, s] of map.entries()) {
    stats.set(key, {
      totalMatches: s.totalMatches,
      avgWinRate: s.totalMatches > 0 ? s.weightedWinRateSum / s.totalMatches : 0,
    });
  }
  return stats;
}

function sortDomains(domains, stats, sortMode) {
  const arr = Array.from(domains);
  if (sortMode === "matches") {
    arr.sort((a, b) => {
      const sb = stats.get(b) ?? { totalMatches: 0 };
      const sa = stats.get(a) ?? { totalMatches: 0 };
      const diff = sb.totalMatches - sa.totalMatches;
      if (diff !== 0) return diff;
      return String(a).localeCompare(String(b));
    });
    return arr;
  }

  if (sortMode === "winrate") {
    arr.sort((a, b) => {
      const sb = stats.get(b) ?? { avgWinRate: 0 };
      const sa = stats.get(a) ?? { avgWinRate: 0 };
      const diff = sb.avgWinRate - sa.avgWinRate;
      if (diff !== 0) return diff;
      return String(a).localeCompare(String(b));
    });
    return arr;
  }

  // Default: formation name.
  arr.sort((a, b) => String(a).localeCompare(String(b)));
  return arr;
}

function createWinRateColorScale() {
  // Diverging palette:
  // low -> purple/red, mid -> neutral gray, high -> yellow/green.
  const purple = "#7e22ce";
  const neutral = "#f3f4f6";
  const yellow = "#facc15";
  const green = "#22c55e";

  return d3
    .scaleLinear()
    .domain([0, 50, 75, 100])
    .range([purple, neutral, yellow, green])
    .clamp(true);
}

function createOpacityScale({ minMatches, maxMatches }) {
  const minScale = Math.max(1, Number(minMatches) || 0);
  const maxScale = Math.max(minScale, Number(maxMatches) || 1);
  if (maxScale === minScale) {
    return () => 1;
  }
  const scale = d3
    .scaleLinear()
    .domain([minScale, maxScale])
    .range([0.25, 1])
    .clamp(true);
  return (v) => scale(Number(v) || 0);
}

function renderHeatmap(data, container, options = {}) {
  const width = options.width ?? 1100;
  const height = options.height ?? 700;
  const margin = options.margin ?? { top: 80, right: 30, bottom: 120, left: 130 };

  const rawTeamDomainsAll = uniqueSorted(data.map((d) => d.team_formation));
  const rawOpponentDomainsAll = uniqueSorted(data.map((d) => d.opponent_formation));

  // Stats for sorting by match count and average win rate.
  const teamStats = computeDomainStats(data, "team_formation");
  const opponentStats = computeDomainStats(data, "opponent_formation");

  // Map for fast lookup by (team_formation, opponent_formation).
  const byCombo = new Map(
    data.map((d) => [`${d.team_formation}|||${d.opponent_formation}`, d]),
  );

  const maxMatches = d3.max(data, (d) => Number(d.matches) || 0) ?? 0;
  const color = createWinRateColorScale();

  // Layout: chart area + legend area.
  const legendW = 240;
  const legendH = 16;
  const gap = 26;
  const totalW = width + legendW + gap;

  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  // Init SVG once; subsequent updates should be in-place with transitions.
  container.innerHTML = "";
  const svg = d3
    .select(container)
    .append("svg")
    .attr("width", totalW)
    .attr("height", height)
    .style("background", DEFAULT_COLORS.bg);

  const tooltip = createTooltip();
  tooltip.style("opacity", 0);

  const x = d3.scaleBand().range([0, innerWidth]).padding(0.01);
  const y = d3.scaleBand().range([0, innerHeight]).padding(0.01);

  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);
  const cellsG = g.append("g").attr("class", "cells");
  const labelsG = g.append("g").attr("class", "cellLabels");
  const gridXG = g.append("g").attr("class", "gridX");
  const gridYG = g.append("g").attr("class", "gridY");

  // Axes groups (ticks are animated on update).
  const xAxisG = g.append("g").attr("transform", `translate(0,${innerHeight})`);
  const yAxisG = g.append("g");

  function styleAxes() {
    xAxisG
      .selectAll("text")
      .attr("fill", DEFAULT_COLORS.tickText)
      .attr("font-size", 12)
      .attr("text-anchor", "end")
      .attr("transform", "rotate(-45)")
      .attr("dx", "-0.6em")
      .attr("dy", "0.15em");

    yAxisG
      .selectAll("text")
      .attr("fill", DEFAULT_COLORS.tickText)
      .attr("font-size", 12);
  }

  // Axis titles (consistent labels).
  svg.append("text")
    .attr("x", margin.left)
    .attr("y", margin.top - 30)
    .attr("fill", DEFAULT_COLORS.axisText)
    .attr("font-weight", 700)
    .text("Team Formation");

  svg.append("text")
    .attr("transform", `rotate(-90)`)
    .attr("x", -margin.top)
    .attr("y", 18)
    .attr("fill", DEFAULT_COLORS.axisText)
    .attr("font-weight", 700)
    .text("Opponent Formation");

  // Win-rate legend (clearer, larger, ticks from 0%..100%).
  const legendX = margin.left + innerWidth + gap;
  const legendY = margin.top + 10;

  const gradId = `legendGrad_${Math.random().toString(16).slice(2)}`;
  const defs = svg.append("defs");
  const linearGrad = defs
    .append("linearGradient")
    .attr("id", gradId)
    .attr("x1", "0%")
    .attr("x2", "100%")
    .attr("y1", "0%")
    .attr("y2", "0%");
  linearGrad.append("stop").attr("offset", "0%").attr("stop-color", color(0));
  linearGrad.append("stop").attr("offset", "50%").attr("stop-color", color(50));
  linearGrad.append("stop").attr("offset", "75%").attr("stop-color", color(75));
  linearGrad.append("stop").attr("offset", "100%").attr("stop-color", color(100));

  svg.append("text")
    .attr("x", legendX)
    .attr("y", legendY - 12)
    .attr("fill", DEFAULT_COLORS.axisText)
    .attr("font-weight", 800)
    .text("Win rate");

  svg.append("rect")
    .attr("x", legendX)
    .attr("y", legendY)
    .attr("width", legendW)
    .attr("height", legendH)
    .attr("fill", `url(#${gradId})`);

  const legendScale = d3.scaleLinear().domain([0, 100]).range([legendX, legendX + legendW]);
  svg.append("g")
    .attr("transform", `translate(0,${legendY + legendH + 22})`)
    .call(
      d3
        .axisBottom(legendScale)
        .tickValues([0, 25, 50, 75, 100])
        .tickFormat((d) => `${d}%`),
    )
    .selectAll("text")
    .attr("fill", DEFAULT_COLORS.tickText)
    .attr("font-size", 11);

  const duration = 650;

  let activeTeamFormation = null;
  let activeOpponentFormation = null;
  let currentContext = { minMatches: 0, opacityScale: (v) => v };

  function cellKey(teamFormation, opponentFormation) {
    return `${teamFormation}|||${opponentFormation}`;
  }

  function getSelectedDomains(rawDomains, selectedDomains) {
    if (Array.isArray(selectedDomains) && selectedDomains.length > 0) {
      const selectedSet = new Set(selectedDomains.map(String));
      return rawDomains.filter((d) => selectedSet.has(String(d)));
    }
    return rawDomains;
  }

  function buildCells(xDomains, yDomains) {
    const cells = [];
    for (const teamFormation of xDomains) {
      for (const opponentFormation of yDomains) {
        const key = cellKey(teamFormation, opponentFormation);
        const row = byCombo.get(key) ?? null;
        cells.push({
          key,
          team_formation: teamFormation,
          opponent_formation: opponentFormation,
          row,
        });
      }
    }
    return cells;
  }

  function cellFill(d, { minMatches }) {
    if (!d.row) return DEFAULT_COLORS.missingCellFill;
    if (Number(d.row.matches) < minMatches) return DEFAULT_COLORS.missingCellFill;
    return color(Number(d.row.win_rate) ?? 0);
  }

  function cellOpacity(d, { minMatches, opacityScale }) {
    if (!d.row) return 1;
    if (Number(d.row.matches) < minMatches) return 1;
    return opacityScale(d.row.matches);
  }

  function applyActiveHighlight({ updateOpacity = true } = {}) {
    const { minMatches, opacityScale } = currentContext;

    cellsG.selectAll("rect.cell").each(function (d) {
      const sel = d3.select(this);
      const matches = d.row ? Number(d.row.matches) || 0 : 0;
      const valid = Boolean(d.row) && matches >= minMatches;
      const inActive =
        valid &&
        (d.team_formation === activeTeamFormation || d.opponent_formation === activeOpponentFormation);

      sel.classed("cellHighlighted", inActive);
      if (!updateOpacity) return;

      const base = cellOpacity(d, { minMatches, opacityScale });

      if (!valid) {
        sel.attr("opacity", 1);
        return;
      }

      if (activeTeamFormation == null && activeOpponentFormation == null) {
        sel.attr("opacity", base);
        return;
      }

      sel.attr("opacity", inActive ? base : Math.max(0.06, base * 0.18));
    });

    xAxisG.selectAll(".tick text").classed(
      "activeTick",
      (t) => activeTeamFormation != null && String(t) === String(activeTeamFormation),
    );
    yAxisG.selectAll(".tick text").classed(
      "activeTick",
      (t) => activeOpponentFormation != null && String(t) === String(activeOpponentFormation),
    );
  }

  function update(state) {
    const {
      sortMode,
      minMatches,
      showWinRateText,
      selectedTeamFormations,
      selectedOpponentFormations,
    } = state;

    const safeMinMatches = Math.max(0, Number(minMatches) || 0);
    const safeShowWinRateText = Boolean(showWinRateText);

    const xFiltered = getSelectedDomains(rawTeamDomainsAll, selectedTeamFormations);
    const yFiltered = getSelectedDomains(rawOpponentDomainsAll, selectedOpponentFormations);

    const xDomains = sortDomains(xFiltered, teamStats, sortMode ?? "name");
    const yDomains = sortDomains(yFiltered, opponentStats, sortMode ?? "name");

    if (xDomains.length === 0 || yDomains.length === 0) {
      tooltip.style("opacity", 0);
      activeTeamFormation = null;
      activeOpponentFormation = null;
      applyActiveHighlight();
      return;
    }

    // Reset hover highlight when the ordering/filter changes.
    activeTeamFormation = null;
    activeOpponentFormation = null;
    tooltip.style("opacity", 0);

    const opacityScale = createOpacityScale({ minMatches: safeMinMatches, maxMatches });
    currentContext = { minMatches: safeMinMatches, opacityScale };

    x.domain(xDomains);
    y.domain(yDomains);

    // Animated axis reordering.
    xAxisG.transition().duration(duration).call(d3.axisBottom(x));
    styleAxes();
    yAxisG.transition().duration(duration).call(d3.axisLeft(y));
    styleAxes();

    // Grid lines.
    const xs = d3.range(xDomains.length + 1);
    const ys = d3.range(yDomains.length + 1);

    gridXG
      .selectAll("line")
      .data(xs, (i) => i)
      .join(
        (enter) =>
          enter
            .append("line")
            .attr("stroke", DEFAULT_COLORS.gridStroke)
            .attr("stroke-width", 1),
      )
      .transition()
      .duration(duration)
      .attr("x1", (i) => i * x.bandwidth())
      .attr("x2", (i) => i * x.bandwidth())
      .attr("y1", 0)
      .attr("y2", innerHeight);

    gridYG
      .selectAll("line")
      .data(ys, (i) => i)
      .join(
        (enter) =>
          enter
            .append("line")
            .attr("stroke", DEFAULT_COLORS.gridStroke)
            .attr("stroke-width", 1),
      )
      .transition()
      .duration(duration)
      .attr("y1", (i) => i * y.bandwidth())
      .attr("y2", (i) => i * y.bandwidth())
      .attr("x1", 0)
      .attr("x2", innerWidth);

    const cells = buildCells(xDomains, yDomains);

    // Rectangles: smooth reordering transitions.
    const rectJoin = cellsG.selectAll("rect.cell").data(cells, (d) => d.key);

    rectJoin
      .exit()
      .transition()
      .duration(200)
      .style("opacity", 0)
      .remove();

    const rectEnter = rectJoin
      .enter()
      .append("rect")
      .attr("class", "cell")
      .attr("stroke", "transparent")
      .attr("stroke-width", 0)
      .attr("x", (d) => x(d.team_formation))
      .attr("y", (d) => y(d.opponent_formation))
      .attr("width", x.bandwidth())
      .attr("height", y.bandwidth())
      .attr("fill", (d) => cellFill(d, { minMatches: safeMinMatches }))
      .attr("opacity", (d) => cellOpacity(d, { minMatches: safeMinMatches, opacityScale }));

    rectEnter
      .on("mouseover", (event, d) => {
        if (!d.row) return;
        const matches = Number(d.row.matches) || 0;
        if (matches < safeMinMatches) return;

        activeTeamFormation = d.team_formation;
        activeOpponentFormation = d.opponent_formation;
        applyActiveHighlight();
        tooltip.style("opacity", 1).html(tooltipHtml(d.row));
      })
      .on("mousemove", (event) => {
        tooltip
          .style("left", `${event.pageX + 12}px`)
          .style("top", `${event.pageY - 20}px`);
      })
      .on("mouseout", () => {
        activeTeamFormation = null;
        activeOpponentFormation = null;
        applyActiveHighlight();
        tooltip.style("opacity", 0);
      });

    rectJoin
      .merge(rectEnter)
      .transition()
      .duration(duration)
      .attr("x", (d) => x(d.team_formation))
      .attr("y", (d) => y(d.opponent_formation))
      .attr("width", x.bandwidth())
      .attr("height", y.bandwidth())
      .attr("fill", (d) => cellFill(d, { minMatches: safeMinMatches }))
      .attr("opacity", (d) => cellOpacity(d, { minMatches: safeMinMatches, opacityScale }));

    // Conditional in-cell labels (avoid clutter).
    const cellW = x.bandwidth();
    const cellH = y.bandwidth();
    const showCellText =
      safeShowWinRateText && cellW > 54 && cellH > 26 && xDomains.length <= 18 && yDomains.length <= 18;

    const textJoin = labelsG.selectAll("text.cellWinRateText").data(cells, (d) => d.key);
    textJoin.exit().remove();

    const textEnter = textJoin
      .enter()
      .append("text")
      .attr("class", "cellWinRateText")
      .attr("text-anchor", "middle")
      .attr("pointer-events", "none");

    textJoin
      .merge(textEnter)
      .transition()
      .duration(duration)
      .attr("x", (d) => x(d.team_formation) + x.bandwidth() / 2)
      .attr("y", (d) => y(d.opponent_formation) + y.bandwidth() / 2 + 4)
      .style("opacity", showCellText ? 1 : 0)
      .text((d) => {
        if (!showCellText) return "";
        if (!d.row) return "";
        if (Number(d.row.matches) < safeMinMatches) return "";
        const v = Number(d.row.win_rate);
        if (!Number.isFinite(v)) return "";
        return `${v.toFixed(0)}%`;
      });

    applyActiveHighlight({ updateOpacity: false });
  }

  // Initialize once with defaults: no filters and formation-name sorting.
  update({
    sortMode: "name",
    minMatches: 0,
    showWinRateText: false,
    selectedTeamFormations: [],
    selectedOpponentFormations: [],
  });

  return { update };
}

async function main() {
  const container = document.querySelector("#chart");
  if (!container) {
    throw new Error("Missing #chart container");
  }

  const data = await d3.json(DATA_URL);

  // Control elements.
  const sortModeEl = document.querySelector("#sortMode");
  const minMatchesEl = document.querySelector("#minMatches");
  const teamFormationsSelectEl = document.querySelector("#teamFormationsSelect");
  const opponentFormationsSelectEl = document.querySelector("#opponentFormationsSelect");
  const clearTeamFormationsEl = document.querySelector("#clearTeamFormations");
  const clearOpponentFormationsEl = document.querySelector("#clearOpponentFormations");
  const showWinRateTextEl = document.querySelector("#showWinRateText");

  const allTeamFormations = uniqueSorted(data.map((d) => d.team_formation));
  const allOpponentFormations = uniqueSorted(data.map((d) => d.opponent_formation));

  function populateMultiSelect(selectEl, values) {
    if (!selectEl) return;
    selectEl.innerHTML = "";
    for (const v of values) {
      const opt = document.createElement("option");
      opt.value = String(v);
      opt.textContent = String(v);
      selectEl.appendChild(opt);
    }
  }

  populateMultiSelect(teamFormationsSelectEl, allTeamFormations);
  populateMultiSelect(opponentFormationsSelectEl, allOpponentFormations);

  const matrix = renderHeatmap(data, container, { width: 1100, height: 700 });

  function readMultiSelectValues(selectEl) {
    if (!selectEl) return [];
    return Array.from(selectEl.selectedOptions).map((o) => o.value);
  }

  function readState() {
    const minMatches = Math.max(0, Number(minMatchesEl?.value ?? 0) || 0);
    return {
      sortMode: sortModeEl?.value ?? "name",
      minMatches,
      showWinRateText: Boolean(showWinRateTextEl?.checked),
      selectedTeamFormations: readMultiSelectValues(teamFormationsSelectEl),
      selectedOpponentFormations: readMultiSelectValues(opponentFormationsSelectEl),
    };
  }

  const onStateChange = () => matrix.update(readState());

  sortModeEl?.addEventListener("change", onStateChange);
  minMatchesEl?.addEventListener("input", onStateChange);
  showWinRateTextEl?.addEventListener("change", onStateChange);
  teamFormationsSelectEl?.addEventListener("change", onStateChange);
  opponentFormationsSelectEl?.addEventListener("change", onStateChange);

  if (clearTeamFormationsEl) {
    clearTeamFormationsEl.addEventListener("click", () => {
      if (!teamFormationsSelectEl) return;
      for (const opt of teamFormationsSelectEl.options) opt.selected = false;
      onStateChange();
    });
  }

  if (clearOpponentFormationsEl) {
    clearOpponentFormationsEl.addEventListener("click", () => {
      if (!opponentFormationsSelectEl) return;
      for (const opt of opponentFormationsSelectEl.options) opt.selected = false;
      onStateChange();
    });
  }

  matrix.update(readState());
}

main().catch((err) => {
  // eslint-disable-next-line no-console
  console.error(err);
  const container = document.querySelector("#chart");
  if (container) container.innerHTML = `<div class="error">Failed to load data: ${escapeHtml(err.message)}</div>`;
});

