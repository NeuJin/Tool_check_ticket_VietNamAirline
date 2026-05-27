// =========================================================
// shared.jsx — airport data, icons, formatters, mock results
// =========================================================

const AIRPORTS = [
  // Việt Nam
  { code: 'HAN', flag: '🇻🇳', city: 'Hà Nội',     name: 'Nội Bài',          country: 'Việt Nam' },
  { code: 'SGN', flag: '🇻🇳', city: 'TP.HCM',      name: 'Tân Sơn Nhất',     country: 'Việt Nam' },
  { code: 'DAD', flag: '🇻🇳', city: 'Đà Nẵng',    name: 'Đà Nẵng Intl.',    country: 'Việt Nam' },
  { code: 'CXR', flag: '🇻🇳', city: 'Nha Trang',  name: 'Cam Ranh',         country: 'Việt Nam' },
  { code: 'PQC', flag: '🇻🇳', city: 'Phú Quốc',   name: 'Phú Quốc Intl.',   country: 'Việt Nam' },
  { code: 'VCA', flag: '🇻🇳', city: 'Cần Thơ',    name: 'Cần Thơ Intl.',    country: 'Việt Nam' },
  { code: 'HUI', flag: '🇻🇳', city: 'Huế',         name: 'Phú Bài',          country: 'Việt Nam' },
  { code: 'DLI', flag: '🇻🇳', city: 'Đà Lạt',     name: 'Liên Khương',      country: 'Việt Nam' },
  { code: 'HPH', flag: '🇻🇳', city: 'Hải Phòng',   name: 'Cát Bi',           country: 'Việt Nam' },
  { code: 'VII', flag: '🇻🇳', city: 'Vinh',        name: 'Vinh',             country: 'Việt Nam' },
  { code: 'UIH', flag: '🇻🇳', city: 'Quy Nhơn',   name: 'Phù Cát',          country: 'Việt Nam' },
  { code: 'BMV', flag: '🇻🇳', city: 'Buôn Ma Thuột', name: 'Buôn Ma Thuột', country: 'Việt Nam' },
  // Nhật Bản
  { code: 'NRT', flag: '🇯🇵', city: 'Tokyo',       name: 'Narita',           country: 'Nhật Bản' },
  { code: 'HND', flag: '🇯🇵', city: 'Tokyo',       name: 'Haneda',           country: 'Nhật Bản' },
  { code: 'KIX', flag: '🇯🇵', city: 'Osaka',       name: 'Kansai',           country: 'Nhật Bản' },
  { code: 'NGO', flag: '🇯🇵', city: 'Nagoya',      name: 'Centrair',         country: 'Nhật Bản' },
  { code: 'FUK', flag: '🇯🇵', city: 'Fukuoka',     name: 'Fukuoka',          country: 'Nhật Bản' },
  { code: 'CTS', flag: '🇯🇵', city: 'Sapporo',     name: 'Chitose',          country: 'Nhật Bản' },
  { code: 'OKA', flag: '🇯🇵', city: 'Okinawa',     name: 'Naha',             country: 'Nhật Bản' },
];

const AIRPORT_BY_CODE = Object.fromEntries(AIRPORTS.map(a => [a.code, a]));

// ─── Formatters ──────────────────────────────────────────────────────────────
const fmtVND = (n) => {
  if (n == null) return '—';
  return new Intl.NumberFormat('vi-VN').format(Math.round(n)) + ' ₫';
};
const fmtJPY = (n) => {
  if (n == null) return '—';
  return '¥' + new Intl.NumberFormat('ja-JP').format(Math.round(n));
};
const fmtPrice = (vnd, currency = 'VND', rate = 165) => {
  if (vnd == null) return '—';
  if (currency === 'JPY') return fmtJPY(vnd / rate);
  if (currency === 'BOTH') return `${fmtVND(vnd)} · ${fmtJPY(vnd / rate)}`;
  return fmtVND(vnd);
};
const fmtDateVI = (d) => {
  const dt = (d instanceof Date) ? d : new Date(d);
  return dt.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' });
};
const fmtDateShort = (d) => {
  const dt = (d instanceof Date) ? d : new Date(d);
  return dt.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
};
const fmtDay = (d) => {
  const dt = (d instanceof Date) ? d : new Date(d);
  const days = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'];
  return days[dt.getDay()];
};
const ymd = (d) => {
  const dt = (d instanceof Date) ? d : new Date(d);
  const y = dt.getFullYear();
  const m = String(dt.getMonth() + 1).padStart(2, '0');
  const dd = String(dt.getDate()).padStart(2, '0');
  return `${y}-${m}-${dd}`;
};
const addDays = (d, n) => {
  const dt = (d instanceof Date) ? new Date(d) : new Date(d);
  dt.setDate(dt.getDate() + n);
  return dt;
};
const daysBetween = (a, b) => {
  const ad = (a instanceof Date) ? a : new Date(a);
  const bd = (b instanceof Date) ? b : new Date(b);
  return Math.round((bd - ad) / 86400000);
};

