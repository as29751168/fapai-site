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
    $('#browse-property').href = '/?' + q.toString() + '#list';
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
  $('#inquiry-form').addEventListener('submit', (event) => { event.preventDefault(); buildInquiry(); $('#inquiry-message').focus({preventScroll:true}); $('#message-review').scrollIntoView({behavior:motion,block:'nearest'}); });
  $('#copy-message').addEventListener('click', async () => {
    const field = $('#inquiry-message');
    try {
      if (!navigator.clipboard || !window.isSecureContext) throw new Error('clipboard_unavailable');
      await navigator.clipboard.writeText(field.value);
      $('#copy-message').textContent = '已複製 ✓';
      $('#copy-status').textContent = '已複製。開啟 Anna LINE，貼上後即可由你送出。';
    } catch {
      field.focus(); field.select(); field.setSelectionRange(0, field.value.length);
      $('#copy-status').textContent = '請長按或按 Ctrl/Cmd+C 複製已選取的文字，再貼到 LINE。';
    }
  });
})();
