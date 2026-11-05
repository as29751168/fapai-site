'use strict';
(() => {
  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => [...document.querySelectorAll(selector)];
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth';

  const menuButton = $('.menu-toggle');
  const nav = $('#primary-nav');
  function closeMenu() {
    menuButton.setAttribute('aria-expanded', 'false');
    menuButton.setAttribute('aria-label', '開啟導覽選單');
    nav.classList.remove('is-open');
  }
  menuButton.addEventListener('click', () => {
    const open = menuButton.getAttribute('aria-expanded') !== 'true';
    menuButton.setAttribute('aria-expanded', String(open));
    menuButton.setAttribute('aria-label', open ? '關閉導覽選單' : '開啟導覽選單');
    nav.classList.toggle('is-open', open);
  });
  nav.addEventListener('click', (event) => { if (event.target.closest('a')) closeMenu(); });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && nav.classList.contains('is-open')) { closeMenu(); menuButton.focus(); }
  });
  document.addEventListener('click', (event) => { if (!event.target.closest('.site-header')) closeMenu(); });
  window.matchMedia('(min-width:701px)').addEventListener('change', closeMenu);

  const tabs = $$('#step-tabs [role="tab"]');
  const panels = $$('.step-detail');
  let step = 0;
  function selectStep(index, focusTab = false, revealTab = false) {
    step = Math.max(0, Math.min(tabs.length - 1, index));
    tabs.forEach((tab, i) => {
      tab.setAttribute('aria-selected', String(i === step));
      tab.tabIndex = i === step ? 0 : -1;
      panels[i].hidden = i !== step;
    });
    $('#previous-step').disabled = step === 0;
    $('#next-step').disabled = step === tabs.length - 1;
    $('#step-progress').textContent = `${String(step + 1).padStart(2, '0')} / 09`;
    if (focusTab) tabs[step].focus({preventScroll:true});
    if (revealTab && window.matchMedia('(max-width:700px)').matches) {
      const rail = $('#step-tabs');
      rail.scrollTo({left: tabs[step].offsetLeft - rail.offsetLeft - (rail.clientWidth - tabs[step].clientWidth) / 2, behavior: motion});
    }
  }
  tabs.forEach((tab, i) => tab.addEventListener('click', () => selectStep(i, false, true)));
  $('#step-tabs').addEventListener('keydown', (event) => {
    let target;
    if (event.key === 'ArrowRight' || event.key === 'ArrowDown') target = (step + 1) % tabs.length;
    if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') target = (step + tabs.length - 1) % tabs.length;
    if (event.key === 'Home') target = 0;
    if (event.key === 'End') target = tabs.length - 1;
    if (target !== undefined) { event.preventDefault(); selectStep(target, true, true); }
  });
  function stepFromHash() {
    const match = location.hash.match(/^#step-([1-9])$/);
    if (match) selectStep(Number(match[1]) - 1, false, true);
  }
  function advanceStep(direction) {
    selectStep(step + direction, false, true);
    panels[step].focus({preventScroll:true});
    if (window.matchMedia('(max-width:700px)').matches) panels[step].scrollIntoView({behavior:motion,block:'start'});
  }
  $('#previous-step').addEventListener('click', () => advanceStep(-1));
  $('#next-step').addEventListener('click', () => advanceStep(1));
  const horizontal = window.matchMedia('(max-width:700px)');
  function setTabOrientation() { $('#step-tabs').setAttribute('aria-orientation', horizontal.matches ? 'horizontal' : 'vertical'); }
  horizontal.addEventListener('change', setTabOrientation);
  setTabOrientation();
  selectStep(0);
  stepFromHash();
  window.addEventListener('hashchange', stepFromHash);

  let selectedRegion = '台北市';
  const regionNotes = { '台北市': '通勤、學區與生活機能，一起納入評估。', '新北市': '捷運沿線與不同生活圈，依需求一起篩選。', '桃園市': '空間、通勤與購屋預算，找到合適的平衡。' };
  $$('[data-region]').forEach((button) => button.addEventListener('click', () => {
    selectedRegion = button.dataset.region;
    $$('[data-region]').forEach((item) => item.setAttribute('aria-pressed', String(item === button)));
    $('#region-caption').textContent = `${selectedRegion}｜${regionNotes[selectedRegion]}`;
  }));
  $('#use-property').addEventListener('click', () => {
    $('#inquiry-region').value = selectedRegion;
    $('#inquiry-budget').value = $('#property-budget').value;
    const type = $('#property-type').value;
    $('#inquiry-note').value = `想了解${selectedRegion}${type === '不限類型' ? '的法拍物件' : `的${type}`}，請協助評估合適案件與需要準備的資金。`;
    if (!$('#message-review').hidden) buildInquiry();
    location.hash = 'contact';
    $('#inquiry-note').focus({preventScroll:true});
  });

  const BROWSE = {
    cities: { '台北市': '台北', '新北市': '新北', '桃園市': '桃園' },
    budgets: { '1,000 萬元以下': '0-1000', '1,000–2,000 萬元': '1000-2000', '2,000–3,000 萬元': '2000-3000', '3,000 萬元以上': '3000-1000000' },
    types: { '電梯大樓': ['大樓,華廈', '電梯大樓'], '透天住宅': ['透天', '透天住宅'], '公寓': ['公寓', '公寓'], '店面／辦公': ['店面,商辦,辦公室', '店面／辦公'] }
  };
  function updateBrowse() {
    const q = new URLSearchParams();
    q.set('c', BROWSE.cities[selectedRegion] || '');
    const p = BROWSE.budgets[$('#property-budget').value];
    if (p) q.set('p', p);
    const t = BROWSE.types[$('#property-type').value];
    if (t) { q.set('t', t[0]); q.set('tl', t[1]); }
    $('#browse-property').href = '/list?' + q.toString();
  }
  $$('[data-region]').forEach((b) => b.addEventListener('click', updateBrowse));
  $('#property-budget').addEventListener('change', updateBrowse);
  $('#property-type').addEventListener('change', updateBrowse);
  updateBrowse();

  const promoActive = () => Date.now() < Date.parse('2027-01-01T00:00:00+08:00');
  function updateRates() {
    const offer = promoActive();
    $('#handover-rate').textContent = offer ? '2' : '3';
    $('#occupied-rate').textContent = offer ? '4' : '5';
    $('#handover-original').hidden = !offer;
    $('#occupied-original').hidden = !offer;
    $('#offer-banner').textContent = offer ? '2026 年底前服務費優惠' : '代標服務費標準';
    if (!offer) $('.fee-note').textContent = '部分點交依實際範圍與難易度個別評估。2026 年底優惠已結束；實際服務範圍、費用與付款方式以委託契約為準。';
  }
  document.addEventListener('visibilitychange', () => { if (!document.hidden) updateRates(); });
  updateRates();

  function buildInquiry() {
    const region = $('#inquiry-region').value;
    const budget = $('#inquiry-budget').value;
    const note = $('#inquiry-note').value.trim();
    $('#inquiry-message').value = `Anna 您好，我想諮詢法拍購屋。\n想找地區：${region}\n購屋預算：${budget}\n${note ? `案件或需求：${note}` : '想先了解適合的案件、購屋流程與資金準備。'}\n請協助評估，謝謝！`;
    $('#message-review').hidden = false;
    $('#copy-status').textContent = '';
    $('#copy-message').textContent = '複製訊息';
  }
  $('#send-line').addEventListener('click', () => {
    try { navigator.clipboard && window.isSecureContext && navigator.clipboard.writeText($('#inquiry-message').value); } catch {}
    $('#copy-status').textContent = '訊息已複製。加入 LINE@ 後，請在對話框貼上並按送出，我們才會收到通知。';
  });
  $('#inquiry-form').addEventListener('submit', (event) => { event.preventDefault(); buildInquiry(); $('#inquiry-message').focus({preventScroll:true}); $('#message-review').scrollIntoView({behavior:motion,block:'nearest'}); });
  $('#copy-message').addEventListener('click', async () => {
    const field = $('#inquiry-message');
    try {
      if (!navigator.clipboard || !window.isSecureContext) throw new Error('clipboard_unavailable');
      await navigator.clipboard.writeText(field.value);
      $('#copy-message').textContent = '已複製 ✓';
      $('#copy-status').textContent = '已複製。開啟 LINE@，貼上後即可由你送出。';
    } catch {
      field.focus(); field.select(); field.setSelectionRange(0, field.value.length);
      $('#copy-status').textContent = '請長按或按 Ctrl/Cmd+C 複製已選取的文字，再貼到 LINE。';
    }
  });
})();