// ─── Mock flight data generator (deterministic per route/date) ───────────────
function hashStr(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) { h = ((h << 5) - h + s.charCodeAt(i)) | 0; }
  return Math.abs(h);
}
function mockPrice(origin, dest, dateStr) {
  // Base price by route type
  const isIntl = AIRPORT_BY_CODE[origin]?.country !== AIRPORT_BY_CODE[dest]?.country;
  const base = isIntl ? 8500000 : 1800000;
  const variance = isIntl ? 6500000 : 2000000;
  const seed = hashStr(`${origin}-${dest}-${dateStr}`);
  const r = (seed % 1000) / 1000;
  const dt = new Date(dateStr);
  const dow = dt.getDay();
  // Weekend premium
  const dowBoost = (dow === 5 || dow === 6 || dow === 0) ? 0.35 : 0;
  // Holiday premium
  const holBoost = HolidayData.isPremiumPeriod(dt) ? 0.55 : 0;
  const price = base * (1 + dowBoost + holBoost) + variance * r * 0.6;
  return Math.round(price / 10000) * 10000;
}
function mockFlights(origin, dest, dateStr, directOnly = false) {
  const isIntl = AIRPORT_BY_CODE[origin]?.country !== AIRPORT_BY_CODE[dest]?.country;
  const seed = hashStr(`${origin}-${dest}-${dateStr}`);
  // 1-4 flights per day
  const count = isIntl ? 1 + (seed % 3) : 2 + (seed % 4);
  const basePrice = mockPrice(origin, dest, dateStr);
  const flights = [];
  for (let i = 0; i < count; i++) {
    const s2 = hashStr(`${seed}-${i}`);
    const stops = directOnly ? 0 : (isIntl && (s2 % 5) === 0 ? 1 : 0);
    const priceMul = 1 + ((s2 % 30) - 10) / 100;
    const depHour = 6 + (s2 % 15);
    const depMin  = ((s2 / 100) | 0) % 60;
    const durMin  = isIntl ? (5 * 60 + 30 + (s2 % 90)) : (2 * 60 + (s2 % 30));
    const fno = isIntl ? `VN30${(s2 % 9) + 1}` : `VN${100 + (s2 % 700)}`;
    const arrTime = new Date(`${dateStr}T${String(depHour).padStart(2,'0')}:${String(depMin).padStart(2,'0')}:00`);
    arrTime.setMinutes(arrTime.getMinutes() + durMin);
    flights.push({
      date: dateStr,
      price: Math.max(800000, Math.round(basePrice * priceMul / 10000) * 10000),
      depTime: `${String(depHour).padStart(2,'0')}:${String(depMin).padStart(2,'0')}`,
      arrTime: `${String(arrTime.getHours()).padStart(2,'0')}:${String(arrTime.getMinutes()).padStart(2,'0')}`,
      stops,
      durationMin: durMin,
      flightNum: fno,
    });
  }
  return flights.sort((a, b) => a.price - b.price);
}
function mockRangeResults(origin, dest, startDate, endDate, directOnly = false) {
  const out = {};
  let cur = new Date(startDate);
  const end = new Date(endDate);
  while (cur <= end) {
    const ds = ymd(cur);
    // 8% of days have no flights (simulate sold out / data gap)
    if ((hashStr(`${origin}-${dest}-${ds}-empty`) % 100) < 6) {
      out[ds] = [];
    } else {
      out[ds] = mockFlights(origin, dest, ds, directOnly);
    }
    cur = addDays(cur, 1);
  }
  return out;
}

