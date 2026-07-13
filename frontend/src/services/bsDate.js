// Live Bikram Sambat (BS) date for the UI. Converts the current AD date using
// nepali-date-converter (offline, reliable). No hardcoded dates.
import * as NepaliDateModule from 'nepali-date-converter';

// UMD build interop: the constructor can be nested under default.default.
const NepaliDate = NepaliDateModule.default?.default || NepaliDateModule.default || NepaliDateModule;

const BS_MONTHS = [
  'Baishakh', 'Jestha', 'Ashadh', 'Shrawan', 'Bhadra', 'Ashwin',
  'Kartik', 'Mangsir', 'Poush', 'Magh', 'Falgun', 'Chaitra',
];

/** Current BS date as 'YYYY-MM-DD' (e.g. '2083-03-28'), or null on failure. */
export function todayBS(date = new Date()) {
  try {
    return new NepaliDate(date).format('YYYY-MM-DD');
  } catch {
    return null;
  }
}

/** Current BS date, long form (e.g. 'Ashadh 28, 2083'). Falls back to short. */
export function todayBSLong(date = new Date()) {
  try {
    const bs = new NepaliDate(date).getBS(); // { year, month (0-indexed), date }
    return `${BS_MONTHS[bs.month]} ${bs.date}, ${bs.year}`;
  } catch {
    return todayBS(date);
  }
}

/** ms until the next local midnight — used to refresh the date once per day. */
export function msUntilMidnight() {
  const now = new Date();
  const next = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 0, 0, 5);
  return next - now;
}
