import React, { useEffect, useState } from 'react';
import { CalendarDays, Stethoscope, Baby, HeartHandshake, Award } from 'lucide-react';
import { leaveService } from '../../services/leaveService';

// Category-aware balance cards for the employee dashboard. Driven entirely by
// /leaves/my-entitlements/, so it shows only the leave types available to the
// user's resolved category (interns see Annual/Sick; permanent staff also see
// Maternity/Paternity when eligible), plus an earned/used/available comp card.
const ICONS = {
  annual: { Icon: CalendarDays, color: 'var(--brand-blue, #2563EB)' },
  sick: { Icon: Stethoscope, color: 'var(--brand-red, #DC143C)' },
  maternity: { Icon: Baby, color: '#DB2777' },
  paternity: { Icon: HeartHandshake, color: '#7C3AED' },
};

const Bar = ({ pct, color }) => (
  <div style={{ background: 'var(--bg-main)', height: 8, borderRadius: 4, marginTop: 12, overflow: 'hidden' }}>
    <div style={{ background: color, height: '100%', width: `${Math.min(100, pct)}%`, borderRadius: 4 }} />
  </div>
);

const CategoryBalances = () => {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    leaveService.getEntitlements()
      .then((d) => { if (alive) setData(d); })
      .catch(() => { if (alive) setError('Could not load your leave balances.'); });
    return () => { alive = false; };
  }, []);

  if (error) return <div className="att-err">{error}</div>;
  if (!data) return <div style={{ color: 'var(--text-muted)' }}>Loading balances…</div>;

  const comp = data.compensatory || {};

  return (
    <section>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8, flexWrap: 'wrap', gap: 8 }}>
        <h3 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', fontFamily: '"Playfair Display", serif' }}>My Leave Balances</h3>
        {data.category_label && (
          <span style={{ fontSize: 12, fontWeight: 600, padding: '4px 10px', borderRadius: 999, background: 'var(--bg-main, #eef1f5)', color: 'var(--text-secondary)' }}>
            {data.category_label} · {data.employment_type_label} · {data.service_label}
          </span>
        )}
      </div>
      {data.category_flag && (
        <div className="att-err" style={{ marginBottom: 12, fontSize: 12 }}>Note for HR: {data.category_flag}</div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 20 }}>
        {data.balances.map((b) => {
          const meta = ICONS[b.code] || { Icon: CalendarDays, color: b.color || 'var(--brand-blue)' };
          const pct = b.total > 0 ? (b.used / b.total) * 100 : 0;
          return (
            <div className="balance-card" key={b.code}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div className="bc-type">{b.name}</div>
                <meta.Icon size={18} color={meta.color} />
              </div>
              <div className="bc-used">{b.used}</div>
              <Bar pct={pct} color={meta.color} />
              <div className="bc-total" style={{ marginTop: 12 }}>
                Remaining: <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{b.remaining}</span> / {b.total} days
              </div>
            </div>
          );
        })}

        {/* Compensatory: earned/used/available (not a fixed allocation). */}
        {comp.applicable && (
          <div className="balance-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div className="bc-type">Compensatory</div>
              <Award size={18} color="#0891B2" />
            </div>
            <div className="bc-used">{comp.available}</div>
            <div className="bc-total" style={{ marginTop: 12 }}>
              Available now{comp.pending > 0 ? ` (${comp.pending} pending HR)` : ''}
            </div>
            <div className="bc-total" style={{ marginTop: 4, fontSize: 12, color: 'var(--text-muted)' }}>
              Earned {comp.earned} · Used {comp.used}
            </div>
          </div>
        )}
      </div>
    </section>
  );
};

export default CategoryBalances;
