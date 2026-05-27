// =========================================================
// search-tab.jsx — flight search form
// =========================================================

function AirportPicker({ value, onChange, label }) {
  const [open, setOpen] = React.useState(false);
  const [query, setQuery] = React.useState('');
  const ref = React.useRef(null);
  React.useEffect(() => {
    function onDown(e) { if (ref.current && !ref.current.contains(e.target)) setOpen(false); }
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, []);
  const apt = AIRPORT_BY_CODE[value];
  const filtered = AIRPORTS.filter(a => {
    if (!query) return true;
    const q = query.toLowerCase();
    return a.code.toLowerCase().includes(q) || a.city.toLowerCase().includes(q) || a.name.toLowerCase().includes(q);
  });
  const groups = { 'Việt Nam': [], 'Nhật Bản': [] };
  filtered.forEach(a => groups[a.country]?.push(a));

  return (
    <div className={`airport ${open ? 'airport--open' : ''}`} ref={ref} onClick={() => setOpen(true)}>
      <div className="airport__icon">{I.plane()}</div>
      <div className="airport__body">
        <div className="airport__label">{label}</div>
        <div className="airport__code">
          <span>{apt.code}</span>
          <small>{apt.flag} {apt.city} · {apt.name}</small>
        </div>
      </div>
      {open && (
        <div className="airport__menu" onClick={e => e.stopPropagation()}>
          <div className="airport__search">
            <input className="input" autoFocus placeholder="Tìm theo mã / thành phố..." value={query} onChange={e => setQuery(e.target.value)} />
          </div>
          <div className="airport__list">
            {Object.entries(groups).map(([country, list]) => list.length > 0 && (
              <div key={country}>
                <div className="airport__group">{country}</div>
                {list.map(a => (
                  <div key={a.code} className={`airport__opt ${a.code === value ? 'airport__opt--active' : ''}`}
                       onClick={() => { onChange(a.code); setOpen(false); setQuery(''); }}>
                    <span className="airport__opt-flag">{a.flag}</span>
                    <span className="airport__opt-code">{a.code}</span>
                    <span className="airport__opt-name">{a.city} — {a.name}</span>
                  </div>
                ))}
              </div>
            ))}
            {filtered.length === 0 && <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-3)', fontSize: 13 }}>Không tìm thấy sân bay</div>}
          </div>
        </div>
      )}
    </div>
  );
}

function SearchTab({ state, setState, onSearch }) {
  const [pickerOpen, setPickerOpen] = React.useState(null); // 'dep' | 'ret' | null

  function setField(k, v) { setState(s => ({ ...s, [k]: v })); }
  function swap() { setState(s => ({ ...s, origin: s.dest, dest: s.origin })); }

  function fmtRange(from, to) {
    if (!from || !to) return '—';
    const n = daysBetween(from, to);
    return (
      <>
        <span style={{ fontVariantNumeric: 'tabular-nums' }}>{fmtDateVI(from)}</span>
        <span style={{ color: 'var(--text-3)', margin: '0 8px' }}>→</span>
        <span style={{ fontVariantNumeric: 'tabular-nums' }}>{fmtDateVI(to)}</span>
        <span className="daterange__nights">({n} đêm)</span>
      </>
    );
  }

  const isRT = state.tripType === 'RT';

  return (
    <>
      <div className="card">
        <div className="card__head">
          <div>
            <div className="card__title">Tìm chuyến bay rẻ nhất</div>
            <div className="card__sub">Quét giá theo khoảng ngày · Tự động đối chiếu lịch nghỉ VN & Nhật</div>
          </div>
          <div className="seg">
            <button className={`seg__btn ${!isRT ? 'seg__btn--active' : ''}`} onClick={() => setField('tripType', 'OW')}>
              {I.arrow()} Một chiều
            </button>
            <button className={`seg__btn ${isRT ? 'seg__btn--active' : ''}`} onClick={() => setField('tripType', 'RT')}>
              {I.swap()} Khứ hồi
            </button>
          </div>
        </div>

        <div className="card__body">
          {/* Route row */}
          <div className="routerow">
            <AirportPicker value={state.origin} onChange={v => setField('origin', v)} label="Điểm đi" />
            <button className="swap-btn" onClick={swap} aria-label="Đổi chiều" title="Đổi chiều">
              {I.swap()}
            </button>
            <AirportPicker value={state.dest} onChange={v => setField('dest', v)} label="Điểm đến" />
          </div>

          {/* Date row */}
          <div className="mt-4" style={{ display: 'grid', gridTemplateColumns: isRT ? '1fr 1fr' : '1fr', gap: 12 }}>
            <button className="daterange" onClick={() => setPickerOpen('dep')}>
              <div className="daterange__icon">{I.cal()}</div>
              <div className="daterange__body">
                <div className="daterange__label">Khoảng ngày đi</div>
                <div className="daterange__value">{fmtRange(state.depFrom, state.depTo)}</div>
              </div>
              <div style={{ color: 'var(--text-3)' }}>{I.chevR()}</div>
            </button>
            {isRT && (
              <button className="daterange daterange--ret" onClick={() => setPickerOpen('ret')}>
                <div className="daterange__icon">{I.cal()}</div>
                <div className="daterange__body">
                  <div className="daterange__label">Khoảng ngày về</div>
                  <div className="daterange__value">{fmtRange(state.retFrom, state.retTo)}</div>
                </div>
                <div style={{ color: 'var(--text-3)' }}>{I.chevR()}</div>
              </button>
            )}
          </div>

          {/* Options row */}
          <div className="mt-4" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10 }}>
            <div className={`optcard ${state.directOnly ? 'optcard--on' : ''}`} onClick={() => setField('directOnly', !state.directOnly)}>
              <div className="optcard__check">{state.directOnly && I.check()}</div>
              <div className="optcard__body">
                <div className="optcard__title">Bay thẳng</div>
                <div className="optcard__desc">Không quá cảnh / transit</div>
              </div>
            </div>
            <div className="optcard" style={{ cursor: 'default' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, width: '100%' }}>
                <div style={{ flex: 1 }}>
                  <div className="optcard__title">Hành khách</div>
                  <div className="optcard__desc">Người lớn</div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <button className="btn btn--icon" style={{ height: 32, width: 32 }} onClick={(e) => { e.stopPropagation(); setField('pax', Math.max(1, state.pax - 1)); }}>−</button>
                  <span className="mono" style={{ minWidth: 18, textAlign: 'center', fontWeight: 700 }}>{state.pax}</span>
                  <button className="btn btn--icon" style={{ height: 32, width: 32 }} onClick={(e) => { e.stopPropagation(); setField('pax', Math.min(9, state.pax + 1)); }}>+</button>
                </div>
              </div>
            </div>
            <div className={`optcard ${state.autoRefresh ? 'optcard--on' : ''}`} onClick={() => setField('autoRefresh', !state.autoRefresh)}>
              <div className="optcard__check">{state.autoRefresh && I.check()}</div>
              <div className="optcard__body">
                <div className="optcard__title">Tự động làm mới</div>
                <div className="optcard__desc">Mỗi {state.refreshInterval} phút</div>
              </div>
            </div>
          </div>

          {/* Action row */}
          <div className="mt-4" style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <button className="btn btn--primary btn--lg" onClick={onSearch} disabled={state.searching}>
              {state.searching ? <><span className="flyloader__plane">{I.plane()}</span>Đang tìm...</> : <>{I.search()} Tìm giá rẻ nhất</>}
            </button>
            <button className="btn" onClick={() => state.onSaveConfig && state.onSaveConfig()}>
              {I.save()} Lưu cấu hình
            </button>
            {state.searching && (
              <div style={{ flex: 1, minWidth: 220 }}>
                <div className="progress">
                  <div className="progress__fill" style={{ width: `${state.progress}%` }} />
                  <div className="progress__shimmer" />
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-2)', marginTop: 6 }}>
                  Đã quét {state.progressDone}/{state.progressTotal} ngày · {state.progress | 0}%
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tips / info card */}
      <div className="card">
        <div className="card__body" style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>
          <div className="alertcard__icon" style={{ background: 'var(--sky-100)', color: 'var(--sky-700)' }}>{I.info()}</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, color: 'var(--ink-900)', marginBottom: 4 }}>Mẹo tìm vé rẻ</div>
            <div style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.55 }}>
              • Chọn <b>khoảng ngày</b> 10–30 ngày — app sẽ quét song song và tự tìm ngày rẻ nhất.<br/>
              • Tránh các <span style={{ background: 'var(--jp-soft)', color: 'var(--jp-big)', padding: '0 6px', borderRadius: 4, fontWeight: 600 }}>kỳ lễ lớn</span> (Golden Week · Obon · Tết) — giá có thể cao gấp 2-3 lần.<br/>
              • Khứ hồi: chuyển sang tab <b>"Khứ hồi tối ưu"</b> để xem mọi tổ hợp ngày đi–về theo tổng giá.
            </div>
          </div>
        </div>
      </div>

      {pickerOpen === 'dep' && (
        <CalendarPicker
          title="Khoảng ngày đi"
          initialStart={state.depFrom}
          initialEnd={state.depTo}
          onConfirm={(s, e) => { setState(st => ({ ...st, depFrom: s, depTo: e })); setPickerOpen(null); }}
          onClose={() => setPickerOpen(null)}
        />
      )}
      {pickerOpen === 'ret' && (
        <CalendarPicker
          title="Khoảng ngày về"
          initialStart={state.retFrom}
          initialEnd={state.retTo}
          onConfirm={(s, e) => { setState(st => ({ ...st, retFrom: s, retTo: e })); setPickerOpen(null); }}
          onClose={() => setPickerOpen(null)}
        />
      )}
    </>
  );
}

window.SearchTab = SearchTab;
window.AirportPicker = AirportPicker;
