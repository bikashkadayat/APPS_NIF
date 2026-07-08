import React from 'react';

/**
 * A single day cell in the month calendar. Colour comes from the leave type,
 * but a text code/badge is always shown too (colour-blind support).
 *
 * @param {{
 *   date: Date, inMonth: boolean, record?: Object, isHoliday?: boolean,
 *   isWeekend?: boolean, holidayName?: string, onSelect?: (record:Object)=>void
 * }} props
 */
const CalendarDay = ({ date, inMonth, record, isHoliday, isWeekend, holidayName, onSelect }) => {
  const dayNum = date.getDate();
  const color = record?.display_color;
  const clickable = Boolean(record);

  const classes = [
    'lr-cal-day',
    !inMonth && 'lr-cal-out',
    isWeekend && 'lr-cal-weekend',
    isHoliday && 'lr-cal-holiday',
    record && 'lr-cal-has-leave',
  ].filter(Boolean).join(' ');

  const label = [
    date.toDateString(),
    isWeekend && 'weekend',
    isHoliday && `holiday${holidayName ? `: ${holidayName}` : ''}`,
    record && `${record.leave_type_code} ${record.status}`,
  ].filter(Boolean).join(', ');

  return (
    <div
      className={classes}
      style={color ? { '--day-color': color } : undefined}
      role={clickable ? 'button' : 'gridcell'}
      tabIndex={clickable ? 0 : -1}
      aria-label={label}
      onClick={clickable ? () => onSelect?.(record) : undefined}
      onKeyDown={clickable ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect?.(record); } } : undefined}
    >
      <span className="lr-cal-date">{dayNum}</span>
      {isHoliday && <span className="lr-cal-badge" title={holidayName}>H</span>}
      {record && (
        <span className="lr-cal-tag" style={{ background: color }}>
          {record.leave_type_code}
          {record.day_portion !== 'full' ? ' ½' : ''}
        </span>
      )}
    </div>
  );
};

export default CalendarDay;
