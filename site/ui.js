/* 透明房訊 UI 強化：開標倒數、較首拍降幅、收藏、分享、地圖、貸款試算 */
(function () {
  var K = 'fav104';
  function get() { try { return JSON.parse(localStorage.getItem(K) || '[]'); } catch (e) { return []; } }
  function set(a) { try { localStorage.setItem(K, JSON.stringify(a)); } catch (e) {} }
  var css = document.createElement('style');
  css.textContent = '.tg{position:absolute;top:8px;padding:3px 10px;border-radius:12px;font-size:12px;font-weight:700;color:#fff}.tg.l{left:8px;background:#b8893b}.tg.r{right:8px;top:44px;background:#b3261e}' +
    '.fv{position:absolute;right:8px;top:8px;width:34px;height:34px;border-radius:50%;border:0;background:rgba(255,255,255,.92);font-size:18px;line-height:34px;cursor:pointer;color:#999;padding:0}.fv.on{color:#e0245e}' +
    '.fvbar{padding:9px 14px;border:1px solid #e0245e;background:#fff;color:#e0245e;border-radius:6px;font-size:15px;cursor:pointer;font-family:inherit}.fvbar.on{background:#e0245e;color:#fff}' +
    'body.onlyfav #g .card:not(.isfav){display:none!important}' +
    '#tools h2{margin-bottom:8px}.tl2{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}.tl2 a,.tl2 button{padding:9px 14px;border-radius:8px;border:1px solid #1f3a4d;background:#fff;color:#1f3a4d;font-size:14px;cursor:pointer;text-decoration:none;font-family:inherit}.tl2 .on{background:#e0245e;border-color:#e0245e;color:#fff}' +
    '.calc{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px}.calc label{font-size:13px;color:#666;display:block}.calc input{width:100%;padding:8px;border:1px solid #ccc;border-radius:6px;font-size:15px}.res{margin-top:10px;background:#f6f1e6;border-radius:8px;padding:10px 12px;font-size:15px}.res b{color:#b3261e;font-size:18px}.note{font-size:12px;color:#888;margin-top:6px}';
  document.head.appendChild(css);

  var today = new Date(); today.setHours(0, 0, 0, 0);
  function tag(cv, cls, text) { var s = document.createElement('span'); s.className = 'tg ' + cls; s.textContent = text; cv.appendChild(s); }
  function sync() {
    var fav = get(), n = 0;
    [].forEach.call(document.querySelectorAll('.card'), function (c) {
      var id = c.getAttribute('href').split('/').pop().replace('.html', ''), on = fav.indexOf(id) > -1;
      c.classList.toggle('isfav', on); if (on) n++;
      var b = c.querySelector('.fv'); if (b) { b.classList.toggle('on', on); b.textContent = on ? '♥' : '♡'; }
    });
    var fb = document.getElementById('fvbar'); if (fb) fb.textContent = '♥ 只看收藏（' + fav.length + '）';
  }
  // 卡片強化
  [].forEach.call(document.querySelectorAll('.card'), function (c) {
    var D = c.dataset, cv = c.querySelector('.cv'); if (!cv) return;
    var d = +D.d;
    if (d && d < 99999999) {
      var days = Math.round((new Date(Math.floor(d / 10000) + 1911, Math.floor(d / 100) % 100 - 1, d % 100) - today) / 864e5);
      if (days >= 0) tag(cv, 'l', days === 0 ? '今天開標' : '還有 ' + days + ' 天開標');
    }
    var f = +D.f, p = +D.p;
    if (f && p && p < f) tag(cv, 'r', '較首拍降 ' + Math.round((1 - p / f) * 100) + '%');
    var id = c.getAttribute('href').split('/').pop().replace('.html', '');
    var b = document.createElement('button'); b.type = 'button'; b.className = 'fv'; b.setAttribute('aria-label', '收藏');
    b.addEventListener('click', function (e) {
      e.preventDefault(); e.stopPropagation();
      var a = get(), i = a.indexOf(id); if (i > -1) a.splice(i, 1); else a.push(id); set(a); sync();
    });
    cv.appendChild(b);
  });
  // 首頁：只看收藏
  var rs = document.getElementById('rs');
  if (rs) {
    var fb = document.createElement('button'); fb.type = 'button'; fb.id = 'fvbar'; fb.className = 'fvbar';
    fb.addEventListener('click', function () { document.body.classList.toggle('onlyfav'); fb.classList.toggle('on'); });
    rs.parentNode.appendChild(fb);
  }
  sync();

  // 物件頁工具
  var t = document.getElementById('tools');
  if (t) {
    var id = t.dataset.id, addr = t.dataset.addr, price = +t.dataset.price || 0;
    var q = encodeURIComponent(addr.replace(/【[^】]*】/g, ''));
    var share = 'https://line.me/R/msg/text/?' + encodeURIComponent(addr + '\n' + location.href);
    t.innerHTML = '<h2>物件工具</h2><div class="tl2"><button type="button" id="fv2"></button>' +
      '<a href="https://www.google.com/maps/search/?api=1&query=' + q + '" target="_blank" rel="noopener">Google 地圖</a>' +
      '<a href="' + share + '" target="_blank" rel="noopener">分享到 LINE</a></div>' +
      '<h2 style="font-size:16px">貸款試算（可自行調整）</h2><div class="calc">' +
      '<div><label>貸款成數 %</label><input id="c1" type="number" value="70" min="0" max="100"></div>' +
      '<div><label>年利率 %</label><input id="c2" type="number" value="2.5" step="0.01"></div>' +
      '<div><label>年限（年）</label><input id="c3" type="number" value="30" min="1" max="40"></div></div>' +
      '<div class="res" id="cr"></div><div class="note">試算僅供參考，實際成數、利率與核貸結果依銀行審核為準；另有法拍規費與稅費需自行評估。</div>';
    var fv2 = document.getElementById('fv2');
    function f2() { var on = get().indexOf(id) > -1; fv2.className = on ? 'on' : ''; fv2.textContent = on ? '♥ 已收藏' : '♡ 收藏'; }
    fv2.onclick = function () { var a = get(), i = a.indexOf(id); if (i > -1) a.splice(i, 1); else a.push(id); set(a); f2(); };
    f2();
    function calc() {
      var r = +document.getElementById('c1').value / 100, y = +document.getElementById('c2').value / 100 / 12, n = +document.getElementById('c3').value * 12;
      var loan = price * r, pay = y ? loan * y / (1 - Math.pow(1 + y, -n)) : loan / n;
      var wan = function (v) { return Math.round(v / 10000).toLocaleString(); };
      document.getElementById('cr').innerHTML = price ? ('以底價 ' + wan(price) + ' 萬試算：貸款約 <b>' + wan(loan) + '</b> 萬，每月約 <b>' + Math.round(pay).toLocaleString() + '</b> 元，自備款約 <b>' + wan(price - loan) + '</b> 萬') : '';
    }
    ['c1', 'c2', 'c3'].forEach(function (i) { document.getElementById(i).addEventListener('input', calc); }); calc();
  }
})();