(function () {
  const bar = document.querySelector('.mobile-contact');
  const target = document.getElementById('contact');
  if (!bar || !target || !('IntersectionObserver' in window)) return;
  new IntersectionObserver((entries) => {
    entries.forEach((e) => bar.classList.toggle('is-hidden', e.isIntersecting));
  }, { rootMargin: '0px 0px -20% 0px' }).observe(target);
})();

/* ===== 動態：開標倒數、即時符合筆數、記住上次條件 ===== */
(function () {
  const $ = (s) => document.querySelector(s);
  const store = {
    get() { try { return JSON.parse(localStorage.getItem('fp_last') || 'null'); } catch (e) { return null; } },
    set(v) { try { localStorage.setItem('fp_last', JSON.stringify(v)); } catch (e) {} }
  };

  // 開標倒數
  const today = new Date(); today.setHours(0, 0, 0, 0);
  document.querySelectorAll('.live-open[data-open]').forEach((el) => {
    if (!el.dataset.open) return;
    const d = new Date(el.dataset.open + 'T00:00:00');
    const n = Math.round((d - today) / 86400000);
    if (n === 0) el.textContent = '今日開標';
    else if (n === 1) el.textContent = '明日開標';
    else if (n > 1 && n <= 14) el.textContent = n + ' 天後開標';
    else if (n < 0) el.textContent = '開標日已過，請洽最新拍次';
    if (n >= 0 && n <= 3) el.classList.add('is-soon');
  });

  // 即時符合筆數（與 /list 篩選規則一致）
  let IDX = [];
  try { IDX = JSON.parse($('#live-index').textContent); } catch (e) {}
  const CITY = { '台北市': '台北', '新北市': '新北', '桃園市': '桃園' };
  const BUD = { '1,000 萬元以下': [0, 1000], '1,000–2,000 萬元': [1000, 2000], '2,000–3,000 萬元': [2000, 3000], '3,000 萬元以上': [3000, 1e6] };
  const TYPE = { '電梯大樓': ['大樓', '華廈'], '透天住宅': ['透天'], '公寓': ['公寓'], '店面／辦公': ['店面', '商辦', '辦公室'] };
  const btn = $('#browse-property'), hint = $('#match-hint');
  function region() { const b = document.querySelector('[data-region][aria-pressed="true"]'); return b ? b.dataset.region : '台北市'; }
  function count(withFilters) {
    const c = CITY[region()], bd = BUD[$('#property-budget').value], ty = TYPE[$('#property-type').value];
    return IDX.filter((r) => r[0] === c && (!withFilters || ((!bd || (r[2] >= bd[0] && r[2] < bd[1])) && (!ty || ty.indexOf(r[1]) > -1)))).length;
  }
  function label() {
    const parts = [CITY[region()]];
    if (BUD[$('#property-budget').value]) parts.push($('#property-budget').value);
    if (TYPE[$('#property-type').value]) parts.push($('#property-type').value);
    return parts.join('・');
  }
  function refresh() {
    if (!btn || !IDX.length) return;
    const n = count(true), all = count(false);
    if (n > 0) {
      btn.innerHTML = '看 <b>' + n + '</b> 筆物件 <span aria-hidden="true">↗</span>';
      hint.className = 'match-hint';
      hint.innerHTML = label() + '：目前有 <b>' + n + '</b> 筆符合';
    } else {
      btn.innerHTML = '看' + CITY[region()] + '全部 ' + all + ' 筆 <span aria-hidden="true">↗</span>';
      hint.className = 'match-hint is-zero';
      hint.textContent = '這組條件目前沒有案件，可放寬預算或類型，或先看' + CITY[region()] + '全部。';
      btn.href = '/list?c=' + CITY[region()];
    }
  }
  ['change'].forEach((ev) => { $('#property-budget').addEventListener(ev, refresh); $('#property-type').addEventListener(ev, refresh); });
  document.querySelectorAll('[data-region]').forEach((b) => b.addEventListener('click', refresh));

  // 記住上次條件
  function save(href, text) { store.set({ href: href, text: text, region: region(), budget: $('#property-budget').value, type: $('#property-type').value }); }
  if (btn) btn.addEventListener('click', () => save(btn.getAttribute('href'), label()));
  document.querySelectorAll('.live-chips a:not(.chip-all)').forEach((a) => a.addEventListener('click', () => store.set({ href: a.getAttribute('href'), text: a.textContent.replace(/\d+$/, ''), region: a.textContent.replace(/\d+$/, '') + '市', budget: '尚未決定', type: '不限類型' })));
  const last = store.get(), link = $('#resume-link');
  if (last && last.href && link) {
    link.href = last.href;
    link.textContent = '繼續看上次的條件：' + last.text + ' →';
    link.hidden = false;
    const rb = document.querySelector('[data-region="' + last.region + '"]');
    if (rb) rb.click();
    if (last.budget) $('#property-budget').value = last.budget;
    if (last.type) $('#property-type').value = last.type;
    $('#property-budget').dispatchEvent(new Event('change'));
    $('#property-type').dispatchEvent(new Event('change'));
  }
  refresh();
})();
