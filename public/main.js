/* ─────────────────────────────────────────────────────────────────
   Visualizing Code Evolution — main.js
   Reads findings.json and animates character images + stats panel
   when the user moves the slider.
─────────────────────────────────────────────────────────────────── */

/* ── Agent definitions (slider order) ── */
const AGENTS = [
  { key: 'human',       label: 'Human'          },
  { key: 'claude_code', label: 'Claude Code'    },
  { key: 'copilot',     label: 'GitHub Copilot' },
  { key: 'jules',       label: 'Google Jules'   },
  { key: 'devin',       label: 'Cognition AI Devin'    },
  { key: 'codex',       label: 'OpenAI Codex'          },
  { key: 'end',         label: 'End'            },
];

/* ── Stat definitions ── */
const STATS = [
  {
    key: 'median_pr_size',
    label: 'Median PR Size',
    fmt: v => `${Math.round(v)} lines`,
    barColor: 'orange',
    higherIsBetter: true,
  },
  {
    key: 'merge_rate',
    label: 'Merge Rate',
    fmt: v => `${(v * 100).toFixed(1)}%`,
    barColor: 'amber',
    higherIsBetter: true,
    absoluteBar: true,
  },
  {
    key: 'median_merge_time_minutes',
    label: 'Median Merge Time',
    fmt: v => v < 60 ? `${v.toFixed(1)} min` : `${(v/60).toFixed(1)} hr`,
    barColor: 'yellow',
    higherIsBetter: true,
  },
  {
    key: 'issue_linking_rate',
    label: 'Issue Linking Rate',
    fmt: v => `${(v * 100).toFixed(1)}%`,
    barColor: 'teal',
    higherIsBetter: true,
    absoluteBar: true,
  },
  {
    key: 'top_file_types',
    label: 'Top File Types',
    type: 'tags',
  },
];

/* ── Annotation definitions ── */
const ANNOTATIONS = [
  { id: 'scope'   },
  { id: 'success' },
  { id: 'note'    },
];

/* ── Annotation display ladders ──────────────────────────────────────
   Each ladder has 5 rungs [shortTrait, dataHint], index 0 = lowest.
   These mirror the normalization ranges used in generate_prompts.py.  ── */
const ANN_STAT_RANGES = {
  median_pr_size:            [50,   400],
  median_merge_time_minutes: [0,    40],
  merge_rate:                [0.60, 0.90],
};

// PR Size → head proportions (no inversion; larger PR = higher rung)
const ANN_SCOPE_LADDER = [
  ['perfectly proportioned head',       'small PRs, focused changes'],
  ['slightly wide forehead',            'modest PR size'],
  ['prominent forehead',                'medium-large PRs'],
  ['large bulging forehead',            'large PRs, broad changes'],
  ['massive giga-brain head',           'massive PRs, sweeping scope'],
];

// Merge Time → hair style (inverted; fast merge = high rung)
const ANN_SPEED_LADDER = [
  ['wild tangled hair',                 'very slow to merge'],
  ['disheveled hair',                   'slower merge time'],
  ['neatly combed hair',                'moderate merge speed'],
  ['sharp side-parted hair',            'fast merge time'],
  ['aerodynamically slicked-back hair', 'near-instant merges'],
];

// Merge Rate → expression (no inversion; higher rate = higher rung)
const ANN_RATE_LADDER = [
  ['battle-worn, rejected expression',  'low merge rate'],
  ['weary, uncertain gaze',             'below-average acceptance'],
  ['neutral composed expression',       'moderate merge rate'],
  ['confident, calm expression',        'high merge rate'],
  ['radiating approval energy',         'very high merge rate'],
];

function getAnnotationText(annId, data) {
  function rung(value, key, invert) {
    const [lo, hi] = ANN_STAT_RANGES[key];
    let score = Math.max(0, Math.min(1, (value - lo) / (hi - lo)));
    if (invert) score = 1 - score;
    return Math.round(score * 4);
  }
  if (annId === 'scope') {
    return ANN_SCOPE_LADDER[rung(data.median_pr_size ?? 0, 'median_pr_size', false)];
  }
  if (annId === 'success') {
    return ANN_SPEED_LADDER[rung(data.median_merge_time_minutes ?? 0, 'median_merge_time_minutes', true)];
  }
  if (annId === 'note') {
    return ANN_RATE_LADDER[rung(data.merge_rate ?? 0, 'merge_rate', false)];
  }
  return ['—', ''];
}

