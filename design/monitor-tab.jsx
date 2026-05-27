// =========================================================
// monitor-tab.jsx — saved searches + price alerts
// =========================================================

function MonitorTab({ state, setState }) {
  const { savedSearches, monitorOn, monitorInterval, notifyInterval, notifyDrop, notifyPeriodic, alerts } = state;

  function toggleMonitor() {
    setState(s => ({ ...s, monitorOn: !s.monitorOn }));
  }
  function loadSearch(id) {
    const ss = savedSearches.find(s => s.id === id);
    if (!ss) return;
    setState(s => ({ ...s, ...ss.cfg, activeTab: 'search' }));
  }
  function delSearch(id) {
    setState(s => ({ ...s, savedSearches: s.savedSearches.filter(x => x.id !== id) }));
  }
  function toggleActive(id) {
    setState(s => ({
      ...s,
      savedSearches: s.savedSearches.map(x => x.id === id ? { ...x, active: !x.active } : x)
    }));
  }

  return (
    <>
      {/* Control panel */}
      <div className="card">
        <div className="card__head">
          <div>
            <div className="card__title">Theo dõi giá tự động</div>
            <div className="card__sub">Định kỳ quét lại các cấu hình đã lưu · Thông báo khi giá giảm</div>
          </div>
          <div className="statuspill">
            <span className={`statuspill__dot ${monitorOn ? '' : 'statuspill__dot--off'}`} />
            <span>{monitorOn ? 'Đang chạy' : 'Đã dừng'}</span>
          </div>
        </div>
        <div className="card__body" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 14 }}>
          <div className="field">
            <span className="field__label">Tần suất kiểm tra</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <input className="input mono" type="number" min="5" max="1440" value={monitorInterval}
                     onChange={e => setState(s => ({ ...s, monitorInterval: +e.target.value }))} style={{ width: 90 }} />
              <span style={{ color: 'var(--text-2)', fontSize: 13 }}>phút</span>
            </div>
          </div>
          <div className="field">
            <span className="field__label">Khoảng cách thông báo</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <input className="input mono" type="number" min="15" max="1440" value={notifyInterval}
                     onChange={e => setState(s => ({ ...s, notifyInterval: +e.target.value }))} style={{ width: 90 }} />
              <span style={{ color: 'var(--text-2)', fontSize: 13 }}>phút</span>
            </div>
          </div>
          <label className={`optcard ${notifyDrop ? 'optcard--on' : ''}`} style={{ marginTop: 22 }} onClick={() => setState(s => ({ ...s, notifyDrop: !s.notifyDrop }))}>
            <div className="optcard__check">{notifyDrop && I.check()}</div>
            <div className="optcard__body">
              <div className="optcard__title">Báo khi giá giảm</div>
              <div className="optcard__desc">Pop-up Windows toast</div>
            </div>
          </label>
          <label className={`optcard ${notifyPeriodic ? 'optcard--on' : ''}`} style={{ marginTop: 22 }} onClick={() => setState(s => ({ ...s, notifyPeriodic: !s.notifyPeriodic }))}>
            <div className="optcard__check">{notifyPeriodic && I.check()}</div>
            <div className="optcard__body">
              <div className="optcard__title">Báo định kỳ</div>
              <div className="optcard__desc">Hiển thị giá hiện tại</div>
            </div>
          </label>
        </div>
        <div className="card__body" style={{ paddingTop: 4, display: 'flex', gap: 10, alignItems: 'center' }}>
          <button className={`btn ${monitorOn ? 'btn--danger' : 'btn--primary'} btn--lg`} onClick={toggleMonitor}>
            {monitorOn ? <>{I.pause()} Dừng theo dõi</> : <>{I.play()} Bắt đầu theo dõi</>}
          </button>
          <span style={{ fontSize: 13, color: 'var(--text-2)' }}>
            {monitorOn
              ? <>Đang theo dõi <b>{savedSearches.filter(s => s.active).length}</b> cấu hình · Lần quét tiếp: <span className="mono">~{monitorInterval} phút</span></>
              : <>Bật để bắt đầu kiểm tra giá tự động</>}
          </span>
        </div>
      </div>

      {/* Recent alerts */}
      <div className="card">
        <div className="card__head">
          <div>
            <div className="card__title">Cảnh báo gần đây</div>
            <div className="card__sub">Lịch sử giá giảm & thông báo định kỳ</div>
          </div>
          <button className="btn btn--ghost">{I.trash()} Xóa tất cả</button>
        </div>
        <div className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {alerts.length === 0 && (
            <div style={{ textAlign: 'center', padding: 30, color: 'var(--text-3)' }}>Chưa có cảnh báo nào</div>
          )}
          {alerts.map(a => (
            <div key={a.id} className={`alertcard alertcard--${a.kind}`}>
              <div className="alertcard__icon">
                {a.kind === 'good' ? I.trendDown() : I.bell()}
              </div>
              <div style={{ flex: 1 }}>
                <div className="alertcard__title">{a.title}</div>
                <div className="alertcard__body">{a.body}</div>
                <div className="alertcard__time">{a.time}</div>
              </div>
              {a.kind === 'good' && (
                <button className="btn btn--primary" style={{ height: 32 }}>{I.eye()} Xem</button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Saved searches */}
      <div className="card">
        <div className="card__head">
          <div>
            <div className="card__title">Cấu hình đã lưu</div>
            <div className="card__sub">Bật công tắc bên trái để đưa cấu hình vào danh sách theo dõi</div>
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-2)' }}>
            {savedSearches.filter(s => s.active).length} / {savedSearches.length} đang theo dõi
          </div>
        </div>
        <div className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {savedSearches.length === 0 && (
            <div style={{ textAlign: 'center', padding: 30, color: 'var(--text-3)' }}>
              Chưa có cấu hình. Lưu một cấu hình từ tab Tìm chuyến bay.
            </div>
          )}
          {savedSearches.map(ss => (
            <div key={ss.id} className={`savedrow ${ss.active ? 'savedrow--active' : ''}`}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <button
                  className={`toggle ${ss.active ? 'toggle--on' : ''}`}
                  onClick={() => toggleActive(ss.id)}
                  aria-label="Toggle"
                />
                <div>
                  <div className="savedrow__name">{ss.name}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-2)' }}>
                    {ss.lastPrice ? `Giá gần nhất: ${fmtPriceCompact(ss.lastPrice, state.currency, state.exchangeRate)}` : 'Chưa quét'}
                  </div>
                </div>
              </div>
              <div className="savedrow__route">
                <span>{ss.cfg.origin}</span>
                {I.arrow()}
                <span>{ss.cfg.dest}</span>
              </div>
              <div className="savedrow__dates">
                {fmtDateShort(ss.cfg.depFrom)} → {fmtDateShort(ss.cfg.depTo)}
              </div>
              <div className="savedrow__type">
                <span className="tag tag--off">{ss.cfg.tripType === 'RT' ? 'Khứ hồi' : 'Một chiều'}</span>
              </div>
              <div className="savedrow__direct">
                {ss.cfg.directOnly ? <span className="tag tag--direct">Bay thẳng</span> : <span style={{ color: 'var(--text-3)' }}>—</span>}
              </div>
              <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
                <button className="btn btn--icon" onClick={() => loadSearch(ss.id)} title="Tải">{I.eye()}</button>
                <button className="btn btn--icon btn--danger" onClick={() => delSearch(ss.id)} title="Xóa">{I.trash()}</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

window.MonitorTab = MonitorTab;
