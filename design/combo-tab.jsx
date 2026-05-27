// =========================================================
// combo-tab.jsx — round-trip optimizer
// =========================================================

function ComboTab({ state, setState }) {
  const { outResults, retResults, currency, exchangeRate, tripType } = state;
  const [minLay, setMinLay] = React.useState(state.minLayover || 3);
  const [maxLay, setMaxLay] = React.useState(state.maxLayover || 14);
  const [unit, setUnit] = React.useState(state.layoverUnit || 'days'); // 'days'|'hours'
  const [sortBy, setSortBy] = React.useState('total'); // 'total'|'date'|'nights'

  if (tripType !== 'RT' || !outResults || !retResults) {
    return (
      <div className="card">
        <div className="card__body" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <div style={{ fontSize: 48, marginBottom: 12, opacity: .3 }}>↻</div>
          <div style={{ fontWeight: 700, color: 'var(--ink-900)', fontSize: 18 }}>Cần tìm khứ hồi trước</div>
          <div style={{ color: 'var(--text-2)', marginTop: 6 }}>Chuyển sang chế độ <b>Khứ hồi</b> ở tab Tìm chuyến bay và quét cả chuyến đi & về.</div>
          <button className="btn btn--primary" style={{ marginTop: 18 }} onClick={() => setState(s => ({ ...s, activeTab: 'search', tripType: 'RT' }))}>
            {I.search()} Đi tới tìm kiếm
          </button>
        </div>
      </div>
    );
  }

  // Compute all combinations
  const combos = React.useMemo(() => {
    const list = [];
    Object.entries(outResults).forEach(([dOut, flightsOut]) => {
      if (!flightsOut || flightsOut.length === 0) return;
      const bestOut = flightsOut[0];
      Object.entries(retResults).forEach(([dRet, flightsRet]) => {
        if (!flightsRet || flightsRet.length === 0) return;
        if (dRet <= dOut) return; // return must be after departure
        const bestRet = flightsRet[0];
        const nights = daysBetween(dOut, dRet);
        // Filter by layover (in days). If 'hours', we treat min as hours.
        if (unit === 'days') {
          if (nights < minLay || nights > maxLay) return;
        } else {
          // hours — convert nights to hours roughly (assume noon departure)
          const hours = nights * 24;
          if (hours < minLay || hours > maxLay) return;
        }
        list.push({
          dOut, dRet, nights,
          outFlight: bestOut, retFlight: bestRet,
          total: bestOut.price + bestRet.price,
        });
      });
    });
    if (sortBy === 'total') list.sort((a, b) => a.total - b.total);
    else if (sortBy === 'date') list.sort((a, b) => a.dOut.localeCompare(b.dOut));
    else if (sortBy === 'nights') list.sort((a, b) => a.nights - b.nights);
    return list;
  }, [outResults, retResults, minLay, maxLay, unit, sortBy]);

  const best = combos[0];
  const topThree = combos.slice(0, 3);

  return (
    <>
      {/* Controls */}
      <div className="card">
        <div className="card__head">
          <div>
            <div className="card__title">Khứ hồi tối ưu</div>
            <div className="card__sub">Tìm tổ hợp ngày đi – về có tổng giá rẻ nhất</div>
          </div>
          <div className="statuspill">
            <span style={{ color: 'var(--sky-700)' }}>{I.zap()}</span>
            <span><b className="mono">{combos.length}</b> tổ hợp khả thi</span>
          </div>
        </div>
        <div className="card__body" style={{ display: 'flex', gap: 14, alignItems: 'center', flexWrap: 'wrap' }}>
          <div className="field" style={{ flex: '0 0 auto' }}>
            <span className="field__label">Số {unit === 'days' ? 'đêm' : 'giờ'} tối thiểu</span>
            <input className="input mono" type="number" min="1" max="365" value={minLay} onChange={e => setMinLay(+e.target.value)} style={{ width: 100 }} />
          </div>
          <div style={{ paddingTop: 22, color: 'var(--text-3)', fontSize: 18 }}>—</div>
          <div className="field" style={{ flex: '0 0 auto' }}>
            <span className="field__label">Số {unit === 'days' ? 'đêm' : 'giờ'} tối đa</span>
            <input className="input mono" type="number" min="1" max="365" value={maxLay} onChange={e => setMaxLay(+e.target.value)} style={{ width: 100 }} />
          </div>
          <div className="field" style={{ flex: '0 0 auto' }}>
            <span className="field__label">Đơn vị</span>
            <div className="seg">
              <button className={`seg__btn ${unit === 'days' ? 'seg__btn--active' : ''}`} onClick={() => setUnit('days')}>Ngày</button>
              <button className={`seg__btn ${unit === 'hours' ? 'seg__btn--active' : ''}`} onClick={() => setUnit('hours')}>Giờ</button>
            </div>
          </div>
          <div style={{ flex: 1 }} />
          <div className="field" style={{ flex: '0 0 auto' }}>
            <span className="field__label">Sắp xếp</span>
            <div className="seg">
              <button className={`seg__btn ${sortBy === 'total' ? 'seg__btn--active' : ''}`} onClick={() => setSortBy('total')}>Tổng giá</button>
              <button className={`seg__btn ${sortBy === 'date' ? 'seg__btn--active' : ''}`} onClick={() => setSortBy('date')}>Ngày đi</button>
              <button className={`seg__btn ${sortBy === 'nights' ? 'seg__btn--active' : ''}`} onClick={() => setSortBy('nights')}>Số đêm</button>
            </div>
          </div>
        </div>
      </div>

      {/* Best combo hero card */}
      {best && (
        <div className="combo-best">
          <div>
            <div className="combo-best__leg-label">✈ Chuyến đi</div>
            <div className="combo-best__leg-date">{fmtDateShort(best.dOut)} <small style={{ fontWeight: 500, opacity: .8, fontSize: 14 }}>{fmtDay(best.dOut)}</small></div>
            <div className="combo-best__leg-price">{best.outFlight.flightNum} · {best.outFlight.depTime} → {best.outFlight.arrTime} · {fmtPriceCompact(best.outFlight.price, currency, exchangeRate)}</div>
          </div>
          <div className="combo-best__arrow">{I.arrow()}</div>
          <div>
            <div className="combo-best__leg-label">↩ Chuyến về</div>
            <div className="combo-best__leg-date">{fmtDateShort(best.dRet)} <small style={{ fontWeight: 500, opacity: .8, fontSize: 14 }}>{fmtDay(best.dRet)}</small></div>
            <div className="combo-best__leg-price">{best.retFlight.flightNum} · {best.retFlight.depTime} → {best.retFlight.arrTime} · {fmtPriceCompact(best.retFlight.price, currency, exchangeRate)}</div>
          </div>
          <div className="combo-best__total">
            <div className="combo-best__total-label">Tổng rẻ nhất</div>
            <div className="combo-best__total-value">{fmtPriceCompact(best.total, currency, exchangeRate)}</div>
            <div className="combo-best__nights">{best.nights} đêm · tiết kiệm {fmtPriceCompact(combos[Math.min(combos.length - 1, 10)]?.total - best.total, currency, exchangeRate)} vs top 10</div>
          </div>
        </div>
      )}

      {/* Combo list */}
      <div className="card">
        <div className="card__head">
          <div className="card__title">Tổ hợp đi – về (sắp xếp theo {sortBy === 'total' ? 'tổng giá' : sortBy === 'date' ? 'ngày đi' : 'số đêm'})</div>
        </div>
        <div className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 600, overflowY: 'auto' }}>
          {/* Header row */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 130px 1fr 130px 140px 90px', gap: 14, padding: '4px 16px', fontSize: 11, fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            <div>Ngày đi</div>
            <div style={{ textAlign: 'right' }}>Giá đi</div>
            <div>Ngày về</div>
            <div style={{ textAlign: 'right' }}>Giá về</div>
            <div style={{ textAlign: 'right' }}>Tổng cộng</div>
            <div style={{ textAlign: 'center' }}>Số đêm</div>
          </div>
          {combos.length === 0 && (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-3)' }}>
              Không có tổ hợp phù hợp. Thử tăng khoảng số đêm cho phép.
            </div>
          )}
          {combos.slice(0, 50).map((c, i) => {
            const isTop = i < 3;
            return (
              <div key={c.dOut + '-' + c.dRet} className={`combo-row ${isTop ? 'combo-row--top' : ''}`}>
                <div className="combo-row__leg">
                  <div className="combo-row__date">
                    {fmtDateShort(c.dOut)}
                    {i === 0 && <span className="tag tag--best" style={{ marginLeft: 6 }}>{I.star()} Rẻ nhất</span>}
                  </div>
                  <div className="combo-row__day">{fmtDay(c.dOut)} · {c.outFlight.flightNum}</div>
                </div>
                <div className="combo-row__price">{fmtPriceCompact(c.outFlight.price, currency, exchangeRate)}</div>
                <div className="combo-row__leg">
                  <div className="combo-row__date">{fmtDateShort(c.dRet)}</div>
                  <div className="combo-row__day">{fmtDay(c.dRet)} · {c.retFlight.flightNum}</div>
                </div>
                <div className="combo-row__price">{fmtPriceCompact(c.retFlight.price, currency, exchangeRate)}</div>
                <div className="combo-row__total">{fmtPriceCompact(c.total, currency, exchangeRate)}</div>
                <div className="combo-row__nights">{c.nights} đêm</div>
              </div>
            );
          })}
          {combos.length > 50 && (
            <div style={{ textAlign: 'center', padding: 10, color: 'var(--text-3)', fontSize: 12.5 }}>
              + {combos.length - 50} tổ hợp khác (đã ẩn để rút gọn)
            </div>
          )}
        </div>
      </div>
    </>
  );
}

window.ComboTab = ComboTab;