/* ── Fallback data (used if findings.json fails to load) ── */
const FALLBACK_DATA = {
  human:       { total_prs:20910, median_pr_size:60,    merge_rate:0.7512, median_merge_time_minutes:25.66, issue_linking_rate:0.0858, top_file_types:['.ts','.py','.md','.tsx','.java'] },
  claude_code: { total_prs:19148, median_pr_size:376,   merge_rate:0.8643, median_merge_time_minutes:10.58, issue_linking_rate:0.2030, top_file_types:['.ts','.md','.py','.tsx','.json'] },
  copilot:     { total_prs:18563, median_pr_size:212,   merge_rate:0.6222, median_merge_time_minutes:37.34, issue_linking_rate:0.5207, top_file_types:['.md','.ts','.py','.js','.json'] },
  jules:       { total_prs:18468, median_pr_size:112,   merge_rate:0.7728, median_merge_time_minutes:1.63,  issue_linking_rate:0.1183, top_file_types:['.py','.js','.md','.ts','.tsx']  },
  devin:       { total_prs:14045, median_pr_size:165,   merge_rate:0.6198, median_merge_time_minutes:20.92, issue_linking_rate:0.0196, top_file_types:['.ts','.tsx','.py','.md','.json'] },
  codex:       { total_prs:20835, median_pr_size:53,    merge_rate:0.8755, median_merge_time_minutes:0.47,  issue_linking_rate:0.0019, top_file_types:['.py','.js','.md','.tsx','.ts']  },
};

/* ── File type tag color map ── */
const TAG_COLORS = {
  '.js':   'tag-js',
  '.jsx':  'tag-jsx',
  '.ts':   'tag-ts',
  '.tsx':  'tag-tsx',
  '.py':   'tag-py',
  '.md':   'tag-md',
  '.java': 'tag-java',
  '.json': 'tag-json',
};

/* ── State ── */
let findings  = {};
let statRanges = {};  // { key: { min, max } }
let currentIdx = 0;

/* ────────────────────────────────────────────
   INIT
──────────────────────────────────────────── */
async function init() {
  try {
    const res = await fetch('findings.json');
    if (!res.ok) throw new Error('HTTP ' + res.status);
    findings = await res.json();
  } catch (e) {
    console.warn('Could not load findings.json, using fallback data.', e);
    findings = FALLBACK_DATA;
  }

  computeRanges();
  buildStatsPanel();
  buildSlider();
  buildMobileAnnotations();
  switchAgent(0, false /* no animation on first load */);
}

/* ── Pre-compute min/max for each numeric stat across all agents ── */
function computeRanges() {
  STATS.forEach(s => {
    if (s.type === 'tags') return;
    let min = Infinity, max = -Infinity;
    AGENTS.forEach(a => {
      const v = findings[a.key] && findings[a.key][s.key];
      if (v != null) { min = Math.min(min, v); max = Math.max(max, v); }
    });
    statRanges[s.key] = { min, max };
  });
}

/* ── Normalize 0→1 (higher = more of this stat) ── */
function normalize(value, key) {
  const { min, max } = statRanges[key];
  if (max === min) return 0.5;
  return (value - min) / (max - min);
}

/* ── Bar pct (always 0→1 where 1 = best for that stat) ── */
function barPct(value, stat) {
  if (stat.absoluteBar) return Math.max(0.04, value);
  const raw = normalize(value, stat.key);
  // Add a small floor so even the worst agent has a visible bar
  const pct = stat.higherIsBetter ? raw : 1 - raw;
  return Math.max(0.04, pct);
}

/* ────────────────────────────────────────────
   BUILD STATS PANEL  (called once on init)
──────────────────────────────────────────── */
function buildStatsPanel() {
  const list = document.getElementById('stats-list');
  list.innerHTML = '';

  STATS.forEach(s => {
    const row = document.createElement('div');
    row.className = 'stat-row';
    row.id = `stat-row-${s.key}`;

    if (s.type === 'tags') {
      row.innerHTML = `
        <div class="stat-header">
          <span class="stat-name">${s.label}</span>
        </div>
        <div class="tag-row" id="tags-${s.key}"></div>
      `;
    } else {
      row.innerHTML = `
        <div class="stat-header">
          <span class="stat-name">${s.label}</span>
          <span class="stat-value" id="val-${s.key}">—</span>
        </div>
        <div class="stat-bar-track">
          <div class="stat-bar-fill ${s.barColor}" id="bar-${s.key}" style="width:0%"></div>
        </div>
      `;
    }

    list.appendChild(row);
  });
}

