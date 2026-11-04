/* XONINAS · utilidades comunes */
(function () {
  var root = document.documentElement;
  var CSRF = (document.querySelector('meta[name="csrf"]') || {}).content || '';
  window.XN = { csrf: CSRF };

  /* Tema claro / oscuro */
  function applyTheme(t) { root.setAttribute('data-theme', t); try { localStorage.setItem('xn-theme', t); } catch (e) {} }
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-theme-toggle]');
    if (b) applyTheme(root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
  });

  /* Confirmaciones en formularios y botones */
  document.addEventListener('submit', function (e) {
    var msg = e.target.getAttribute('data-confirm');
    if (msg && !window.confirm(msg)) e.preventDefault();
  });

  /* Copiar texto */
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-copy]');
    if (!b) return;
    var text = b.getAttribute('data-copy');
    (navigator.clipboard ? navigator.clipboard.writeText(text) : Promise.reject()).then(function () {
      var old = b.textContent; b.textContent = 'Copiado'; setTimeout(function () { b.textContent = old; }, 1400);
    }).catch(function () { window.prompt('Copia la dirección:', text); });
  });

  /* Lista de destinatarios del correo */
  function bindRecipients(box) {
    var list = box.querySelector('[data-rcpt-list]');
    var tpl = box.querySelector('template');
    function add(addr, on) {
      var n = tpl.content.firstElementChild.cloneNode(true);
      var t = n.querySelector('input[type=text], input[type=email]');
      var c = n.querySelector('input[type=checkbox]');
      t.value = addr || ''; c.checked = on !== false; c.value = t.value;
      list.appendChild(n); t.focus();
    }
    box.addEventListener('input', function (e) {
      if (e.target.matches('input[type=email]')) {
        var c = e.target.closest('.rcpt').querySelector('input[type=checkbox]'); c.value = e.target.value.trim();
      }
    });
    box.addEventListener('click', function (e) {
      if (e.target.closest('[data-rcpt-add]')) { e.preventDefault(); add('', true); }
      var x = e.target.closest('.x');
      if (x) { e.preventDefault(); x.closest('.rcpt').remove(); }
    });
  }
  document.querySelectorAll('[data-recipients]').forEach(bindRecipients);

  /* Mostrar u ocultar bloques según un interruptor */
  document.querySelectorAll('[data-toggles]').forEach(function (sw) {
    var target = document.getElementById(sw.getAttribute('data-toggles'));
    function sync() { if (target) target.hidden = !sw.checked; }
    sw.addEventListener('change', sync); sync();
  });

  /* Subida con progreso real */
  XN.upload = function (url, formData, cb) {
    var xhr = new XMLHttpRequest();
    xhr.open('POST', url);
    xhr.setRequestHeader('X-CSRF-Token', CSRF);
    xhr.upload.onprogress = function (e) { if (e.lengthComputable && cb.progress) cb.progress(e.loaded, e.total); };
    xhr.onload = function () {
      var data = {}; try { data = JSON.parse(xhr.responseText); } catch (e) {}
      if (xhr.status >= 200 && xhr.status < 300 && data.ok) cb.done && cb.done(data);
      else cb.error && cb.error(data.error || ('Error ' + xhr.status));
    };
    xhr.onerror = function () { cb.error && cb.error('Se perdió la conexión.'); };
    xhr.send(formData);
  };
  XN.size = function (n) {
    if (n > 1048576) return (n / 1048576).toFixed(1) + ' MB';
    if (n > 1024) return (n / 1024).toFixed(1) + ' KB';
    return n + ' B';
  };
})();
