// =========================================================
// calendar.jsx — date range picker modal
// =========================================================

function CalendarPicker({ initialStart, initialEnd, onConfirm, onClose, title = "Chọn khoảng ngày" }) {
  const today = React.useMemo(() => { const d = new Date(); d.setHours(0,0,0,0); return d; }, []);
  const [start, setStart] = React.useState(initialStart ? new Date(initialStart) : null);
  const [end,   setEnd]   = React.useState(initialEnd   ? new Date(initialEnd)   : null);
  const [hover, setHover] = React.useState(null);
  const [phase, setPhase] = React.useState(start ? (end ? 2 : 1) : 0);
  const [view, setView]   = React.useState(() => {
    const ref = start || today;
    return new Date(ref.getFullYear(), ref.getMonth(), 1);
  });
  const [showVN, setShowVN] = React.useState(true);
  const [showJP, setShowJP] = React.useState(true);
  const [showBig, setShowBig] = React.useState(true);
  const [hoverInfo, setHoverInfo] = React.useState('');

  const monthName = ['Tháng 1','Tháng 2','Tháng 3','Tháng 4','Tháng 5','Tháng 6','Tháng 7','Tháng 8','Tháng 9','Tháng 10','Tháng 11','Tháng 12'];

  function pickDate(d) {
    if (d < today) return;
    if (phase === 0 || phase === 2) {
      setStart(d); setEnd(null); setPhase(1);
    } else {
      if (d < start) { setEnd(start); setStart(d); }
      else { setEnd(d); }
      setPhase(2);
    }
  }

  function classifyCell(d) {
    const past = d < today;
    const isToday = d.getTime() === today.getTime();
    const isStart = start && d.getTime() === start.getTime();
    const isEnd   = end   && d.getTime() === end.getTime();
    const inRange = start && end && d > start && d < end;
    const preview = phase === 1 && hover && start && !inRange && d > Math.min(start, hover) && d < Math.max(start, hover);
    const previewStart = phase === 1 && hover && start && hover < start && d.getTime() === hover.getTime();

    let hol = null;
    if (showBig) { const t = HolidayData.jpBig(d); if (t) hol = { cls: 'big', text: t }; }
    if (!hol && showJP) { const t = HolidayData.jpHoliday(d); if (t) hol = { cls: 'jp', text: t }; }
    if (!hol && showVN) { const t = HolidayData.vnHoliday(d); if (t) hol = { cls: 'vn', text: t }; }

    return { past, isToday, isStart, isEnd, inRange, preview, previewStart, hol };
  }

  function renderMonth(year, month, navDir) {
    const firstDay = new Date(year, month, 1);
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    // Mon-first
    let startCol = firstDay.getDay() - 1; if (startCol < 0) startCol = 6;
    const cells = [];
    for (let i = 0; i < startCol; i++) cells.push(null);
    for (let d = 1; d <= daysInMonth; d++) cells.push(new Date(year, month, d));
    while (cells.length < 42) cells.push(null);

    return (
      <div className="cal__month">
        <div className="cal__month-hdr">
          {navDir === 'left'
            ? <button className="cal__nav" onClick={() => setView(new Date(view.getFullYear(), view.getMonth() - 1, 1))} aria-label="Trước">{I.chevL()}</button>
            : <div style={{ width: 28 }} />}
          <div>{monthName[month]} {year}</div>
          {navDir === 'right'
            ? <button className="cal__nav" onClick={() => setView(new Date(view.getFullYear(), view.getMonth() + 1, 1))} aria-label="Sau">{I.chevR()}</button>
            : <div style={{ width: 28 }} />}
        </div>
        <div className="cal__grid">
          {['T2','T3','T4','T5','T6','T7','CN'].map((d, i) => (
            <div key={d} className={`cal__dow ${i === 6 ? 'cal__dow--sun' : ''}`}>{d}</div>
          ))}
          {cells.map((d, i) => {
            if (!d) return <div key={i} />;
            const c = classifyCell(d);
            const isSun = d.getDay() === 0;
            const isSel = c.isStart || c.isEnd;
            const isRange = c.inRange || c.preview;
            const cls = [
              'cal__cell',
              isSun ? 'cal__cell--sun' : '',
              c.past ? 'cal__cell--past' : '',
              c.isToday ? 'cal__cell--today' : '',
              isSel ? 'cal__cell--sel' : '',
              isRange ? 'cal__cell--range' : '',
              c.isStart && end ? 'cal__cell--range-start' : '',
              c.isEnd ? 'cal__cell--range-end' : '',
              !isSel && !isRange && c.hol ? `cal__cell--hol-${c.hol.cls}` : '',
            ].filter(Boolean).join(' ');
            return (
              <button
                key={i}
                className={cls}
                disabled={c.past}
                onMouseEnter={() => { setHover(d); setHoverInfo(c.hol ? c.hol.text : ''); }}
                onMouseLeave={() => { setHover(null); setHoverInfo(''); }}
                onClick={() => pickDate(d)}
              >
                {d.getDate()}
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  function instr() {
    if (phase === 0) return 'Chọn ngày bắt đầu';
    if (phase === 1) return 'Chọn ngày kết thúc';
    return 'Khoảng đã chọn';
  }
  function rangeLabel() {
    if (start && end) {
      const n = daysBetween(start, end);
      return <span>{fmtDateVI(start)} <small>→</small> {fmtDateVI(end)} <small>({n} đêm)</small></span>;
    }
    if (start) return <span>{fmtDateVI(start)} <small>→ ?</small></span>;
    return <span style={{ opacity: .7 }}>Chưa chọn</span>;
  }

  function handleConfirm() {
    if (start && end) onConfirm(ymd(start), ymd(end));
    else if (start)   onConfirm(ymd(start), ymd(start));
    else onClose();
  }

  // Quick presets
  const presets = [
    { label: 'Tuần tới', s: 7, e: 14 },
    { label: '2 tuần tới', s: 7, e: 21 },
    { label: 'Tháng tới', s: 14, e: 44 },
    { label: 'Cuối tuần này', s: ((6 - today.getDay() + 7) % 7) || 7, e: ((7 - today.getDay() + 7) % 7) || 7 },
  ];
  function applyPreset(p) {
    const s = addDays(today, p.s);
    const e = addDays(today, p.e);
    setStart(s); setEnd(e); setPhase(2);
    setView(new Date(s.getFullYear(), s.getMonth(), 1));
  }

  const monthRight = new Date(view.getFullYear(), view.getMonth() + 1, 1);

  return (
    <div className="cal__overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="cal" role="dialog" aria-modal="true">
        <div className="cal__hdr">
          <div>
            <div className="cal__hdr-instr">✈  {title}</div>
            <div className="cal__hdr-instr" style={{ opacity: 1, marginTop: 4, fontWeight: 600 }}>{instr()}</div>
          </div>
          <div className="cal__hdr-range">{rangeLabel()}</div>
        </div>

        <div className="cal__opts">
          <span style={{ fontWeight: 700, color: 'var(--text-2)' }}>Lịch nghỉ:</span>
          <label className="cal__opt"><input type="checkbox" checked={showBig} onChange={e => setShowBig(e.target.checked)} /><span className="cal__opt-sw" style={{ background: 'var(--jp-big)' }} />3 kỳ lớn Nhật (GW · Obon · Tết JP)</label>
          <label className="cal__opt"><input type="checkbox" checked={showJP}  onChange={e => setShowJP(e.target.checked)} /><span className="cal__opt-sw" style={{ background: 'var(--jp-soft)' }} />Lễ Nhật</label>
          <label className="cal__opt"><input type="checkbox" checked={showVN}  onChange={e => setShowVN(e.target.checked)} /><span className="cal__opt-sw" style={{ background: 'var(--vn-soft)' }} />Lễ VN</label>

          <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
            {presets.map(p => (
              <button key={p.label} className="btn btn--ghost" style={{ height: 28, padding: '0 10px', fontSize: 12 }} onClick={() => applyPreset(p)}>{p.label}</button>
            ))}
          </div>
        </div>

        <div className="cal__body">
          {renderMonth(view.getFullYear(), view.getMonth(), 'left')}
          {renderMonth(monthRight.getFullYear(), monthRight.getMonth(), 'right')}
        </div>

        <div className="cal__legend">
          <span><span className="cal__legend-sw" style={{ background: 'var(--sky-600)' }} />Ngày chọn</span>
          <span><span className="cal__legend-sw" style={{ background: 'var(--sky-100)' }} />Khoảng chọn</span>
          <span><span className="cal__legend-sw" style={{ background: 'var(--jp-big)' }} />Kỳ lớn JP</span>
          <span><span className="cal__legend-sw" style={{ background: 'var(--jp-soft)' }} />Lễ JP</span>
          <span><span className="cal__legend-sw" style={{ background: 'var(--vn-soft)' }} />Lễ VN</span>
          <span><span className="cal__legend-sw" style={{ background: 'transparent', boxShadow: 'inset 0 0 0 1.5px var(--sky-500)' }} />Hôm nay</span>
        </div>

        <div className="cal__foot">
          <div className="cal__hover-info">{hoverInfo}</div>
          <button className="btn btn--ghost" onClick={() => { setStart(null); setEnd(null); setPhase(0); }}>Xóa chọn</button>
          <button className="btn" onClick={onClose}>Hủy</button>
          <button className="btn btn--primary" onClick={handleConfirm} disabled={!start}>Xác nhận</button>
        </div>
      </div>
    </div>
  );
}

window.CalendarPicker = CalendarPicker;