/* ────────────────────────────────────────────
   BUILD SLIDER  (called once on init)
──────────────────────────────────────────── */
function buildSlider() {
  const stopsEl  = document.getElementById('slider-stops');
  const labelsEl = document.getElementById('slider-labels');

  AGENTS.forEach((agent, i) => {
    const pct = (i / (AGENTS.length - 1)) * 100;

    /* Stop dot */
    const dot = document.createElement('div');
    dot.className = 'stop-dot';
    dot.style.left = pct + '%';
    dot.dataset.idx = i;
    stopsEl.appendChild(dot);

    /* Label */
    const lbl = document.createElement('div');
    lbl.className = 'slider-label-item';
    lbl.style.left = pct + '%';
    lbl.dataset.idx = i;
    lbl.innerHTML = `<span>${agent.label}</span>`;
    lbl.addEventListener('click', () => {
      document.getElementById('agent-slider').value = i;
      switchAgent(i, true);
    });
    labelsEl.appendChild(lbl);
  });

  /* Range input handler */
  const slider = document.getElementById('agent-slider');
  slider.addEventListener('input', () => {
    const idx = parseInt(slider.value, 10);
    switchAgent(idx, true);
  });
}

/* ────────────────────────────────────────────
   BUILD MOBILE ANNOTATIONS STRIP
──────────────────────────────────────────── */
function buildMobileAnnotations() {
  const col = document.querySelector('.character-col');

  const strip = document.createElement('div');
  strip.className = 'mobile-annotations';
  strip.id = 'mobile-annotations';

  ANNOTATIONS.forEach(ann => {
    const item = document.createElement('div');
    item.className = 'mobile-ann-item';
    item.innerHTML = `
      <div class="mobile-ann-dot"></div>
      <div class="mobile-ann-text">
        <span class="mobile-ann-val" id="mob-${ann.id}">—</span>
        <span class="mobile-ann-hint" id="mob-${ann.id}-hint"></span>
      </div>
    `;
    strip.appendChild(item);
  });

  col.appendChild(strip);
}

/* ────────────────────────────────────────────
   SLIDER VISUALS HELPER
──────────────────────────────────────────── */
function updateSliderVisuals(newIdx) {
  const pct = (newIdx / (AGENTS.length - 1)) * 100;
  document.getElementById('slider-fill').style.width = pct + '%';

  document.querySelectorAll('.stop-dot').forEach((dot, i) => {
    dot.classList.toggle('active', i === newIdx);
    dot.classList.toggle('passed', i < newIdx);
  });

  document.querySelectorAll('.slider-label-item').forEach((lbl, i) => {
    lbl.classList.toggle('active', i === newIdx);
  });
}

