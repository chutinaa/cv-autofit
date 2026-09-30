/*! cv-autofit.js — fit any HTML resume onto exactly N pages. MIT.
 *
 * Contract (the only thing your CSS has to do):
 *   .page{ padding: var(--mvt) var(--mh) var(--mv); font-size: var(--fs); line-height: var(--lh); }
 *   .page h2{ margin: var(--sg) 0 calc(var(--sg)*.35); }     section gap
 *   .page ul{ margin: .15em 0 var(--eg); }                    entry gap
 *   .page li{ margin-bottom: var(--bg); }                     bullet gap
 *   .page{ width:210mm }  and fixed page height 1123px (A4 @96dpi) or pass pageHeight.
 *
 * Usage:
 *   var result = CVAutofit.fit(document.querySelector('.page'), { lang:'en' });
 *   // result = {fs,lh,mv,mh,mvt,sg,eg,bg,ols,pages,fallback}
 *
 * Variable names are configurable via opts.vars. Everything is measured on the live DOM
 * at zoom 100% (opts.zoomEl is reset to zoom 1 during measurement and restored after).
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.CVAutofit = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  /* ---- per-language knob ranges: [tightest, loosest] -------------------------------- */
  var RANGES = {
    cn: { fs: [12, 14.67], lh: [1.35, 1.5], sg: [1.0, 1.4], eg: [0.25, 0.5], bg: [0.05, 0.12], m: [14, 18] },
    en: { fs: [12, 14],    lh: [1.15, 1.35], sg: [1.0, 1.4], eg: [0.25, 0.5], bg: [0.05, 0.12], m: [14, 18] },
    fr: { fs: [12, 14],    lh: [1.2, 1.4],  sg: [1.0, 1.4], eg: [0.25, 0.5], bg: [0.05, 0.12], m: [14, 18] }
  };
  var DEFAULTS = {
    lang: "en",            // picks RANGES[lang]; or pass opts.range
    pages: 1,
    pageHeight: 1123,      // px, A4 297mm @96dpi
    printSlack: 4,         // px kept free at the bottom: screen vs PDF pagination differs by a hair
    wideMargin: 18,        // mm, upper margin bound for sparse content
    lhFloor: 1.1,          // line-height never below this even in the "no floor" scale layer
    topOffset: 2, topMin: 13, // top margin = side margin - topOffset, min topMin (optical compensation for the big name)
    wFs: 3, wM: 1,         // cost weights: font concession vs margin concession
    orphanRatio: 0.3,      // last line under 30% of width = orphan
    orphanMaxLs: { cn: 0.05, en: 0.04, fr: 0.05 }, // per-bullet letter-spacing cap (em)
    lsSlack: 0.0075,
    regrowMiss: 4,
    bullets: "li",
    vars: { fs: "--fs", lh: "--lh", mv: "--mv", mh: "--mh", mvt: "--mvt", sg: "--sg", eg: "--eg", bg: "--bg" },
    zoomEl: null,          // element whose style.zoom is forced to 1 while measuring
    onApply: null,         // function(L) called after every apply (e.g. to update a form)
    log: false
  };
  var PX_PER_MM = 3.7795;

  function assign(a, b) { for (var k in b) if (b[k] !== undefined) a[k] = b[k]; return a; }
  function lerpR(r, t) { return r[1] - t * (r[1] - r[0]); }
  function seg(t, a, b) { return Math.min(1, Math.max(0, (t - a) / (b - a))); }

  function fit(pageEl, options) {
    var o = assign(assign({}, DEFAULTS), options || {});
    o.vars = assign(assign({}, DEFAULTS.vars), (options && options.vars) || {});
    var R = o.range || RANGES[o.lang] || RANGES.en;
    var cap = o.pages * o.pageHeight - o.printSlack;
    var L = { fs: 0, lh: 0, mv: 0, mh: 0, sg: 0, eg: 0, bg: 0, ols: [], olsN: -1, _fb: 0 };
    var sparse = false, fitlog = [];

    /* ---- DOM plumbing ------------------------------------------------------------- */
    function withZoom1(fn) {
      var z = o.zoomEl ? o.zoomEl.style.zoom : null;
      if (o.zoomEl) o.zoomEl.style.zoom = "1";
      try { return fn(); } finally { if (o.zoomEl) o.zoomEl.style.zoom = z; }
    }
    function mvTop() { return Math.max(o.topMin, L.mh - o.topOffset); }
    function apply() {
      var s = pageEl.style, v = o.vars;
      s.setProperty(v.fs, L.fs + "px"); s.setProperty(v.lh, L.lh);
      s.setProperty(v.mv, L.mv + "mm"); s.setProperty(v.mh, L.mh + "mm"); s.setProperty(v.mvt, mvTop().toFixed(2) + "mm");
      s.setProperty(v.sg, L.sg + "px"); s.setProperty(v.eg, L.eg + "px"); s.setProperty(v.bg, L.bg + "px");
      applyOls();
      if (o.onApply) o.onApply(L);
    }
    function lis() { return pageEl.querySelectorAll(o.bullets); }
    function applyOls() {
      var ls = lis(); ls.forEach(function (li) { li.style.letterSpacing = ""; });
      if (!L.ols.length || L.olsN !== ls.length) return;
      L.ols.forEach(function (p) { if (ls[p[0]]) ls[p[0]].style.letterSpacing = p[1].toFixed(4) + "em"; });
    }
    function contentH() {
      return withZoom1(function () { var mh = pageEl.style.minHeight; pageEl.style.minHeight = "0"; var h = pageEl.scrollHeight; pageEl.style.minHeight = mh; return h; });
    }
    function setGaps(sgR, egR, bgR) { var lhpx = L.fs * L.lh; L.sg = +(lhpx * sgR).toFixed(1); L.eg = +(lhpx * egR).toFixed(1); L.bg = +(lhpx * bgR).toFixed(1); }
    function applyT(t) {
      var t1 = seg(t, 0, 0.4), t2 = seg(t, 0.3, 0.7), t3 = seg(t, 0.6, 1);
      L.fs = +lerpR(R.fs, t2).toFixed(2); L.lh = +lerpR(R.lh, t1).toFixed(3);
      setGaps(lerpR(R.sg, t1), lerpR(R.eg, t1), lerpR(R.bg, t1));
      L.mv = L.mh = +lerpR(R.m, t3).toFixed(1); apply();
    }
    function applyK(k) {
      L.fs = +(R.fs[0] * k).toFixed(2); L.lh = +Math.max(o.lhFloor, R.lh[0] * k).toFixed(3);
      setGaps(R.sg[0], R.eg[0], R.bg[0]); L.mv = L.mh = R.m[0]; apply();
    }
    function applyMF(m, t1, t2) {
      L.fs = +lerpR(R.fs, t2).toFixed(2); L.lh = +lerpR(R.lh, t1).toFixed(3);
      setGaps(lerpR(R.sg, t1), lerpR(R.eg, t1), lerpR(R.bg, t1)); L.mv = L.mh = m; apply();
    }

    /* ---- orphan measurement ------------------------------------------------------- */
    function liLines(li) { var lh = parseFloat(getComputedStyle(li).lineHeight); return Math.round(li.getBoundingClientRect().height / lh); }
    function lastLineRatio(li) {
      var r = document.createRange(); r.selectNodeContents(li); var rects = r.getClientRects(); if (!rects.length) return 1;
      var lh = parseFloat(getComputedStyle(li).lineHeight) || 12, bot = -1e9, i;
      for (i = 0; i < rects.length; i++) if (rects[i].width > 0 && rects[i].bottom > bot) bot = rects[i].bottom;
      var l = 1e9, rt = -1e9;
      for (i = 0; i < rects.length; i++) { var q = rects[i]; if (q.width > 0 && q.bottom > bot - lh * 0.5) { if (q.left < l) l = q.left; if (q.right > rt) rt = q.right; } }
      var b = li.getBoundingClientRect(); return rt <= l ? 0 : (rt - l) / b.width;
    }
    function orphanCost() {
      return withZoom1(function () { var c = 0; lis().forEach(function (li) { if (liLines(li) < 2) return; var q = lastLineRatio(li); if (q < o.orphanRatio) c += o.orphanRatio - q; }); return c; });
    }
    function orphLs() { return o.orphanMaxLs[o.lang] || 0.04; }
    function tightenOrphans() {
      return withZoom1(function () {
        var fixed = 0, ols = [], ls = lis(); L.ols = []; L.olsN = ls.length;
        ls.forEach(function (li, idx) {
          li.style.letterSpacing = ""; var n = liLines(li); if (n < 2) return;
          if (lastLineRatio(li) >= o.orphanRatio) return;
          for (var k = 0.005; k <= orphLs() - o.lsSlack + 1e-9; k += 0.0025) {            // condense: pull last line up
            li.style.letterSpacing = (-k).toFixed(4) + "em";
            if (liLines(li) < n) { var kk = +(k + o.lsSlack).toFixed(4); li.style.letterSpacing = (-kk).toFixed(4) + "em"; fixed++; ols.push([idx, -kk]); return; }
          }
          for (var k2 = 0.005; k2 <= orphLs() + 1e-9; k2 += 0.0025) {                    // expand: push last line past 30%
            li.style.letterSpacing = k2.toFixed(4) + "em"; var n2 = liLines(li); if (n2 > n) break;
            if (lastLineRatio(li) >= o.orphanRatio) {
              li.style.letterSpacing = (k2 + o.lsSlack).toFixed(4) + "em"; var safe = liLines(li) === n; li.style.letterSpacing = k2.toFixed(4) + "em";
              if (!safe) break; fixed++; ols.push([idx, +k2.toFixed(4)]); return;
            }
          }
          li.style.letterSpacing = "";
        });
        L.ols = ols; return fixed;
      });
    }

    /* ---- layer 1–3: find t / k ------------------------------------------------------ */
    applyT(0);
    if (contentH() > cap) {
      applyT(1);
      if (contentH() > cap) {
        // layer 3: margins locked at minimum, scale font with no floor
        var lo = 0.2, hi = 1;
        for (var i = 0; i < 14; i++) { var k = (lo + hi) / 2; applyK(k); if (contentH() > cap) hi = k; else lo = k; }
        applyK(lo);
      } else {
        // layer 2: margin × font-size cost trade-off
        var best = null;
        for (var m = R.m[1]; m >= R.m[0] - 1e-9; m -= 0.5) {
          m = +m.toFixed(1); applyMF(m, 1, 0); var t2 = 0;
          if (contentH() > cap) {
            applyMF(m, 1, 1); if (contentH() > cap) continue;
            var alo = 0, ahi = 1; for (var j = 0; j < 10; j++) { var a = (alo + ahi) / 2; applyMF(m, 1, a); if (contentH() > cap) alo = a; else ahi = a; } t2 = ahi;
          }
          var c = o.wFs * t2 + o.wM * (R.m[1] - m) / (R.m[1] - R.m[0]);
          fitlog.push([m, L.fs, +c.toFixed(3)]);
          if (!best || c < best.c - 1e-9) best = { m: m, t2: t2, c: c };
        }
        if (!best) best = { m: R.m[0], t2: 1 };
        // font at its max → relax line-height/gaps until just-fits; otherwise keep tight for regrow
        var bhi = 1;
        if (best.t2 === 0) { var blo = 0; for (var q = 0; q < 8; q++) { var b = (blo + bhi) / 2; applyMF(best.m, b, 0); if (contentH() > cap) blo = b; else bhi = b; } }
        applyMF(best.m, bhi, best.t2);
      }
    } else {
      sparse = true;
      while (L.mv < o.wideMargin) { L.mv = L.mh = L.mv + 1; apply(); if (contentH() > cap) { L.mv = L.mh = L.mv - 1; apply(); break; } }
    }

    /* ---- orphan pass + regrow --------------------------------------------------------- */
    var sgR = L.sg / (L.fs * L.lh), egR = L.eg / (L.fs * L.lh), bgR = L.bg / (L.fs * L.lh);
    function orph1() {
      L.ols = []; apply(); var m0 = L.mv, f0 = L.fs, best = { m: m0, f: f0, c: orphanCost() }, minH = sparse ? 0 : cap - L.fs * L.lh * 1.5;
      var fj = [0, 0.1, 0.2, 0.3, 0.4, 0.5, -0.1, -0.2, -0.3, -0.4, -0.5];
      var mHi = Math.min(o.wideMargin, m0 + 2.5), mLo = Math.max(R.m[0], m0 - 1.5);
      for (var m = mHi; m >= mLo - 1e-9; m -= 0.25) {
        m = +m.toFixed(2);
        for (var q = 0; q < fj.length; q++) {
          var f = +(f0 + fj[q]).toFixed(2); if (f < R.fs[0] - 1e-9) continue; if (m === m0 && f === f0) continue;
          L.mv = L.mh = m; L.fs = f; setGaps(sgR, egR, bgR); apply(); var h = contentH(); if (h > cap || h < minH) continue;
          var c = orphanCost();
          if (c < best.c - 1e-6 || (Math.abs(c - best.c) < 1e-6 && (m > best.m || (m === best.m && f > best.f)))) best = { m: m, f: f, c: c };
          if (best.c < 1e-6) break;
        }
        if (best.c < 1e-6) break;
      }
      L.mv = L.mh = best.m; L.fs = best.f; setGaps(sgR, egR, bgR); apply();
    }
    function regrow() {
      var n = 0, miss = 0, ok = { f: L.fs, ols: L.ols, N: L.olsN }, f = L.fs;
      while (f < R.fs[1] - 1e-9 && miss < o.regrowMiss) {
        f = +(f + 0.1).toFixed(2); L.fs = f; setGaps(sgR, egR, bgR); L.ols = []; apply(); tightenOrphans(); apply();
        if (contentH() > cap) miss++; else { miss = 0; n++; ok = { f: f, ols: L.ols, N: L.olsN }; }
      }
      L.fs = ok.f; L.ols = ok.ols; L.olsN = ok.N; setGaps(sgR, egR, bgR); apply(); return n;
    }
    var L2 = assign({}, L);
    orph1();
    for (var rd = 0; rd < 3; rd++) { tightenOrphans(); apply(); if (regrow() === 0) break; orph1(); }
    tightenOrphans(); apply();
    // fallback: if orphan work shrank the font below layer-2 and left >1.5 lines empty, revert
    if (L.fs < L2.fs - 1e-9 && cap - contentH() > L.fs * L.lh * 1.5) { assign(L, L2); L._fb = 1; apply(); }

    /* ---- distribute leftover: bottom margin (≤2mm) → entry gap (≤1mm) → section gap (≤1mm) ---- */
    var left = cap - contentH();
    if (left > 0) {
      var add = Math.min(2, Math.floor(left / PX_PER_MM / 2 * 2) / 2); L.mv = +(L.mv + add).toFixed(1); apply();
      while (contentH() > cap && L.mv > L.mh + 1e-9) { L.mv = +(L.mv - 0.5).toFixed(1); apply(); }
    }
    var egCap = L.eg + PX_PER_MM; while (L.eg < egCap) { L.eg = +(L.eg + 0.5).toFixed(1); apply(); if (contentH() > cap) { L.eg = +(L.eg - 0.5).toFixed(1); apply(); break; } }
    var sgCap = L.sg + PX_PER_MM; while (L.sg < sgCap) { L.sg = +(L.sg + 0.5).toFixed(1); apply(); if (contentH() > cap) { L.sg = +(L.sg - 0.5).toFixed(1); apply(); break; } }

    var out = { fs: L.fs, lh: L.lh, mv: L.mv, mh: L.mh, mvt: +mvTop().toFixed(2), sg: L.sg, eg: L.eg, bg: L.bg, ols: L.ols,
                pages: Math.ceil(contentH() / o.pageHeight), fallback: !!L._fb, sparse: sparse, fitlog: fitlog };
    if (o.log && console) console.table(fitlog);
    return out;
  }

  /* convenience: CSS text for @page so print margins match the screen */
  function pageCSS(res) { return "@page{size:A4;margin:" + res.mvt + "mm " + res.mh + "mm " + res.mv + "mm " + res.mh + "mm;}"; }

  return { fit: fit, pageCSS: pageCSS, RANGES: RANGES, DEFAULTS: DEFAULTS, version: "1.0.0" };
});