/* 防複製：禁用右鍵、選取、拖曳圖片、複製與常見儲存快捷鍵（輸入框除外）。僅能提高門檻，無法完全防止截圖或原始碼檢視。 */
(function () {
  function inField(t) { return t && t.closest && t.closest('input,textarea,select,[contenteditable]'); }
  ['contextmenu', 'copy', 'cut', 'dragstart', 'selectstart'].forEach(function (ev) {
    document.addEventListener(ev, function (e) { if (!inField(e.target)) e.preventDefault(); });
  });
  document.addEventListener('keydown', function (e) {
    if (inField(e.target)) return;
    var k = (e.key || '').toLowerCase();
    if ((e.ctrlKey || e.metaKey) && ['c', 'x', 's', 'u', 'p', 'a'].indexOf(k) > -1) e.preventDefault();
    if (e.key === 'F12' || ((e.ctrlKey || e.metaKey) && e.shiftKey && ['i', 'j', 'c'].indexOf(k) > -1)) e.preventDefault();
  });
})();

/* 橫向滑動卡片：圓點隨滑動更新，點圓點跳到該張 */
(function () {
  document.querySelectorAll('[data-cr]').forEach(function (box) {
    var track = box.querySelector('.crt'), slides = track.children, dots = box.querySelector('.crdots');
    if (!slides.length) return;
    for (var i = 0; i < slides.length; i++) { var d = document.createElement('i'); d.dataset.i = i; dots.appendChild(d); }
    function mark() {
      var mid = track.scrollLeft + track.clientWidth / 2, best = 0, bd = 1e9;
      for (var i = 0; i < slides.length; i++) { var c = slides[i].offsetLeft + slides[i].offsetWidth / 2, dd = Math.abs(c - mid); if (dd < bd) { bd = dd; best = i; } }
      for (var k = 0; k < dots.children.length; k++) dots.children[k].className = k === best ? 'on' : '';
    }
    track.addEventListener('scroll', function () { window.requestAnimationFrame(mark); }, { passive: true });
    function go(i) { var s = slides[i]; track.scrollTo({ left: s.offsetLeft - (track.clientWidth - s.offsetWidth) / 2, behavior: 'smooth' }); }
    dots.addEventListener('click', function (e) { var i = e.target.dataset && e.target.dataset.i; if (i != null) go(+i); });
    mark();
    if (box.hasAttribute('data-auto')) {   /* 幻燈：每 4 秒自動換下一張；手指或滑鼠停留時暫停 */
      var cur = 0, paused = false, timer = setInterval(function () {
        if (paused || document.hidden) return;
        cur = (cur + 1) % slides.length; go(cur);
      }, 4000);
      ['touchstart', 'mouseenter', 'pointerdown'].forEach(function (ev) { box.addEventListener(ev, function () { paused = true; }, { passive: true }); });
      ['mouseleave'].forEach(function (ev) { box.addEventListener(ev, function () { paused = false; }); });
      track.addEventListener('scroll', function () { var m = track.scrollLeft + track.clientWidth / 2; for (var i = 0; i < slides.length; i++) { var c = slides[i].offsetLeft + slides[i].offsetWidth / 2; if (Math.abs(c - m) < slides[i].offsetWidth / 2) { cur = i; break; } } }, { passive: true });
      box.addEventListener('touchend', function () { setTimeout(function () { paused = false; }, 6000); }, { passive: true });
    }
  });
})();