/* ────────────────────────────────────────────
   SWITCH AGENT  (the main update function)
──────────────────────────────────────────── */
function switchAgent(newIdx, animate) {
  const prevIdx = currentIdx;
  currentIdx = newIdx;

  const agent   = AGENTS[newIdx];
  const isEnd   = agent.key === 'end';
  const wasEnd  = AGENTS[prevIdx].key === 'end';

  const stage          = document.querySelector('.stage');
  const conclusionPanel = document.getElementById('conclusion-panel');

  /* ── Handle End slide ── */
  if (isEnd) {
    if (animate && typeof gsap !== 'undefined') {
      gsap.to(stage, { opacity: 0, duration: 0.3, ease: 'power2.out', onComplete: () => {
        stage.style.display = 'none';
        conclusionPanel.style.display = 'flex';
        gsap.fromTo(conclusionPanel, { opacity: 0 }, { opacity: 1, duration: 0.4, ease: 'power2.in' });
      }});
    } else {
      stage.style.display = 'none';
      conclusionPanel.style.display = 'flex';
    }
    updateSliderVisuals(newIdx);
    return;
  }

  /* ── Restore normal view when coming from End ── */
  if (wasEnd) {
    if (animate && typeof gsap !== 'undefined') {
      gsap.to(conclusionPanel, { opacity: 0, duration: 0.3, ease: 'power2.out', onComplete: () => {
        conclusionPanel.style.display = 'none';
        stage.style.display = '';
        gsap.fromTo(stage, { opacity: 0 }, { opacity: 1, duration: 0.4, ease: 'power2.in' });
      }});
    } else {
      conclusionPanel.style.display = 'none';
      stage.style.display = '';
    }
  }

  const data  = findings[agent.key] || {};

  /* ── 1. Crossfade images ── */
  // When returning from End, all images kept their pre-End state — reset them all first
  if (wasEnd) {
    AGENTS.forEach(a => {
      if (a.key === 'end') return;
      const img = document.getElementById('img-' + a.key);
      if (!img) return;
      img.classList.remove('active');
      img.style.position = 'absolute';
      img.style.opacity  = '0';
    });
  }

  const prevImg = document.getElementById('img-' + AGENTS[prevIdx].key);
  const nextImg = document.getElementById('img-' + agent.key);

  if (prevIdx !== newIdx || !animate) {
    if (animate && typeof gsap !== 'undefined') {
      if (prevImg && prevImg !== nextImg) {
        // Fade out previous
        gsap.to(prevImg, { opacity: 0, duration: 0.35, ease: 'power2.out', onComplete: () => {
          prevImg.classList.remove('active');
          prevImg.style.position = 'absolute';
        }});
      }
      // Fade in next
      if (nextImg) {
        nextImg.classList.add('active');
        nextImg.style.position = 'relative';
        gsap.fromTo(nextImg, { opacity: 0 }, { opacity: 1, duration: 0.4, ease: 'power2.in' });
      }
    } else {
      // Instant swap (first load or no GSAP)
      if (prevImg && prevImg !== nextImg) {
        prevImg.classList.remove('active');
        prevImg.style.position = 'absolute';
        prevImg.style.opacity  = '0';
      }
      if (nextImg) {
        nextImg.classList.add('active');
        nextImg.style.position = 'relative';
        nextImg.style.opacity  = '1';
      }
    }
  }

  /* ── 2. Update character name ── */
  document.getElementById('character-name').textContent = agent.label;

  /* ── 3. Animate annotations ── */
  const annDuration = animate ? 0.25 : 0;
  const annDelay    = animate ? 0.15 : 0;

  ANNOTATIONS.forEach(ann => {
    const valEl   = document.getElementById('ann-' + ann.id + '-val');
    const hintEl  = document.getElementById('ann-' + ann.id + '-hint');
    const cardEl  = valEl ? valEl.closest('.ann-card') : null;
    const mobEl   = document.getElementById('mob-' + ann.id);

    const [fmtVal, ctx] = isEnd ? ['—', ''] : getAnnotationText(ann.id, data);

    if (animate && typeof gsap !== 'undefined' && cardEl) {
      gsap.to(cardEl, {
        opacity: 0, y: -4, duration: annDuration * 0.8, ease: 'power1.in',
        onComplete: () => {
          if (valEl)  valEl.textContent  = fmtVal;
          if (hintEl) hintEl.textContent = ctx;
          gsap.to(cardEl, { opacity: 1, y: 0, duration: annDuration, ease: 'power1.out', delay: annDelay * 0.5 });
        }
      });
    } else {
      if (valEl)  valEl.textContent  = fmtVal;
      if (hintEl) hintEl.textContent = ctx;
    }

    if (mobEl) mobEl.textContent = fmtVal;
    const mobHintEl = document.getElementById('mob-' + ann.id + '-hint');
    if (mobHintEl) mobHintEl.textContent = ctx;
  });

  /* ── 4. Animate stats bars ── */
  STATS.forEach(s => {
    if (s.type === 'tags') {
      const tagsEl = document.getElementById('tags-' + s.key);
      if (!tagsEl) return;
      const types = data[s.key] || [];
      tagsEl.innerHTML = types.map(t =>
        `<span class="tag ${TAG_COLORS[t] || ''}">${t}</span>`
      ).join('');
      return;
    }

    const valEl = document.getElementById('val-' + s.key);
    const barEl = document.getElementById('bar-' + s.key);
    if (!valEl || !barEl) return;

    const raw = data[s.key];
    if (raw == null) {
      valEl.textContent = '—';
      if (animate && typeof gsap !== 'undefined') {
        gsap.to(barEl, { width: '0%', duration: 0.5, ease: 'power2.out' });
      } else {
        barEl.style.width = '0%';
      }
      return;
    }

    valEl.textContent = s.fmt(raw);
    const pct = (barPct(raw, s) * 100).toFixed(1) + '%';

    if (animate && typeof gsap !== 'undefined') {
      gsap.to(barEl, { width: pct, duration: 0.7, ease: 'power3.out', delay: 0.05 });
    } else {
      barEl.style.width = pct;
    }
  });

  /* ── 5. Update slider fill + stop dots + labels ── */
  updateSliderVisuals(newIdx);
}

/* ── Go ── */
init();
