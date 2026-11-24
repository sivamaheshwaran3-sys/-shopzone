(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const csrf = () => ($('meta[name=csrf]') || {}).content || '';

  /* ---------- toasts ---------- */
  const box = $('#toasts');
  function toast(msg, type = 'success') {
    const t = document.createElement('div');
    t.className = 'toast ' + type;
    t.textContent = msg;
    box.appendChild(t);
    arm(t);
  }
  function arm(t) {
    setTimeout(() => t.classList.add('hide'), 3200);
    setTimeout(() => t.remove(), 3700);
    t.addEventListener('click', () => t.remove());
  }
  $$('.toast', box).forEach(arm);

  /* ---------- dark mode ---------- */
  const themeBtn = $('#theme-toggle');
  const syncIcon = () => themeBtn && (themeBtn.textContent = document.documentElement.dataset.theme === 'dark' ? '☀️' : '🌙');
  syncIcon();
  themeBtn && themeBtn.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('theme', next); } catch (e) {}
    syncIcon();
  });

  /* ---------- mobile nav / user menu / filters ---------- */
  $('#burger')?.addEventListener('click', () => $('#nav').classList.toggle('open'));
  const dd = $('#user-dropdown');
  $('#user-btn')?.addEventListener('click', e => { e.stopPropagation(); dd.hidden = !dd.hidden; });
  document.addEventListener('click', e => {
    if (dd && !dd.contains(e.target)) dd.hidden = true;
    if (!e.target.closest('.search')) hideSuggest();
  });
  $('#filter-toggle')?.addEventListener('click', () => $('#filters').classList.toggle('open'));

  /* ---------- cart badge ---------- */
  function setCount(n) {
    const c = $('#cart-count');
    if (!c) return;
    c.textContent = n;
    if (n) c.removeAttribute('data-zero'); else c.setAttribute('data-zero', '');
    c.classList.remove('bump'); void c.offsetWidth; c.classList.add('bump');
  }

  /* ---------- AJAX add to cart ---------- */
  document.addEventListener('submit', async e => {
    const form = e.target.closest('.js-cart-form');
    if (!form) return;
    if (e.submitter && e.submitter.name === 'buy_now') return; // normal submit -> checkout
    e.preventDefault();
    const btn = e.submitter || $('button[type=submit]', form);
    const label = btn.innerHTML;
    btn.disabled = true; btn.innerHTML = 'Adding…';
    try {
      const res = await fetch(form.action, {
        method: 'POST', body: new FormData(form),
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      });
      const data = await res.json();
      toast(data.message, data.ok ? 'success' : 'error');
      if (typeof data.count === 'number') setCount(data.count);
    } catch (err) {
      form.submit();
    } finally {
      btn.disabled = false; btn.innerHTML = label;
    }
  });

  /* ---------- wishlist ---------- */
  document.addEventListener('click', async e => {
    const btn = e.target.closest('[data-wish]');
    if (!btn) return;
    e.preventDefault();
    const fd = new FormData();
    fd.append('next', location.pathname + location.search);
    try {
      const res = await fetch(`/wishlist/toggle/${btn.dataset.wish}/`, {
        method: 'POST', body: fd,
        headers: { 'X-CSRFToken': csrf(), 'X-Requested-With': 'XMLHttpRequest' },
      });
      const data = await res.json();
      if (res.status === 401 && data.login) { location.href = data.login; return; }
      $$(`[data-wish="${btn.dataset.wish}"]`).forEach(b => b.classList.toggle('active', data.added));
      toast(data.message, 'success');
      if (location.pathname.startsWith('/wishlist') && !data.added) {
        btn.closest('.product')?.remove();
      }
    } catch (err) { toast('Something went wrong', 'error'); }
  });

  /* ---------- quantity steppers ---------- */
  $$('.qty').forEach(q => {
    const input = $('input', q);
    const max = parseInt(q.dataset.max || input.max || '99', 10);
    $$('button', q).forEach(b => b.addEventListener('click', () => {
      const v = Math.min(max, Math.max(1, (parseInt(input.value, 10) || 1) + parseInt(b.dataset.step, 10)));
      if (v !== parseInt(input.value, 10)) {
        input.value = v;
        if (q.hasAttribute('data-autosubmit')) input.form.submit();
      }
    }));
    input.addEventListener('change', () => {
      input.value = Math.min(max, Math.max(1, parseInt(input.value, 10) || 1));
      if (q.hasAttribute('data-autosubmit')) input.form.submit();
    });
  });

  /* ---------- live search suggestions ---------- */
  const sInput = $('#search-input');
  const sBox = $('#suggest');
  let timer, seq = 0;
  function hideSuggest() { if (sBox) sBox.hidden = true; }
  const inr = n => '₹' + Number(n).toLocaleString('en-IN');
  const esc = s => s.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  sInput?.addEventListener('input', () => {
    clearTimeout(timer);
    const q = sInput.value.trim();
    if (q.length < 2) return hideSuggest();
    timer = setTimeout(async () => {
      const my = ++seq;
      try {
        const res = await fetch('/api/search/?q=' + encodeURIComponent(q));
        const data = await res.json();
        if (my !== seq) return;
        if (!data.results.length) {
          sBox.innerHTML = '<div class="s-empty">No matches 😕</div>';
        } else {
          sBox.innerHTML = data.results.map(r => `
            <a href="${r.url}">
              <span class="s-ico">${r.image ? `<img src="${esc(r.image)}" alt="">` : esc(r.emoji)}</span>
              <span class="s-txt"><b>${esc(r.name)}</b><small>${esc(r.category)}</small></span>
              <span class="s-price">${inr(r.price)}</span>
            </a>`).join('');
        }
        sBox.hidden = false;
      } catch (e) { hideSuggest(); }
    }, 220);
  });
  sInput?.addEventListener('focus', () => { if (sBox && sBox.innerHTML.trim() && sInput.value.trim().length > 1) sBox.hidden = false; });

  /* ---------- confirm dialogs ---------- */
  document.addEventListener('submit', e => {
    const msg = e.target.dataset && e.target.dataset.confirm;
    if (msg && !confirm(msg)) e.preventDefault();
  });

  /* ---------- scroll reveal + back-to-top ---------- */
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver(entries => entries.forEach(en => {
      if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
    }), { threshold: 0.08 });
    $$('.reveal').forEach(el => io.observe(el));
  } else {
    $$('.reveal').forEach(el => el.classList.add('in'));
  }
  const top = $('#to-top');
  window.addEventListener('scroll', () => { top.hidden = window.scrollY < 500; }, { passive: true });
  top?.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
})();
