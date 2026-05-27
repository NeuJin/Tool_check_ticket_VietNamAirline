// =========================================================
// app.jsx — main App with tabs, state, and tweaks
// =========================================================

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "accent": "#0EA5E9",
  "fontScale": 1,
  "showHolidayDots": true,
  "denseRows": false
}/*EDITMODE-END*/;

function todayPlus(days) {
  const d = new Date(); d.setHours(0,0,0,0);
  d.setDate(d.getDate() + days);
  return ymd(d);
}

function App() {
  const [activeTab, setActiveTab] = React.useState('search');
  const [tweaks, setTweak] = useTweaks(TWEAK_DEFAULTS);

  // Master state for the app
  const [state, _setState] = React.useState({
    // search form
    origin: 'HAN',
    dest: 'NRT',
    tripType: 'RT',
    depFrom: todayPlus(14),
    depTo: todayPlus(44),
    retFrom: todayPlus(21),
    retTo: todayPlus(60),
    directOnly: false,
    pax: 1,
    autoRefresh: false,
    refreshInterval: 15,

    // results
    outResults: null,
    retResults: null,
    currency: 'VND',
    exchangeRate: 168.5,
    fallbackRate: 165,
    searching: false,
    progress: 0,
    progressDone: 0,
    progressTotal: 0,
    lastSearch: null,

    // combo
    minLayover: 5,
    maxLayover: 21,
    layoverUnit: 'days',

    // monitor
    monitorOn: false,
    monitorInterval: 60,
    notifyInterval: 120,
    notifyDrop: true,
    notifyPeriodic: true,
    alerts: [
      { id: 1, kind: 'good', title: 'Giá giảm 12% trên tuyến HAN → NRT',
        body: 'Từ 11.200.000 ₫ xuống còn 9.850.000 ₫ cho ngày 14/06/2026 · VN300',
        time: '2 phút trước' },
      { id: 2, kind: 'info', title: 'Báo cáo định kỳ — HAN ↔ SGN',
        body: 'Giá thấp nhất tuần này: 1.380.000 ₫ (Thứ 3, 19/05)',
        time: '34 phút trước' },
      { id: 3, kind: 'good', title: 'Vé khứ hồi tốt — HAN ⇄ KIX',
        body: 'Tổng 18.450.000 ₫ · 10 đêm · Tránh được kỳ Obon',
        time: '1 giờ trước' },
    ],

    // settings
    apiType: 'vna_direct',
    xdToken: '',
    amadeusId: '',
    amadeusSecret: '',
    kiwiKey: '',

    // saved searches
    savedSearches: [
      { id: 'cfg1', name: 'Tết về quê HCM', active: true, lastPrice: 1850000,
        cfg: { origin: 'HAN', dest: 'SGN', tripType: 'OW',
               depFrom: todayPlus(10), depTo: todayPlus(25), retFrom: todayPlus(15), retTo: todayPlus(30), directOnly: true } },
      { id: 'cfg2', name: 'Du lịch Tokyo mùa hoa anh đào', active: true, lastPrice: 22400000,
        cfg: { origin: 'HAN', dest: 'NRT', tripType: 'RT',
               depFrom: '2026-03-25', depTo: '2026-04-05', retFrom: '2026-04-02', retTo: '2026-04-12', directOnly: false } },
      { id: 'cfg3', name: 'Công tác Osaka', active: false, lastPrice: 18900000,
        cfg: { origin: 'SGN', dest: 'KIX', tripType: 'RT',
               depFrom: todayPlus(30), depTo: todayPlus(40), retFrom: todayPlus(45), retTo: todayPlus(55), directOnly: true } },
      { id: 'cfg4', name: 'Phú Quốc nghỉ dưỡng', active: true, lastPrice: 1620000,
        cfg: { origin: 'HAN', dest: 'PQC', tripType: 'OW',
               depFrom: todayPlus(20), depTo: todayPlus(50), retFrom: todayPlus(25), retTo: todayPlus(55), directOnly: false } },
    ],

    activeTab: 'search',
  });

  const setState = React.useCallback((updater) => {
    if (typeof updater === 'function') _setState(updater);
    else _setState(s => ({ ...s, ...updater }));
  }, []);

  // Sync activeTab into state for cross-tab nav
  React.useEffect(() => { setState(s => ({ ...s, activeTab })); }, [activeTab, setState]);
  React.useEffect(() => { if (state.activeTab !== activeTab) setActiveTab(state.activeTab); }, [state.activeTab]);

  // Apply tweaks to root CSS vars
  React.useEffect(() => {
    const root = document.documentElement;
    // Re-derive a palette from a base hex by shifting lightness with HSL
    function adjust(hex, lightDelta) {
      const r = parseInt(hex.slice(1, 3), 16) / 255;
      const g = parseInt(hex.slice(3, 5), 16) / 255;
      const b = parseInt(hex.slice(5, 7), 16) / 255;
      const max = Math.max(r, g, b), min = Math.min(r, g, b);
      let h = 0, s = 0, l = (max + min) / 2;
      if (max !== min) {
        const d = max - min;
        s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
        switch (max) {
          case r: h = (g - b) / d + (g < b ? 6 : 0); break;
          case g: h = (b - r) / d + 2; break;
          case b: h = (r - g) / d + 4; break;
        }
        h /= 6;
      }
      l = Math.max(0, Math.min(1, l + lightDelta));
      function hue2rgb(p, q, t) {
        if (t < 0) t += 1; if (t > 1) t -= 1;
        if (t < 1/6) return p + (q - p) * 6 * t;
        if (t < 1/2) return q;
        if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
        return p;
      }
      const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
      const p = 2 * l - q;
      const rr = Math.round(hue2rgb(p, q, h + 1/3) * 255);
      const gg = Math.round(hue2rgb(p, q, h) * 255);
      const bb = Math.round(hue2rgb(p, q, h - 1/3) * 255);
      return '#' + [rr, gg, bb].map(x => x.toString(16).padStart(2, '0')).join('');
    }
    const base = tweaks.accent || '#0EA5E9';
    root.style.setProperty('--sky-500', base);
    root.style.setProperty('--sky-400', adjust(base, 0.08));
    root.style.setProperty('--sky-600', adjust(base, -0.06));
    root.style.setProperty('--sky-700', adjust(base, -0.14));
    root.style.setProperty('--sky-100', adjust(base, 0.42));
    root.style.setProperty('--sky-50',  adjust(base, 0.48));
    root.style.fontSize = (15 * (tweaks.fontScale || 1)) + 'px';
  }, [tweaks.accent, tweaks.fontScale]);

  // ── Search execution (simulated) ────────────────────────────────────────
  const searchRef = React.useRef(0);
  async function doSearch() {
    const myId = searchRef.current + 1;
    searchRef.current = myId;
    setState({ searching: true, progress: 0, progressDone: 0, progressTotal: 0, outResults: null, retResults: null });

    const depDays = daysBetween(state.depFrom, state.depTo) + 1;
    const retDays = state.tripType === 'RT' ? daysBetween(state.retFrom, state.retTo) + 1 : 0;
    const total = Math.max(1, depDays + retDays);
    setState({ progressTotal: total });

    const out = mockRangeResults(state.origin, state.dest, state.depFrom, state.depTo, state.directOnly);
    const ret = state.tripType === 'RT' ? mockRangeResults(state.dest, state.origin, state.retFrom, state.retTo, state.directOnly) : null;

    for (let i = 1; i <= total; i++) {
      await new Promise(r => setTimeout(r, 15 + Math.random() * 25));
      if (searchRef.current !== myId) return;
      setState(s => ({ ...s, progressDone: i, progress: (i / total) * 100 }));
    }

    setState({
      outResults: out,
      retResults: ret,
      searching: false,
      progress: 100,
      lastSearch: new Date().toISOString(),
      activeTab: 'results',
    });
    setActiveTab('results');
  }

  function saveConfig() {
    const name = prompt('Đặt tên cho cấu hình:', `${state.origin}→${state.dest} · ${fmtDateShort(state.depFrom)}`);
    if (!name) return;
    const id = 'cfg' + Date.now();
    setState(s => ({
      ...s,
      savedSearches: [
        ...s.savedSearches,
        {
          id, name, active: false, lastPrice: null,
          cfg: {
            origin: s.origin, dest: s.dest, tripType: s.tripType,
            depFrom: s.depFrom, depTo: s.depTo, retFrom: s.retFrom, retTo: s.retTo,
            directOnly: s.directOnly,
          },
        }
      ],
    }));
  }

  const searchStateWithSave = { ...state, onSaveConfig: saveConfig };

  const tabs = [
    { id: 'search',  label: 'Tìm chuyến bay', icon: I.search },
    { id: 'results', label: 'Kết quả giá',    icon: I.list },
    { id: 'combo',   label: 'Khứ hồi tối ưu', icon: I.combo },
    { id: 'monitor', label: 'Theo dõi giá',   icon: I.bell },
    { id: 'settings',label: 'Cài đặt',        icon: I.settings },
  ];

  return (
    <div className="app" data-screen-label="VNA Flight Check">
      <header className="appbar">
        <div className="appbar__inner">
          <div className="brand">
            <div className="brand__mark">{I.plane()}</div>
            <div className="brand__title">
              VNA Flight Check
              <small>Theo dõi & săn vé rẻ</small>
            </div>
          </div>
          <nav className="nav" role="tablist">
            {tabs.map(t => (
              <button
                key={t.id}
                className={`nav__btn ${activeTab === t.id ? 'nav__btn--active' : ''}`}
                onClick={() => setActiveTab(t.id)}
                role="tab"
                aria-selected={activeTab === t.id}
              >
                {t.icon()}
                <span>{t.label}</span>
              </button>
            ))}
          </nav>
          <div className="statuspill" title="Trạng thái app">
            <span className={`statuspill__dot ${state.searching ? 'statuspill__dot--warn' : state.monitorOn ? '' : ''}`} />
            <span>{state.searching ? 'Đang quét...' : state.monitorOn ? 'Theo dõi bật' : 'Sẵn sàng'}</span>
          </div>
        </div>
      </header>

      <main className="main">
        {activeTab === 'search'   && <SearchTab state={searchStateWithSave} setState={setState} onSearch={doSearch} />}
        {activeTab === 'results'  && <ResultsTab state={state} setState={setState} onSearch={doSearch} />}
        {activeTab === 'combo'    && <ComboTab state={state} setState={setState} />}
        {activeTab === 'monitor'  && <MonitorTab state={state} setState={setState} />}
        {activeTab === 'settings' && <SettingsTab state={state} setState={setState} />}
      </main>

      <TweaksPanel title="Tweaks">
        <TweakSection label="Màu chủ đạo" />
        <TweakColor
          label="Accent"
          value={tweaks.accent}
          options={['#0EA5E9', '#3D5A99', '#14B8A6', '#F97316', '#9333EA']}
          onChange={(v) => setTweak('accent', v)}
        />
        <TweakSection label="Hiển thị" />
        <TweakSlider
          label="Cỡ chữ"
          value={tweaks.fontScale}
          min={0.85} max={1.2} step={0.05}
          unit="×"
          onChange={(v) => setTweak('fontScale', v)}
        />
        <TweakToggle
          label="Chấm lễ trên biểu đồ"
          value={tweaks.showHolidayDots}
          onChange={(v) => setTweak('showHolidayDots', v)}
        />
        <TweakToggle
          label="Hàng dày đặc"
          value={tweaks.denseRows}
          onChange={(v) => setTweak('denseRows', v)}
        />
      </TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
