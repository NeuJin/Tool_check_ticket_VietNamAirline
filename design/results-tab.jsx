// =========================================================
// results-tab.jsx — flight results with price chart
// =========================================================

function PriceChart({ data, currency, rate, onSelectDate, selectedDate }) {
  // data: array of { date, price (vnd), hasFlights }
  const [hoverIdx, setHoverIdx] = React.useState(null);
  if (!data || data.length === 0) return null;

  const prices = data.filter(d => d.price > 0).map(d => d.price);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;

  const W = 1000, H = 200, PAD = { t: 16, r: 16, b: 36, l: 8 };
  const innerW = W - PAD.l - PAD.r;
  const innerH = H - PAD.t - PAD.b;
  const barW = innerW / data.length;

  return (
    <div className="chart" style={{ position: 'relative' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16 }}>
        <div>
          <div className="chart__title">Xu hướng giá theo ngày</div>
          <div className="chart__sub">Click vào cột để xem các chuyến bay ngày đó</div>
        </div>
        <div style={{ display: 'flex', gap: 14, fontSize: 12, color: 'var(--text-2)' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><span style={{ width: 12, height: 12, borderRadius: 3, background: 'var(--good)' }} />Rẻ nhất</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><span style={{ width: 12, height: 12, borderRadius: 3, background: 'var(--sky-400)' }} />Trung bình</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><span style={{ width: 12, height: 12, borderRadius: 3, background: 'var(--warn)' }} />Đắt</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><span style={{ width: 12, height: 12, borderRadius: 3, background: 'var(--surface-2)', border: '1px dashed var(--line-2)' }} />Hết vé</span>
        </div>
      </div>
      <svg className="chart__svg" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
        {/* baseline */}
        <line x1={PAD.l} x2={W - PAD.r} y1={H - PAD.b + 1} y2={H - PAD.b + 1} stroke="var(--line)" strokeWidth="1" />
        {/* avg line */}
        {(() => {
          const avg = prices.reduce((a, b) => a + b, 0) / prices.length;
          const y = PAD.t + innerH - ((avg - min) / range) * innerH;
          return <>
            <line x1={PAD.l} x2={W - PAD.r} y1={y} y2={y} stroke="var(--sky-300)" strokeWidth="1" strokeDasharray="4 4" />
            <text x={W - PAD.r - 6} y={y - 4} fontSize="11" fill="var(--sky-700)" textAnchor="end" fontFamily="JetBrains Mono">
              TB {fmtPriceCompact(avg, currency, rate)}
            </text>
          </>;
        })()}
        {data.map((d, i) => {
          const x = PAD.l + i * barW;
          let h, color;
          if (d.price > 0) {
            const norm = (d.price - min) / range;
            h = Math.max(8, innerH * (0.15 + norm * 0.85));
            if (norm < 0.25) color = 'var(--good)';
            else if (norm > 0.75) color = 'var(--warn)';
            else color = 'var(--sky-400)';
          } else {
            h = 6; color = 'var(--line)';
          }
          const y = PAD.t + innerH - h;
          const isSel = d.date === selectedDate;
          const isHov = i === hoverIdx;
          const dt = new Date(d.date);
          const hol = holidayTag(dt);
          return (
            <g key={d.date}>
              {isSel && (
                <rect x={x} y={PAD.t} width={barW} height={innerH} fill="var(--sky-100)" />
              )}
              <rect
                className="chart__bar"
                x={x + barW * 0.15}
                y={y}
                width={barW * 0.7}
                height={h}
                fill={d.price > 0 ? color : 'transparent'}
                stroke={d.price > 0 ? 'none' : 'var(--line-2)'}
                strokeDasharray={d.price > 0 ? '0' : '3 3'}
                rx="3"
                style={{ opacity: isHov ? 0.85 : 1, filter: isSel ? `drop-shadow(0 2px 6px ${color}80)` : 'none' }}
                onMouseEnter={() => setHoverIdx(i)}
                onMouseLeave={() => setHoverIdx(null)}
                onClick={() => d.price > 0 && onSelectDate && onSelectDate(d.date)}
              />
              {hol && (
                <circle cx={x + barW / 2} cy={H - PAD.b + 14} r="3" fill={hol.cls === 'big' ? 'var(--jp-big)' : hol.cls === 'jp' ? 'var(--warn)' : 'var(--bad)'} />
              )}
              {/* Day labels — every 3rd day */}
              {i % Math.max(1, (data.length / 14) | 0) === 0 && (
                <text x={x + barW / 2} y={H - PAD.b + 26} fontSize="10" fill="var(--text-3)" textAnchor="middle" fontFamily="JetBrains Mono">
                  {dt.getDate()}/{dt.getMonth() + 1}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      {hoverIdx !== null && (() => {
        const d = data[hoverIdx];
        const left = PAD.l + (hoverIdx + 0.5) * barW;
        const dt = new Date(d.date);
        const hol = holidayTag(dt);
        return (
          <div className="chart__tooltip" style={{ left: `${(left / W) * 100}%`, top: 90 }}>
            <div style={{ fontFamily: 'JetBrains Mono', fontSize: 11, opacity: .8, marginBottom: 2 }}>{fmtDay(dt)} · {fmtDateShort(dt)}</div>
            <div>{d.price > 0 ? fmtPrice(d.price, currency, rate) : 'Không có chuyến'}</div>
            {hol && <div style={{ fontSize: 11, opacity: .85, marginTop: 4 }}>{hol.text}</div>}
          </div>
        );
      })()}
    </div>
  );
}

function fmtPriceCompact(vnd, currency, rate = 165) {
  if (vnd == null) return '—';
  if (currency === 'JPY') return '¥' + ((vnd / rate / 1000) | 0) + 'k';
  if (vnd >= 1000000) return (vnd / 1000000).toFixed(1).replace(/\.0$/, '') + 'M ₫';
  return ((vnd / 1000) | 0) + 'k ₫';
}

function FlightRow({ flight, currency, rate, badge, onClick, isSelected }) {
  if (!flight) {
    return null;
  }
  if (flight.empty) {
    return (
      <div className="flightrow flightrow--none">
        <div className="flightrow__date">
          {fmtDateShort(flight.date)}
          <small>{fmtDay(flight.date)}</small>
        </div>
        <div style={{ color: 'var(--text-3)', fontStyle: 'italic', fontSize: 13 }}>Không có chuyến trong ngày này</div>
        <div /><div /><div /><div />
      </div>
    );
  }
  const dt = new Date(flight.date);
  const hol = holidayTag(dt);
  const cls = ['flightrow', badge === 'best' ? 'flightrow--best' : badge === 'cheap' ? 'flightrow--cheap' : badge === 'mid' ? 'flightrow--mid' : '', isSelected ? 'flightrow--best' : ''].filter(Boolean).join(' ');
  return (
    <div className={cls} onClick={onClick}>
      <div className="flightrow__date">
        {fmtDateShort(flight.date)}
        <small>{fmtDay(flight.date)} · {flight.date.slice(0, 4)}</small>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
          {badge === 'best' && <span className="tag tag--best"><span>{I.star()}</span>Rẻ nhất</span>}
          {badge === 'cheap' && <span className="tag tag--cheap">Giá tốt</span>}
          {badge === 'mid' && <span className="tag tag--mid">Trung bình</span>}
          {flight.stops === 0 && <span className="tag tag--direct">Bay thẳng</span>}
          {hol && <span className={`tag ${hol.cls === 'vn' ? 'tag--hol' : 'tag--jp'}`}>{hol.text.slice(0, 28)}</span>}
        </div>
      </div>
      <div className="flightrow__stops">{flight.stops === 0 ? 'Trực tiếp' : `${flight.stops} điểm dừng`}</div>
      <div className="flightrow__flight">{flight.flightNum}</div>
      <div className="flightrow__dep">
        {flight.depTime} <span style={{ color: 'var(--text-3)' }}>→</span> {flight.arrTime}
        <div className="flightrow__dur" style={{ fontSize: 11, marginTop: 2 }}>{fmtDuration(flight.durationMin)}</div>
      </div>
      <div className="flightrow__price" style={{ textAlign: 'right' }}>
        {fmtPriceCompact(flight.price, currency, rate)}
        <small>{currency === 'JPY' ? fmtVND(flight.price) : `¥${((flight.price / rate / 1000) | 0)}k`}</small>
      </div>
    </div>
  );
}

function ResultsTab({ state, setState, onSearch }) {
  const { outResults, retResults, currency, exchangeRate, searching, lastSearch } = state;

  // Choose which leg to display
  const [activeLeg, setActiveLeg] = React.useState('out');
  const isRT = state.tripType === 'RT';
  const results = (activeLeg === 'ret' && isRT) ? retResults : outResults;

  // Selected date for table emphasis
  const [selectedDate, setSelectedDate] = React.useState(null);

  // Aggregated chart data
  const chartData = React.useMemo(() => {
    if (!results) return [];
    return Object.entries(results)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, flights]) => ({
        date,
        price: (flights && flights.length > 0) ? flights[0].price : 0,
        hasFlights: !!(flights && flights.length > 0),
      }));
  }, [results]);

  // Best per leg
  const allOut = outResults ? Object.values(outResults).flat() : [];
  const allRet = retResults ? Object.values(retResults).flat() : [];
  const bestOut = allOut.length > 0 ? allOut.reduce((m, f) => !m || f.price < m.price ? f : m, null) : null;
  const bestRet = allRet.length > 0 ? allRet.reduce((m, f) => !m || f.price < m.price ? f : m, null) : null;
  const totalBest = isRT ? (bestOut && bestRet ? bestOut.price + bestRet.price : null) : (bestOut ? bestOut.price : null);

  // Table rows — one per date, showing cheapest flight that day
  const rows = React.useMemo(() => {
    if (!results) return [];
    return Object.entries(results)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, flights]) => {
        if (!flights || flights.length === 0) return { date, empty: true };
        return flights[0];
      });
  }, [results]);

  const allPrices = rows.filter(r => !r.empty).map(r => r.price);
  const minPrice = allPrices.length ? Math.min(...allPrices) : 0;
  const maxPrice = allPrices.length ? Math.max(...allPrices) : 0;
  function badge(f) {
    if (f.empty) return null;
    if (f.price === minPrice) return 'best';
    const norm = (f.price - minPrice) / Math.max(1, maxPrice - minPrice);
    if (norm < 0.3) return 'cheap';
    if (norm > 0.75) return 'mid';
    return null;
  }

  if (!results || Object.keys(results).length === 0) {
    return (
      <div className="card">
        <div className="card__body" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <div style={{ fontSize: 48, marginBottom: 12, opacity: .3 }}>✈</div>
          <div style={{ fontWeight: 700, color: 'var(--ink-900)', fontSize: 18 }}>Chưa có kết quả</div>
          <div style={{ color: 'var(--text-2)', marginTop: 6 }}>Sang tab <b>Tìm chuyến bay</b> để bắt đầu quét giá theo khoảng ngày.</div>
          <button className="btn btn--primary" style={{ marginTop: 18 }} onClick={() => setState(s => ({ ...s, activeTab: 'search' }))}>
            {I.search()} Đi tới tìm kiếm
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Top summary KPIs */}
      <div className="kpi-grid">
        <div className="kpi kpi--best">
          <div className="kpi__label">Giá rẻ nhất chuyến đi</div>
          <div className="kpi__value">{fmtPriceCompact(bestOut?.price, currency, exchangeRate)}</div>
          <div className="kpi__sub">{bestOut ? `${fmtDateShort(bestOut.date)} · ${bestOut.flightNum}` : '—'}</div>
        </div>
        {isRT && (
          <div className="kpi">
            <div className="kpi__label">Rẻ nhất chuyến về</div>
            <div className="kpi__value">{fmtPriceCompact(bestRet?.price, currency, exchangeRate)}</div>
            <div className="kpi__sub">{bestRet ? `${fmtDateShort(bestRet.date)} · ${bestRet.flightNum}` : '—'}</div>
          </div>
        )}
        <div className="kpi kpi--total">
          <div className="kpi__label">{isRT ? 'Tổng cộng' : 'Một chiều'}</div>
          <div className="kpi__value">{fmtPriceCompact(totalBest, currency, exchangeRate)}</div>
          <div className="kpi__sub">{state.pax} hành khách</div>
        </div>
        <div className="kpi">
          <div className="kpi__label">Đã quét</div>
          <div className="kpi__value">{Object.keys(results).length}</div>
          <div className="kpi__sub">ngày · {allOut.length + allRet.length} chuyến</div>
        </div>
      </div>

      {/* Currency toggle + actions */}
      <div className="card">
        <div className="card__body" style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap', padding: '14px 22px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-2)' }}>Đơn vị:</span>
            <div className="seg">
              {['VND', 'JPY', 'BOTH'].map(c => (
                <button key={c} className={`seg__btn ${currency === c ? 'seg__btn--active' : ''}`} onClick={() => setState(s => ({ ...s, currency: c }))}>
                  {c === 'BOTH' ? 'Cả hai' : c}
                </button>
              ))}
            </div>
          </div>
          <div className="statuspill">
            <span style={{ color: 'var(--sky-700)' }}>{I.refresh()}</span>
            <span>1 JPY ≈ <b className="mono">{exchangeRate.toFixed(1)}</b> ₫</span>
          </div>
          {isRT && (
            <div className="seg" style={{ marginLeft: 'auto' }}>
              <button className={`seg__btn ${activeLeg === 'out' ? 'seg__btn--active' : ''}`} onClick={() => setActiveLeg('out')}>
                {I.arrow()} Chuyến đi
              </button>
              <button className={`seg__btn ${activeLeg === 'ret' ? 'seg__btn--active' : ''}`} onClick={() => setActiveLeg('ret')}>
                {I.arrow()} Chuyến về
              </button>
            </div>
          )}
          <button className="btn" onClick={() => onSearch && onSearch()}>{I.refresh()} Quét lại</button>
        </div>
      </div>

      {/* Price chart */}
      <PriceChart data={chartData} currency={currency} rate={exchangeRate} onSelectDate={setSelectedDate} selectedDate={selectedDate} />

      {/* Flight table */}
      <div className="card">
        <div className="card__head">
          <div>
            <div className="card__title">
              {activeLeg === 'ret' ? 'Chuyến về' : 'Chuyến đi'} — {state.origin} → {state.dest}
            </div>
            <div className="card__sub">Hiển thị chuyến rẻ nhất mỗi ngày · Click để xem chi tiết</div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn">{I.copy()} Sao chép</button>
            <button className="btn">{I.bell()} Thêm vào theo dõi</button>
          </div>
        </div>
        <div className="card__body">
          <div className="flighttable">
            {rows.map((r, i) => (
              <FlightRow
                key={r.date + i}
                flight={r}
                currency={currency}
                rate={exchangeRate}
                badge={badge(r)}
                isSelected={selectedDate === r.date}
                onClick={() => !r.empty && setSelectedDate(r.date)}
              />
            ))}
            {rows.length === 0 && (
              <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-3)' }}>Không có dữ liệu</div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

window.ResultsTab = ResultsTab;
window.PriceChart = PriceChart;
window.fmtPriceCompact = fmtPriceCompact;
