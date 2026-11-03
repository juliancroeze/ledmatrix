/* LED Matrix dashboard */
(() => {
  'use strict';

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const MODES = Object.fromEntries(window.LED.modes.map(m => [m.id, m]));
  const LIVE_PANELS = ['webcam', 'screen', 'draw', 'text', 'image'];

  let state = window.LED.state;
  let selected = state.mode;           // which tile/panel is open
  const socket = io({ transports: ['websocket', 'polling'] });

  // ------------------------------------------------------------------ utils
  const isTouch = () => matchMedia('(pointer: coarse)').matches || (navigator.maxTouchPoints > 0 && !matchMedia('(pointer: fine)').matches);
  function toast(message, type = 'info') {
    const el = document.createElement('div');
    el.className = 'toast' + (type === 'error' ? ' error' : '');
    el.textContent = message;
    $('#toasts').appendChild(el);
    setTimeout(() => el.remove(), 3200);
  }

  async function api(path, body, opts = {}) {
    const init = { method: 'POST', ...opts };
    if (body instanceof FormData) init.body = body;
    else if (body !== undefined) {
      init.headers = { 'Content-Type': 'application/json' };
      init.body = JSON.stringify(body);
    }
    let res;
    try {
      res = await fetch(path, init);
    } catch (e) {
      throw new Error("Can't reach the matrix. Check that the Pi is on.");
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) throw new Error(data.message || `Request failed (${res.status})`);
    if (data.state) applyState(data.state);
    return data;
  }

  function segmented(el, onChange) {
    el.addEventListener('click', e => {
      const b = e.target.closest('button');
      if (!b) return;
      $$('button', el).forEach(x => x.classList.toggle('active', x === b));
      onChange && onChange(b.dataset.value);
    });
    return () => ($('button.active', el) || {}).dataset?.value;
  }

  // ------------------------------------------------------------------ state
  function applyState(s) {
    state = s;
    const on = s.on && s.mode;
    const info = on ? MODES[s.mode] : null;
    document.body.classList.toggle('is-on', !!on);
    $('#now-label').textContent = info ? info.label : 'Off';
    $('#now-sub').textContent = subtitle(s, info);
    $('#stop-btn').disabled = !on;
    $$('.tile').forEach(t => {
      t.classList.toggle('running', on && t.dataset.mode === s.mode);
      t.setAttribute('aria-pressed', on && t.dataset.mode === s.mode ? 'true' : 'false');
    });
    const b = $('#brightness');
    if (document.activeElement !== b) {
      b.value = s.brightness;
      $('#brightness-value').textContent = s.brightness + '%';
    }
    if (!on && pad.open) closePad();
    updateGameInfo();
    // keep showing the stream panel while a stream is running even if
    // another device took over, so the user can stop it
    if (selected === undefined || selected === null) select(s.mode, false);
  }

  function subtitle(s, info) {
    if (!info) return 'Pick a mode to start';
    if (info.group === 'games') return 'Game running';
    if (info.id === 'webcam' || info.id === 'screen') {
      return streamer.active ? 'Streaming from this device' : 'Waiting for a device to stream';
    }
    if (info.id === 'text' && s.options && s.options.text) return '“' + s.options.text.slice(0, 40) + '”';
    if (info.id === 'weather' && s.options && s.options.city) return s.options.city;
    return 'Running';
  }

  // ------------------------------------------------------------------ socket
  socket.on('disconnect', () => toast('Lost connection to the matrix, reconnecting…', 'error'));
  socket.on('state', applyState);

  // ------------------------------------------------------------------ preview
  // Each matrix pixel is drawn as a round LED on a high-resolution canvas:
  // the frame is scaled up (no smoothing), cut out with a dot mask, and added
  // on top of a layer of dim "unlit" LEDs.
  class LedScreen {
    constructor(canvas) {
      this.c = canvas;
      this.ctx = canvas.getContext('2d');
      this.layer = document.createElement('canvas');
      this.pitch = 0;
      this.last = null;
      new ResizeObserver(() => this.resize()).observe(canvas);
    }
    resize() {
      const w = this.c.clientWidth * (window.devicePixelRatio || 1);
      if (!w) return;
      const pitch = Math.max(2, Math.round(w / 192));
      if (pitch === this.pitch) return;
      this.pitch = pitch;
      const W2 = 192 * pitch, H2 = 64 * pitch;
      this.c.width = this.layer.width = W2;
      this.c.height = this.layer.height = H2;
      // dot mask + unlit layer, built once per size
      const mk = (color) => {
        const cv = Object.assign(document.createElement('canvas'), { width: W2, height: H2 });
        const g = cv.getContext('2d');
        const tile = Object.assign(document.createElement('canvas'), { width: pitch, height: pitch });
        const t = tile.getContext('2d');
        t.fillStyle = color;
        t.beginPath();
        t.arc(pitch / 2, pitch / 2, pitch * 0.4, 0, Math.PI * 2);
        t.fill();
        g.fillStyle = g.createPattern(tile, 'repeat');
        g.fillRect(0, 0, W2, H2);
        return cv;
      };
      this.dots = mk('#fff');
      this.unlit = mk('#1a1d25');
      if (this.last) this.draw(this.last); else this.draw(null);
    }
    draw(bmp) {
      if (!this.pitch) this.resize();
      if (!this.pitch) return;
      const { ctx, c, layer } = this;
      const l = layer.getContext('2d');
      ctx.globalCompositeOperation = 'source-over';
      ctx.clearRect(0, 0, c.width, c.height);
      ctx.drawImage(this.unlit, 0, 0);
      if (!bmp) return;
      l.globalCompositeOperation = 'source-over';
      l.imageSmoothingEnabled = false;
      l.clearRect(0, 0, layer.width, layer.height);
      l.drawImage(bmp, 0, 0, layer.width, layer.height);
      l.globalCompositeOperation = 'destination-in';
      l.drawImage(this.dots, 0, 0);
      ctx.globalCompositeOperation = 'lighter';
      ctx.drawImage(layer, 0, 0);
      ctx.globalCompositeOperation = 'source-over';
    }
    show(bmp) {
      if (this.last && this.last !== bmp && this.last.close) this.last.close();
      this.last = bmp;
      if (this.c.offsetParent !== null) this.draw(bmp);
    }
  }
  const screens = [new LedScreen($('#pad-preview'))];   // preview only lives in the game controller
  const glowCanvas = document.createElement('canvas');
  glowCanvas.width = 24; glowCanvas.height = 8;
  const glowCtx = glowCanvas.getContext('2d', { willReadFrequently: true });
  let lastGlow = '';

  socket.on('preview', async (buf) => {
    if (document.hidden || !pad.open) return;
    try {
      const bmp = await createImageBitmap(new Blob([buf], { type: 'image/png' }));
      screens.forEach(sc => sc.show(bmp));
      // average colour of the frame drives the UI glow
      // average of the lit areas only, so a thin line on black still counts
      glowCtx.drawImage(bmp, 0, 0, 24, 8);
      const px = glowCtx.getImageData(0, 0, 24, 8).data;
      let r = 0, g = 0, b = 0;
      for (let i = 0; i < px.length; i += 4) {
        if (Math.max(px[i], px[i + 1], px[i + 2]) > 20) { r += px[i]; g += px[i + 1]; b += px[i + 2]; }
      }
      const max = Math.max(r, g, b);
      if (max > 0) {
        const k = 255 / max;                      // normalise brightness
        const glow = `${Math.round(r * k)}, ${Math.round(g * k)}, ${Math.round(b * k)}`;
        if (glow !== lastGlow) {
          document.documentElement.style.setProperty('--glow', glow);
          lastGlow = glow;
        }
      }
    } catch (e) { /* ignore broken frame */ }
  });

  // ------------------------------------------------------------------ tiles & panels
  // On narrow screens the controls are a bottom sheet that slides over the modes.
  const narrow = matchMedia('(max-width: 959px)');
  function openSheet() {
    if (!narrow.matches) return;
    document.body.classList.add('sheet-open');
    $('#sheet-backdrop').hidden = false;
  }
  function closeSheet() {
    document.body.classList.remove('sheet-open');
    $('#sheet-backdrop').hidden = true;
  }
  $('#sheet-close').addEventListener('click', closeSheet);
  $('#sheet-backdrop').addEventListener('click', closeSheet);
  narrow.addEventListener && narrow.addEventListener('change', closeSheet);

  function select(modeId, open = true) {
    selected = modeId;
    const info = MODES[modeId];
    const panel = info ? info.panel : null;
    $$('.panel').forEach(p => { p.hidden = p.dataset.panel !== panel; });
    $$('.tile').forEach(t => t.classList.toggle('selected', t.dataset.mode === modeId));
    $('#sheet-empty').hidden = !!panel;
    if (panel === 'gamepad') updateGameInfo();
    if (open && panel) openSheet();
    else if (!panel) closeSheet();
  }

  $$('.tile').forEach(tile => tile.addEventListener('click', async () => {
    const id = tile.dataset.mode;
    const info = MODES[id];
    select(id);
    // Modes that need input first only open their panel
    if (LIVE_PANELS.includes(info.panel)) {
      if (id === 'draw') startDrawMode();
      return;
    }
    try {
      await api('/api/mode', { mode: id });
      if (info.group === 'games' && isTouch()) openPad(id);
    } catch (e) { toast(e.message, 'error'); }
  }));

  $('#stop-btn').addEventListener('click', async () => {
    streamer.stop(false);
    try { await api('/api/stop'); toast('Matrix turned off'); } catch (e) { toast(e.message, 'error'); }
  });

  let brightnessTimer;
  $('#brightness').addEventListener('input', e => {
    const v = e.target.value;
    $('#brightness-value').textContent = v + '%';
    clearTimeout(brightnessTimer);
    brightnessTimer = setTimeout(() => api('/api/brightness', { value: +v }).catch(err => toast(err.message, 'error')), 120);
  });

  // ------------------------------------------------------------------ secure context note
  if (!window.isSecureContext) {
    $$('[data-needs-secure]').forEach(el => {
      el.hidden = false;
      el.innerHTML = 'Browsers only allow camera and screen access over HTTPS. Start the server with ' +
        '<code>sudo python3 index.py --https</code> and open <code>https://' + location.hostname + ':' + (location.port || 8000) + '</code>.';
    });
  }
  if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
    if (window.isSecureContext) $('#screen-unsupported').hidden = false;
  }

  // ------------------------------------------------------------------ streaming (camera + screen)
  const W = 192, H = 64;
  const streamer = {
    active: null,          // 'webcam' | 'screen' | null
    stream: null,
    timerWorker: null,
    inflight: false,
    inflightAt: 0,
    sent: 0,
    lastStats: 0,
    facing: 'user',
    canvas: Object.assign(document.createElement('canvas'), { width: W, height: H }),
    fit: { webcam: 'cover', screen: 'contain' },
    fps: 20,

    video(kind) { return kind === 'webcam' ? $('#webcam-video') : $('#screen-video'); },

    async start(kind) {
      if (!navigator.mediaDevices) { toast('Camera and screen access need HTTPS', 'error'); return; }
      this.stop(false);
      try {
        // Ask for the device first: getDisplayMedia must run straight from the click
        this.stream = kind === 'webcam'
          ? await navigator.mediaDevices.getUserMedia({ video: { facingMode: this.facing, width: { ideal: 640 }, height: { ideal: 480 } }, audio: false })
          : await navigator.mediaDevices.getDisplayMedia({ video: { frameRate: 30 }, audio: false });
      } catch (e) {
        if (e.name !== 'NotAllowedError' && e.name !== 'AbortError') toast(e.message, 'error');
        else toast(kind === 'webcam' ? 'Camera access was blocked' : 'Screen sharing was cancelled', 'error');
        return;
      }
      this.active = kind;
      const video = this.video(kind);
      video.srcObject = this.stream;
      video.classList.toggle('mirror', kind === 'webcam' && $('#webcam-mirror').checked);
      video.closest('.stream-view').classList.add('streaming');
      try { await video.play(); } catch (e) { /* autoplay quirks */ }
      this.stream.getVideoTracks()[0].addEventListener('ended', () => this.stop());
      try {
        await api('/api/mode', { mode: kind });
      } catch (e) {
        toast(e.message, 'error');
        this.stop(false);
        return;
      }
      this.sent = 0;
      this.lastStats = performance.now();
      this.inflight = false;
      // A worker timer keeps ticking when the tab is in the background,
      // which matters for screen sharing.
      const src = 'let t;onmessage=e=>{clearInterval(t);if(e.data>0)t=setInterval(()=>postMessage(0),e.data)}';
      this.timerWorker = new Worker(URL.createObjectURL(new Blob([src], { type: 'text/javascript' })));
      this.timerWorker.onmessage = () => this.tick();
      this.setRate();
      updateStreamButtons();
      applyState(state);
    },

    setRate() {
      if (!this.timerWorker) return;
      const fps = this.active === 'screen' ? this.fps : 24;
      this.timerWorker.postMessage(Math.round(1000 / fps));
    },

    stop(notify = true) {
      if (!this.active && !this.stream) return;
      const kind = this.active;
      if (this.timerWorker) { this.timerWorker.terminate(); this.timerWorker = null; }
      if (this.stream) this.stream.getTracks().forEach(t => t.stop());
      this.stream = null;
      this.active = null;
      ['webcam', 'screen'].forEach(k => {
        const v = this.video(k);
        v.srcObject = null;
        v.closest('.stream-view').classList.remove('streaming');
        $(`[data-stats="${k}"]`).textContent = '';
      });
      updateStreamButtons();
      if (notify && kind) toast(kind === 'webcam' ? 'Camera stopped' : 'Screen sharing stopped');
      applyState(state);
    },

    tick() {
      const now = performance.now();
      if (this.inflight && now - this.inflightAt < 1000) return;   // wait for the Pi to keep up
      const video = this.video(this.active);
      if (!video || video.readyState < 2 || !video.videoWidth) return;
      const ctx = this.canvas.getContext('2d');
      ctx.fillStyle = '#000';
      ctx.fillRect(0, 0, W, H);
      ctx.save();
      if (this.active === 'webcam' && $('#webcam-mirror').checked) {
        ctx.translate(W, 0);
        ctx.scale(-1, 1);
      }
      drawFitted(ctx, video, video.videoWidth, video.videoHeight, this.fit[this.active]);
      ctx.restore();
      this.inflight = true;
      this.inflightAt = now;
      this.canvas.toBlob(blob => {
        if (!blob || !this.active) { this.inflight = false; return; }
        blob.arrayBuffer().then(buf => {
          socket.timeout(2000).emit('stream-frame', buf, () => { this.inflight = false; });
          this.sent++;
        });
      }, 'image/jpeg', 0.82);
      if (now - this.lastStats > 1000) {
        const fps = this.sent * 1000 / (now - this.lastStats);
        $(`[data-stats="${this.active}"]`).textContent = `${fps.toFixed(0)} frames per second to the matrix`;
        this.sent = 0;
        this.lastStats = now;
      }
    },
  };

  function drawFitted(ctx, src, sw, sh, fit) {
    if (fit === 'stretch') return ctx.drawImage(src, 0, 0, W, H);
    const scale = fit === 'cover' ? Math.max(W / sw, H / sh) : Math.min(W / sw, H / sh);
    const dw = sw * scale, dh = sh * scale;
    ctx.drawImage(src, (W - dw) / 2, (H - dh) / 2, dw, dh);
  }

  function updateStreamButtons() {
    $$('[data-stream-toggle]').forEach(btn => {
      const kind = btn.dataset.streamToggle;
      const live = streamer.active === kind;
      btn.classList.toggle('btn-primary', !live);
      btn.classList.toggle('is-live', live);
      $('use', btn).setAttribute('href', live ? '#i-square' : '#i-play');
      $('span', btn).textContent = live ? 'Stop' : (kind === 'webcam' ? 'Start camera' : 'Share screen');
    });
  }

  $$('[data-stream-toggle]').forEach(btn => btn.addEventListener('click', () => {
    const kind = btn.dataset.streamToggle;
    if (streamer.active === kind) streamer.stop();
    else streamer.start(kind);
  }));
  $$('[data-fit-for]').forEach(el => segmented(el, v => { streamer.fit[el.dataset.fitFor] = v; }));
  segmented($('#screen-fps'), v => { streamer.fps = +v; streamer.setRate(); });
  $('#webcam-mirror').addEventListener('change', e => $('#webcam-video').classList.toggle('mirror', e.target.checked));
  $('#webcam-flip').addEventListener('click', () => {
    streamer.facing = streamer.facing === 'user' ? 'environment' : 'user';
    $('#webcam-mirror').checked = streamer.facing === 'user';
    if (streamer.active === 'webcam') streamer.start('webcam');
  });
  window.addEventListener('pagehide', () => streamer.stop(false));

  // ------------------------------------------------------------------ drawing
  const dc = $('#draw-canvas');
  const dctx = dc.getContext('2d');
  dctx.fillStyle = '#000';
  dctx.fillRect(0, 0, W, H);
  let drawColor = '#ff3b3b', brush = 2, tool = 'brush', drawing = false, last = null, liveTimer = null, liveDirty = false;

  async function startDrawMode() {
    if (state.mode === 'draw' && state.on) return;
    try { await api('/api/mode', { mode: 'draw' }); } catch (e) { toast(e.message, 'error'); }
  }

  function canvasPoint(e) {
    const r = dc.getBoundingClientRect();
    return { x: (e.clientX - r.left) * W / r.width, y: (e.clientY - r.top) * H / r.height };
  }
  function stamp(x, y) {
    const s = brush, o = Math.floor(s / 2);
    dctx.fillRect(Math.floor(x) - o, Math.floor(y) - o, s, s);
  }
  function line(a, b) {
    const steps = Math.max(1, Math.ceil(Math.hypot(b.x - a.x, b.y - a.y)));
    for (let i = 0; i <= steps; i++) stamp(a.x + (b.x - a.x) * i / steps, a.y + (b.y - a.y) * i / steps);
  }
  dc.addEventListener('pointerdown', e => {
    dc.setPointerCapture(e.pointerId);
    drawing = true;
    dctx.fillStyle = tool === 'eraser' ? '#000' : drawColor;
    last = canvasPoint(e);
    stamp(last.x, last.y);
    markDirty();
  });
  dc.addEventListener('pointermove', e => {
    if (!drawing) return;
    const events = e.getCoalescedEvents ? e.getCoalescedEvents() : [e];
    events.forEach(ev => { const p = canvasPoint(ev); line(last, p); last = p; });
    markDirty();
  });
  ['pointerup', 'pointercancel'].forEach(t => dc.addEventListener(t, () => {
    if (drawing && $('#draw-live').checked) sendDrawing(true);
    drawing = false;
  }));

  function markDirty() {
    if (!$('#draw-live').checked) return;
    liveDirty = true;
    if (!liveTimer) liveTimer = setTimeout(() => { liveTimer = null; if (liveDirty) sendDrawing(true); }, 180);
  }

  async function sendDrawing(quiet) {
    liveDirty = false;
    const body = new URLSearchParams({ image_data: dc.toDataURL('image/png') });
    try {
      const res = await fetch('/send-drawing', { method: 'POST', body });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).message || 'Could not send drawing');
      if (!quiet) toast('Drawing sent to the matrix');
    } catch (e) {
      toast(e.message.includes('fetch') ? "Can't reach the matrix" : e.message, 'error');
    }
  }

  $('#swatches').addEventListener('click', e => {
    const s = e.target.closest('.swatch');
    if (!s || s.classList.contains('swatch-custom')) return;
    $$('.swatch').forEach(x => x.classList.toggle('active', x === s));
    drawColor = s.dataset.color;
    setTool('brush');
  });
  $('#custom-color').addEventListener('input', e => {
    drawColor = e.target.value;
    const c = e.target.closest('.swatch');
    c.style.setProperty('--c', drawColor);
    $$('.swatch').forEach(x => x.classList.toggle('active', x === c));
    setTool('brush');
  });
  const toolSeg = $('#draw-tool');
  segmented(toolSeg, v => { tool = v; });
  function setTool(t) {
    tool = t;
    $$('button', toolSeg).forEach(b => b.classList.toggle('active', b.dataset.value === t));
  }
  $('#brush-size').addEventListener('input', e => { brush = +e.target.value; $('#brush-size-value').textContent = brush; });
  $('#clear-canvas').addEventListener('click', () => {
    dctx.fillStyle = '#000';
    dctx.fillRect(0, 0, W, H);
    if ($('#draw-live').checked) sendDrawing(true);
  });
  $('#send-to-matrix').addEventListener('click', () => sendDrawing(false));

  // ------------------------------------------------------------------ text
  const getTextSize = segmented($('#text-size'));
  $('#text-speed').addEventListener('input', e => { $('#text-speed-value').textContent = e.target.value; });
  $('#text-send').addEventListener('click', async () => {
    const text = $('#text-input').value.trim();
    if (!text) { toast('Type a message first', 'error'); $('#text-input').focus(); return; }
    try {
      await api('/api/text', {
        text,
        color: $('#text-color').value,
        rainbow: $('#text-rainbow').checked,
        speed: +$('#text-speed').value,
        size: getTextSize(),
      });
      toast('Message is on the matrix');
    } catch (e) { toast(e.message, 'error'); }
  });
  $('#text-input').addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); $('#text-send').click(); }
  });

  // ------------------------------------------------------------------ image
  const getFit = segmented($('#image-fit'));
  let imageFile = null;
  const dz = $('#dropzone');
  function pickImage(file) {
    if (!file || !file.type.startsWith('image/')) { toast("That file isn't an image", 'error'); return; }
    imageFile = file;
    const img = $('#image-thumb');
    img.src = URL.createObjectURL(file);
    img.hidden = false;
    $('#dropzone-text').hidden = true;
  }
  $('#image-file').addEventListener('change', e => pickImage(e.target.files[0]));
  ['dragenter', 'dragover'].forEach(t => dz.addEventListener(t, e => { e.preventDefault(); dz.classList.add('drag'); }));
  ['dragleave', 'drop'].forEach(t => dz.addEventListener(t, e => { e.preventDefault(); dz.classList.remove('drag'); }));
  dz.addEventListener('drop', e => pickImage(e.dataTransfer.files[0]));
  $('#image-send').addEventListener('click', async () => {
    const fd = new FormData();
    if (imageFile) fd.append('file', imageFile);
    fd.append('fit', getFit());
    const btn = $('#image-send');
    btn.disabled = true;
    try {
      await api('/api/image', fd);
      toast(imageFile && imageFile.type === 'image/gif' ? 'GIF is playing' : 'Image is on the matrix');
    } catch (e) { toast(e.message, 'error'); }
    btn.disabled = false;
  });

  // ------------------------------------------------------------------ weather
  $('#weather-form').addEventListener('submit', async e => {
    e.preventDefault();
    try {
      await api('/api/mode', { mode: 'weather', options: { city: $('#weather-city').value } });
    } catch (err) { toast(err.message, 'error'); }
  });

  // ------------------------------------------------------------------ game controller
  const pad = { open: false, mode: null, player: 1, repeat: {} };
  const padEl = $('#pad');

  function gameScoreText(s) {
    const g = s.game;
    if (!g) return '';
    if (s.mode === 'pong') return `${g.score} : ${g.cpu}`;
    return String(g.score ?? '');
  }

  function updateGameInfo() {
    const info = MODES[selected];
    if (info && info.panel === 'gamepad') {
      $('#game-title').textContent = info.label;
      $('#game-hint').textContent = info.controls.hint || '';
      const running = state.on && state.mode === info.id;
      const g = running ? state.game : null;
      let html = '';
      if (g) {
        html = gameScoreText(state);
        if (g.best !== undefined) html += `<small>best ${g.best}</small>`;
        if (g.lines !== undefined) html += `<small>${g.lines} lines · level ${g.level}</small>`;
        if (g.game_over) html += '<small>game over</small>';
      }
      $('#game-score').innerHTML = html;
      $('#open-controller').textContent = running ? 'Open controller' : 'Start ' + info.label;
    }
    if (pad.open) $('#pad-score').textContent = state.mode === pad.mode ? gameScoreText(state) : '';
  }

  $('#open-controller').addEventListener('click', async () => {
    const info = MODES[selected];
    if (!(state.on && state.mode === info.id)) {
      try { await api('/api/mode', { mode: info.id }); } catch (e) { toast(e.message, 'error'); return; }
    }
    openPad(info.id);
  });

  function openPad(id) {
    const info = MODES[id];
    const c = info.controls || {};
    pad.open = true;
    pad.mode = id;
    $('#pad-name').textContent = info.label;
    $('#pad-hint').textContent = c.hint || '';
    const dpad = $('#dpad');
    dpad.hidden = c.dpad === false;
    dpad.classList.toggle('vertical', c.dpad === 'vertical');
    $('#paddle').hidden = !c.slider;
    $('#pad-player').hidden = !c.players;
    $('#btn-b').hidden = !c.b;
    $('small', $('#btn-a')).textContent = c.a || '';
    $('small', $('#btn-b')).textContent = c.b || '';
    padEl.classList.toggle('big-a', c.dpad === false && !c.slider);
    padEl.classList.toggle('slider-only', c.dpad === false && !!c.slider);
    padEl.hidden = false;
    document.body.style.overflow = 'hidden';
    updateGameInfo();
    if (padEl.requestFullscreen && isTouch() && !matchMedia('(display-mode: standalone)').matches) {
      padEl.requestFullscreen().catch(() => {});
    }
  }

  function closePad() {
    pad.open = false;
    padEl.hidden = true;
    document.body.style.overflow = '';
    Object.keys(pad.repeat).forEach(stopRepeat);
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
  }
  $('#pad-close').addEventListener('click', closePad);
  segmented($('#pad-player'), v => { pad.player = +v; });

  function send(action, pressed) {
    socket.emit('game-input', { action, pressed, player: pad.player });
  }
  function press(action) {
    const c = (MODES[pad.mode] || MODES[state.mode] || {}).controls || {};
    send(action, true);
    if (navigator.vibrate) navigator.vibrate(8);
    if ((c.repeat || []).includes(action) && !pad.repeat[action]) {
      pad.repeat[action] = setTimeout(function rep() {
        send(action, true);
        pad.repeat[action] = setTimeout(rep, 70);
      }, 190);
    }
  }
  function stopRepeat(action) {
    clearTimeout(pad.repeat[action]);
    delete pad.repeat[action];
  }
  function release(action) {
    stopRepeat(action);
    send(action, false);
  }

  $$('[data-action]', padEl).forEach(btn => {
    const action = btn.dataset.action;
    btn.addEventListener('pointerdown', e => {
      e.preventDefault();
      btn.setPointerCapture(e.pointerId);
      btn.classList.add('pressed');
      press(action);
    });
    const up = () => { if (btn.classList.contains('pressed')) { btn.classList.remove('pressed'); release(action); } };
    btn.addEventListener('pointerup', up);
    btn.addEventListener('pointercancel', up);
    btn.addEventListener('contextmenu', e => e.preventDefault());
  });

  // Pong touch slider: absolute paddle position
  const paddle = $('#paddle'), knob = $('#paddle-knob');
  function movePaddle(e) {
    const r = paddle.getBoundingClientRect();
    const pos = Math.min(1, Math.max(0, (e.clientY - r.top - 28) / (r.height - 56)));
    knob.style.top = (12 + pos * (r.height - 80)) + 'px';
    socket.emit('paddle', { pos, player: pad.player });
  }
  paddle.addEventListener('pointerdown', e => { paddle.setPointerCapture(e.pointerId); movePaddle(e); });
  paddle.addEventListener('pointermove', e => { if (e.buttons || e.pointerType === 'touch') movePaddle(e); });

  // Keyboard: works whenever a game is running (controller open or not)
  const KEYMAP = { ArrowUp: 'UP', ArrowDown: 'DOWN', ArrowLeft: 'LEFT', ArrowRight: 'RIGHT', w: 'UP', s: 'DOWN', a: 'LEFT', d: 'RIGHT', z: 'A', Enter: 'A', x: 'B', Shift: 'B' };
  const held = new Set();
  function keyAction(e) {
    const info = MODES[state.mode];
    if (!info || info.group !== 'games' || !state.on) return null;
    if (e.target.closest && e.target.closest('input, textarea')) return null;
    if (e.key === ' ') return (info.controls && info.controls.space) || ((info.controls && info.controls.b) ? 'B' : 'A');
    return KEYMAP[e.key] || KEYMAP[e.key.toLowerCase()] || null;
  }
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && pad.open) { closePad(); return; }
    if (e.key === 'Escape' && document.body.classList.contains('sheet-open')) { closeSheet(); return; }
    const action = keyAction(e);
    if (!action) return;
    e.preventDefault();
    if (held.has(e.code)) return;      // ignore OS auto-repeat, we repeat ourselves
    held.add(e.code);
    pad.mode = state.mode;
    press(action);
  });
  document.addEventListener('keyup', e => {
    const action = keyAction(e);
    held.delete(e.code);
    if (action) release(action);
  });

  // ------------------------------------------------------------------ system info
  async function refreshSystem() {
    if (document.hidden) return;
    try {
      const res = await fetch('/api/system');
      const { system: s } = await res.json();
      const set = (k, v) => { const el = $(`[data-sys="${k}"]`); if (el) el.textContent = v; };
      set('model', s.model); set('ip', s.ip); set('uptime', s.uptime);
      set('temp', s.temp != null ? s.temp + ' °C' : '–');
      set('cpu', Math.round(s.cpu) + '%'); set('memory', Math.round(s.memory) + '%'); set('storage', s.storage);
      ['cpu', 'memory', 'disk'].forEach(k => { const el = $(`[data-bar="${k}"]`); if (el) el.style.width = s[k] + '%'; });
    } catch (e) { /* offline */ }
  }
  setInterval(refreshSystem, 15000);

  // ------------------------------------------------------------------ PWA
  if ('serviceWorker' in navigator && window.isSecureContext) {
    navigator.serviceWorker.register('/sw.js').catch(err => console.warn('Service worker failed', err));
  }
  // ------------------------------------------------------------------ init
  updateStreamButtons();
  selected = null;
  applyState(state);
})();
