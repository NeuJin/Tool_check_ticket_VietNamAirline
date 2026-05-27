// =========================================================
// settings-tab.jsx — API & app preferences
// =========================================================

function SettingsTab({ state, setState }) {
  const [showSecret, setShowSecret] = React.useState(false);
  const [tokenStatus, setTokenStatus] = React.useState({ vna: 'ok', amadeus: 'unset', kiwi: 'unset' });

  // Local buffers for token inputs — committing to global state on every keystroke
  // re-renders the entire app, which freezes the UI when pasting the very long
  // x-d-token (thousands of chars). Commit only on blur or via explicit button.
  const [localXdToken,     setLocalXdToken]     = React.useState(state.xdToken     || '');
  const [localAmadeusId,   setLocalAmadeusId]   = React.useState(state.amadeusId   || '');
  const [localAmadeusSec,  setLocalAmadeusSec]  = React.useState(state.amadeusSecret || '');
  const [localKiwiKey,     setLocalKiwiKey]     = React.useState(state.kiwiKey     || '');

  function setField(k, v) { setState(s => ({ ...s, [k]: v })); }

  function commitXdToken()     { if (localXdToken    !== state.xdToken)       setField('xdToken',       localXdToken); }
  function commitAmadeusId()   { if (localAmadeusId  !== state.amadeusId)     setField('amadeusId',     localAmadeusId); }
  function commitAmadeusSec()  { if (localAmadeusSec !== state.amadeusSecret) setField('amadeusSecret', localAmadeusSec); }
  function commitKiwiKey()     { if (localKiwiKey    !== state.kiwiKey)       setField('kiwiKey',       localKiwiKey); }

  async function pasteFromClipboard() {
    try {
      const txt = await navigator.clipboard.readText();
      if (txt) {
        const trimmed = txt.trim();
        setLocalXdToken(trimmed);
        // Commit immediately since user explicitly invoked paste
        setField('xdToken', trimmed);
      }
    } catch (e) {
      alert('Không đọc được clipboard. Hãy paste thủ công vào ô và nhấn Lưu.');
    }
  }

  return (
    <>
      {/* API source selection */}
      <div className="card">
        <div className="card__head">
          <div>
            <div className="card__title">Nguồn dữ liệu giá vé</div>
            <div className="card__sub">Chọn API để lấy giá. Có thể bật nhiều nguồn để so sánh.</div>
          </div>
        </div>
        <div className="card__body" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
          {[
            { id: 'vna_direct', name: 'VNA Direct', desc: 'API booking trực tiếp · Miễn phí · Không cần đăng ký', status: tokenStatus.vna, recommend: true },
            { id: 'amadeus',    name: 'Amadeus',    desc: 'API Amadeus · Đa hãng · Cần đăng ký miễn phí', status: tokenStatus.amadeus },
            { id: 'kiwi',       name: 'Kiwi Tequila', desc: 'API Kiwi.com · Cần API key', status: tokenStatus.kiwi },
          ].map(api => (
            <div key={api.id} className={`optcard ${state.apiType === api.id ? 'optcard--on' : ''}`} style={{ padding: 14, alignItems: 'flex-start' }} onClick={() => setField('apiType', api.id)}>
              <div className="optcard__check" style={{ marginTop: 2 }}>{state.apiType === api.id && I.check()}</div>
              <div className="optcard__body">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div className="optcard__title">{api.name}</div>
                  {api.recommend && <span className="tag tag--cheap">Khuyến nghị</span>}
                  {api.status === 'ok' && <span className="tag tag--cheap" style={{ background: 'var(--good-bg)', color: '#047857' }}>● Sẵn sàng</span>}
                  {api.status === 'unset' && <span className="tag tag--off">○ Chưa cài</span>}
                </div>
                <div className="optcard__desc" style={{ marginTop: 4 }}>{api.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="settings-grid">
        {/* VNA Direct token */}
        <div className="card">
          <div className="card__head">
            <div>
              <div className="card__title">VNA Direct — Token</div>
              <div className="card__sub">x-d-token được lấy tự động qua headless browser khi cần</div>
            </div>
          </div>
          <div className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div className="field">
              <span className="field__label">x-d-token (tự động làm mới)</span>
              <div className="tokenrow" style={{ alignItems: 'flex-start' }}>
                {showSecret ? (
                  <textarea className="input mono"
                            value={localXdToken}
                            onChange={e => setLocalXdToken(e.target.value)}
                            onBlur={commitXdToken}
                            placeholder="Để trống — app sẽ tự lấy khi cần"
                            rows={3}
                            spellCheck={false}
                            style={{ flex: 1, resize: 'vertical', fontSize: 11, lineHeight: 1.4, wordBreak: 'break-all' }} />
                ) : (
                  <input className="input mono" type="password" readOnly
                         value={localXdToken ? '•'.repeat(Math.min(localXdToken.length, 40)) : ''}
                         placeholder="Để trống — app sẽ tự lấy khi cần"
                         style={{ flex: 1 }} />
                )}
                <button className="btn btn--icon" onClick={() => setShowSecret(s => !s)} title={showSecret ? 'Ẩn' : 'Hiện'}>
                  {showSecret ? I.eyeOff() : I.eye()}
                </button>
              </div>
              <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
                <button className="btn" onClick={pasteFromClipboard}>📋 Dán từ clipboard</button>
                <button className="btn" onClick={() => { setLocalXdToken(''); setField('xdToken', ''); }}>🗑 Xóa</button>
                <button className="btn btn--primary" onClick={commitXdToken}>💾 Lưu</button>
              </div>
              <span className="field__hint">Token được lưu cục bộ, không gửi cho bên thứ ba · Dùng nút "Dán từ clipboard" để tránh lag khi paste chuỗi dài</span>
            </div>
            <div className="statusrow">
              <span style={{ color: 'var(--good)' }}>●</span>
              <span style={{ flex: 1 }}>Token còn hiệu lực <b className="mono">~24 phút</b></span>
              <button className="btn">{I.refresh()} Làm mới</button>
            </div>
            <div className="statusrow">
              <span style={{ color: 'var(--sky-700)' }}>{I.info()}</span>
              <span style={{ flex: 1 }}>App ưu tiên dùng Microsoft Edge cài sẵn để bypass bot detection. Cần Playwright + Chromium.</span>
            </div>
          </div>
        </div>

        {/* Amadeus */}
        <div className="card">
          <div className="card__head">
            <div>
              <div className="card__title">Amadeus API</div>
              <div className="card__sub">developers.amadeus.com — đăng ký miễn phí</div>
            </div>
          </div>
          <div className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div className="field">
              <span className="field__label">Client ID</span>
              <input className="input mono" value={localAmadeusId}
                     onChange={e => setLocalAmadeusId(e.target.value)}
                     onBlur={commitAmadeusId}
                     placeholder="abc123..." />
            </div>
            <div className="field">
              <span className="field__label">Client Secret</span>
              <input className="input mono" type={showSecret ? 'text' : 'password'} value={localAmadeusSec}
                     onChange={e => setLocalAmadeusSec(e.target.value)}
                     onBlur={commitAmadeusSec}
                     placeholder="••••••••" />
            </div>
            <button className="btn">{I.zap()} Kiểm tra kết nối</button>
          </div>
        </div>

        {/* Kiwi */}
        <div className="card">
          <div className="card__head">
            <div>
              <div className="card__title">Kiwi Tequila API</div>
              <div className="card__sub">tequila.kiwi.com → My account → Add API key</div>
            </div>
          </div>
          <div className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div className="field">
              <span className="field__label">API Key</span>
              <input className="input mono" type={showSecret ? 'text' : 'password'} value={localKiwiKey}
                     onChange={e => setLocalKiwiKey(e.target.value)}
                     onBlur={commitKiwiKey}
                     placeholder="••••••••" />
            </div>
            <button className="btn">{I.zap()} Kiểm tra kết nối</button>
          </div>
        </div>

        {/* Exchange rate */}
        <div className="card">
          <div className="card__head">
            <div>
              <div className="card__title">Tỷ giá</div>
              <div className="card__sub">open.er-api.com · Cache 1 giờ · Tự động làm mới</div>
            </div>
          </div>
          <div className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div className="statusrow">
              <span style={{ fontWeight: 700, color: 'var(--ink-900)' }}>1 JPY ≈</span>
              <span className="mono" style={{ fontWeight: 700, fontSize: 18, color: 'var(--sky-700)', flex: 1 }}>{state.exchangeRate.toFixed(2)} ₫</span>
              <button className="btn">{I.refresh()} Làm mới</button>
            </div>
            <div className="field">
              <span className="field__label">Tỷ giá fallback (khi mất mạng)</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <input className="input mono" type="number" value={state.fallbackRate} onChange={e => setField('fallbackRate', +e.target.value)} style={{ width: 120 }} />
                <span style={{ color: 'var(--text-2)', fontSize: 13 }}>₫ / JPY</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* About */}
      <div className="card">
        <div className="card__body" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div className="brand__mark">{I.plane()}</div>
            <div>
              <div style={{ fontWeight: 700, color: 'var(--ink-900)' }}>VNA Flight Check</div>
              <div style={{ fontSize: 12, color: 'var(--text-2)' }}>Phiên bản 2.0 · Web UI redesign</div>
            </div>
          </div>
          <div style={{ fontSize: 12.5, color: 'var(--text-2)' }}>
            Tool độc lập, không liên kết chính thức với hãng. Dữ liệu giá lấy qua API công khai.
          </div>
        </div>
      </div>
    </>
  );
}

window.SettingsTab = SettingsTab;