// ─── Holidays ────────────────────────────────────────────────────────────────
const HolidayData = {
  // VN fixed (month-day)
  vnFixed: {
    '1-1':  'Tết Dương lịch',
    '4-30': 'Giải phóng miền Nam',
    '5-1':  'Quốc tế Lao động',
    '9-2':  'Quốc khánh',
  },
  // VN Tết (lunar new year, approximated for demo)
  vnTetCenter: { 2026: '2026-02-17', 2027: '2027-02-06' },
  // JP fixed holidays
  jpFixed: {
    '1-1':   '元日 / Năm mới',
    '2-11':  '建国記念の日',
    '2-23':  '天皇誕生日',
    '4-29':  '昭和の日',
    '5-3':   '憲法記念日',
    '5-4':   'みどりの日',
    '5-5':   'こどもの日',
    '8-11':  '山の日',
    '11-3':  '文化の日',
    '11-23': '勤労感謝の日',
  },
  jpBig(d) {
    const y = d.getFullYear();
    const inRange = (s, e) => d >= new Date(s) && d <= new Date(e);
    if (inRange(`${y}-04-27`, `${y}-05-06`)) return '🎌 Golden Week';
    if (inRange(`${y}-08-10`, `${y}-08-18`)) return '🏮 Obon';
    if (inRange(`${y}-12-27`, `${y}-12-31`)) return '🎍 Năm mới Nhật (年末)';
    if (inRange(`${y}-01-01`, `${y}-01-05`)) return '🎍 Năm mới Nhật (正月)';
    return null;
  },
  vnHoliday(d) {
    const key = `${d.getMonth() + 1}-${d.getDate()}`;
    if (this.vnFixed[key]) return this.vnFixed[key];
    // Approximate Tết — 5 days around Tết center
    const y = d.getFullYear();
    if (this.vnTetCenter[y]) {
      const center = new Date(this.vnTetCenter[y]);
      const diff = Math.abs(daysBetween(center, d));
      if (diff <= 4) return `Tết Nguyên Đán (ngày ${diff + 1})`;
    }
    return null;
  },
  jpHoliday(d) {
    const key = `${d.getMonth() + 1}-${d.getDate()}`;
    return this.jpFixed[key] || null;
  },
  isPremiumPeriod(d) {
    return !!(this.jpBig(d) || this.vnHoliday(d) || this.jpHoliday(d));
  }
};

// ─── Icons ───────────────────────────────────────────────────────────────────
const I = {
  plane: (cls='') => <svg className={cls} width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"/></svg>,
  search: (cls='') => <svg className={cls} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>,
  list: (cls='') => <svg className={cls} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="8" x2="21" y1="6" y2="6"/><line x1="8" x2="21" y1="12" y2="12"/><line x1="8" x2="21" y1="18" y2="18"/><line x1="3" x2="3.01" y1="6" y2="6"/><line x1="3" x2="3.01" y1="12" y2="12"/><line x1="3" x2="3.01" y1="18" y2="18"/></svg>,
  combo: (cls='') => <svg className={cls} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/></svg>,
  bell: (cls='') => <svg className={cls} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>,
  settings: (cls='') => <svg className={cls} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>,
  cal: (cls='') => <svg className={cls} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>,
  swap: (cls='') => <svg className={cls} width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M7 16V4M3 8l4-4 4 4M17 8v12M13 16l4 4 4-4"/></svg>,
  arrow: (cls='') => <svg className={cls} width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 5l7 7-7 7"/></svg>,
  arrowDown: (cls='') => <svg className={cls} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m6 9 6 6 6-6"/></svg>,
  check: (cls='') => <svg className={cls} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5"/></svg>,
  x: (cls='') => <svg className={cls} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18M6 6l12 12"/></svg>,
  trend: (cls='') => <svg className={cls} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>,
  trendDown: (cls='') => <svg className={cls} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 17 13.5 8.5 8.5 13.5 2 7"/><polyline points="16 17 22 17 22 11"/></svg>,
  refresh: (cls='') => <svg className={cls} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/></svg>,
  copy: (cls='') => <svg className={cls} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="14" height="14" x="8" y="8" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>,
  trash: (cls='') => <svg className={cls} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>,
  save: (cls='') => <svg className={cls} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>,
  play: (cls='') => <svg className={cls} width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>,
  pause: (cls='') => <svg className={cls} width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>,
  chevL: (cls='') => <svg className={cls} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>,
  chevR: (cls='') => <svg className={cls} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="m9 18 6-6-6-6"/></svg>,
  pin: (cls='') => <svg className={cls} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 17v5"/><path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z"/></svg>,
  star: (cls='') => <svg className={cls} width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>,
  zap: (cls='') => <svg className={cls} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>,
  eye: (cls='') => <svg className={cls} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>,
  eyeOff: (cls='') => <svg className={cls} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><line x1="2" x2="22" y1="2" y2="22"/></svg>,
  info: (cls='') => <svg className={cls} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>,
};

// Format duration min → "Xh YYm"
const fmtDuration = (min) => {
  const h = (min / 60) | 0;
  const m = min % 60;
  return `${h}h${String(m).padStart(2, '0')}m`;
};

// Holiday flag for a date — returns {tag, text} or null
function holidayTag(d) {
  const dt = (d instanceof Date) ? d : new Date(d);
  const big = HolidayData.jpBig(dt);
  if (big) return { cls: 'big', text: big };
  const jp = HolidayData.jpHoliday(dt);
  if (jp) return { cls: 'jp', text: jp };
  const vn = HolidayData.vnHoliday(dt);
  if (vn) return { cls: 'vn', text: vn };
  return null;
}

// Export to window
Object.assign(window, {
  AIRPORTS, AIRPORT_BY_CODE,
  fmtVND, fmtJPY, fmtPrice, fmtDateVI, fmtDateShort, fmtDay, fmtDuration,
  ymd, addDays, daysBetween,
  HolidayData, holidayTag,
  mockFlights, mockRangeResults, mockPrice,
  I,
});
